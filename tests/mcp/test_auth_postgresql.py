#!/usr/bin/env python3
"""
Unit tests for the PostgreSQL authentication functionality in the HADES MCP server.

These tests require a PostgreSQL server to be running and accessible with the
credentials specified in the environment variables or test configuration.

If PostgreSQL is not available, these tests will be skipped.
"""
import os
import unittest
import pytest
from datetime import datetime, timedelta
from unittest import mock

import psycopg2
import psycopg2.extras

from src.mcp.auth import AuthDB, APIKey
from src.utils.config import PostgreSQLConfig
from tests.patch_auth import postgresql_skip, is_postgresql_available


@postgresql_skip
class TestPostgreSQLAuth(unittest.TestCase):
    """Test PostgreSQL authentication functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Skip if PostgreSQL is not available
        if not is_postgresql_available():
            pytest.skip("PostgreSQL is not available")
            
        # Test configuration
        cls.pg_config = PostgreSQLConfig(
            host=os.environ.get("HADES_MCP__AUTH__PG_CONFIG__HOST", "localhost"),
            port=int(os.environ.get("HADES_MCP__AUTH__PG_CONFIG__PORT", "5432")),
            username=os.environ.get("HADES_MCP__AUTH__PG_CONFIG__USERNAME", "postgres"),
            password=os.environ.get("HADES_MCP__AUTH__PG_CONFIG__PASSWORD", "postgres"),
            database=os.environ.get("HADES_MCP__AUTH__PG_CONFIG__DATABASE", "hades_test")
        )
        
        # Create test database if it doesn't exist
        try:
            cls._create_test_database()
        except Exception as e:
            pytest.skip(f"Failed to create test database: {e}")

    @classmethod
    def _create_test_database(cls):
        """Create test database if it doesn't exist."""
        conn = None
        try:
            # Connect to default postgres database with a timeout
            conn = psycopg2.connect(
                host=cls.pg_config.host,
                port=cls.pg_config.port,
                user=cls.pg_config.username,
                password=cls.pg_config.password,
                dbname="postgres",
                connect_timeout=5  # Add timeout to avoid hanging tests
            )
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (cls.pg_config.database,)
                )
                if not cursor.fetchone():
                    # Create database
                    cursor.execute(f"CREATE DATABASE {cls.pg_config.database}")
                    print(f"Created test database: {cls.pg_config.database}")
                else:
                    print(f"Using existing test database: {cls.pg_config.database}")
        except Exception as e:
            print(f"Warning: Failed to create test database: {e}")
            raise
        finally:
            if conn is not None:
                conn.close()

    def setUp(self):
        """Set up test case."""
        # Skip if PostgreSQL is not available
        if not is_postgresql_available():
            pytest.skip("PostgreSQL is not available")
            
        # Mock the config to use PostgreSQL
        self.config_patcher = mock.patch('src.mcp.auth.config')
        self.mock_config = self.config_patcher.start()
        
        # Configure auth to use PostgreSQL
        self.mock_config.mcp.auth.db_type = "postgresql"
        self.mock_config.mcp.auth.pg_config = self.pg_config
        
        try:
            # Initialize auth DB
            self.auth_db = AuthDB()
            
            # Clean up any existing data
            with self.auth_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rate_limits")
                cursor.execute("DELETE FROM api_keys")
                conn.commit()
        except Exception as e:
            pytest.skip(f"Failed to set up PostgreSQL test: {e}")

    def tearDown(self):
        """Tear down test case."""
        if hasattr(self, 'config_patcher'):
            self.config_patcher.stop()

    def test_init_db(self):
        """Test database initialization."""
        # Re-initialize the database
        self.auth_db.init_db()
        
        # Check if tables exist
        with self.auth_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check api_keys table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'api_keys'
                )
            """)
            self.assertTrue(cursor.fetchone()[0])
            
            # Check rate_limits table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'rate_limits'
                )
            """)
            self.assertTrue(cursor.fetchone()[0])

    def test_create_api_key(self):
        """Test creating an API key."""
        # Create a key with no expiration
        key_id, api_key = self.auth_db.create_api_key("Test Key")
        
        # Verify key was created
        with self.auth_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_keys WHERE key_id = %s", (key_id,))
            row = cursor.fetchone()
            
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "Test Key")
            self.assertIsNone(row["expires_at"])
            self.assertTrue(row["is_active"])
        
        # Create a key with expiration
        key_id2, api_key2 = self.auth_db.create_api_key("Expiring Key", expiry_days=7)
        
        # Verify key was created with expiration
        with self.auth_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_keys WHERE key_id = %s", (key_id2,))
            row = cursor.fetchone()
            
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "Expiring Key")
            self.assertIsNotNone(row["expires_at"])
            
            # Check expiration is approximately 7 days in the future
            now = datetime.now()
            expires_at = row["expires_at"]
            delta = expires_at - now
            self.assertGreater(delta.days, 6)
            self.assertLess(delta.days, 8)

    def test_validate_api_key(self):
        """Test validating an API key."""
        # Create a key
        key_id, api_key = self.auth_db.create_api_key("Validation Test")
        
        # Validate the key
        api_key_obj = self.auth_db.validate_api_key(api_key)
        
        # Check validation result
        self.assertIsNotNone(api_key_obj)
        self.assertEqual(api_key_obj.key_id, key_id)
        self.assertEqual(api_key_obj.name, "Validation Test")
        self.assertTrue(api_key_obj.is_active)
        
        # Test invalid key
        invalid_key = "invalid_key_12345"
        self.assertIsNone(self.auth_db.validate_api_key(invalid_key))
        
        # Test expired key
        # Create a key that's already expired
        with self.auth_db.get_connection() as conn:
            cursor = conn.cursor()
            expired_key_id = "expired_key_id"
            expired_key = "expired_key_12345"
            import hashlib
            key_hash = hashlib.sha256(expired_key.encode()).hexdigest()
            
            # Set expiration to yesterday
            yesterday = datetime.now() - timedelta(days=1)
            
            cursor.execute(
                """
                INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    expired_key_id,
                    key_hash,
                    "Expired Key",
                    datetime.now(),
                    yesterday,
                    True
                )
            )
            conn.commit()
        
        # Validate the expired key
        self.assertIsNone(self.auth_db.validate_api_key(expired_key))

    def test_check_rate_limit(self):
        """Test rate limiting."""
        # Create a key
        key_id, api_key = self.auth_db.create_api_key("Rate Limit Test")
        
        # Set a low rate limit for testing
        rpm_limit = 5
        
        # Check rate limit multiple times
        for i in range(rpm_limit):
            self.assertTrue(self.auth_db.check_rate_limit(api_key, rpm_limit))
        
        # Next request should exceed the limit
        self.assertFalse(self.auth_db.check_rate_limit(api_key, rpm_limit))
        
        # Check rate limit with a different key
        key_id2, api_key2 = self.auth_db.create_api_key("Rate Limit Test 2")
        self.assertTrue(self.auth_db.check_rate_limit(api_key2, rpm_limit))


if __name__ == "__main__":
    unittest.main()
