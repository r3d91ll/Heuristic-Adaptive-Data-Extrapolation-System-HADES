"""
Tests for the MCP authentication module using SQLite in-memory database.

This provides a real database testing approach without requiring PostgreSQL setup.
"""
import os
import pytest
import uuid
import hashlib
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

from src.mcp.auth import APIKey, AuthDB
from fastapi import HTTPException

# Set environment variables for testing
os.environ["HADES_ENV"] = "test"

class TestAuthDBSQLite:
    """Test the AuthDB class with SQLite in-memory database."""
    
    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Set up a SQLite in-memory database for testing."""
        # Create an in-memory SQLite database
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        
        # Create the necessary tables
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE api_keys (
            key_id TEXT PRIMARY KEY,
            key_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            is_active BOOLEAN DEFAULT TRUE
        )
        """)
        
        cursor.execute("""
        CREATE TABLE rate_limits (
            key TEXT NOT NULL,
            requests INTEGER DEFAULT 1,
            window_start TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """)
        
        # Add indexes
        cursor.execute("CREATE INDEX idx_rate_limits_key ON rate_limits(key)")
        cursor.execute("CREATE INDEX idx_rate_limits_expires ON rate_limits(expires_at)")
        
        self.conn.commit()
        
        # Create a custom AuthDB class that uses our connection
        class TestAuthDB(AuthDB):
            def __init__(self, conn):
                self.db_type = "sqlite"
                self.db_path = ":memory:"
                self.conn = conn
            
            @contextmanager
            def get_connection(self):
                try:
                    yield self.conn
                finally:
                    pass  # Don't close the connection
        
        # Create an instance of our test AuthDB
        self.auth_db = TestAuthDB(self.conn)
        
        yield
        
        # Clean up
        self.conn.close()
    
    def test_create_api_key(self):
        """Test API key creation."""
        # Create a key with no expiration
        key_id1, api_key1 = self.auth_db.create_api_key("test_key_1")
        assert key_id1 is not None
        assert api_key1 is not None
        
        # Create a key with expiration
        key_id2, api_key2 = self.auth_db.create_api_key("test_key_2", expiry_days=30)
        assert key_id2 is not None
        assert api_key2 is not None
        
        # Verify keys were created in the database
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM api_keys")
        count = cursor.fetchone()[0]
        assert count == 2
    
    def test_validate_api_key(self):
        """Test API key validation."""
        # Create a test key
        key_id, api_key = self.auth_db.create_api_key("test_key")
        
        # Test valid key
        result = self.auth_db.validate_api_key(api_key)
        assert result is not None
        assert result.key_id == key_id
        assert result.name == "test_key"
        assert result.is_active is True
        
        # Test invalid key
        result = self.auth_db.validate_api_key("invalid_key")
        assert result is None
    
    def test_expired_key(self):
        """Test expired API key validation."""
        # Create a key that expires immediately
        key_id, api_key = self.auth_db.create_api_key("expired_key", expiry_days=0)
        
        # Manually set the expiration to the past
        cursor = self.conn.cursor()
        past_time = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute(
            "UPDATE api_keys SET expires_at = ? WHERE key_id = ?",
            (past_time, key_id)
        )
        self.conn.commit()
        
        # Validation should fail for expired key
        result = self.auth_db.validate_api_key(api_key)
        assert result is None
    
    def test_inactive_key(self):
        """Test inactive API key validation."""
        # Create a key
        key_id, api_key = self.auth_db.create_api_key("inactive_key")
        
        # Manually set the key to inactive
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET is_active = ? WHERE key_id = ?",
            (False, key_id)
        )
        self.conn.commit()
        
        # Validation should fail for inactive key
        result = self.auth_db.validate_api_key(api_key)
        assert result is None
    
    def test_rate_limit(self):
        """Test rate limiting."""
        # Create a test key
        key_id, api_key = self.auth_db.create_api_key("rate_limited_key")
        
        # First request should be allowed
        result = self.auth_db.check_rate_limit(api_key, rpm_limit=5)
        assert result is True
        
        # Make multiple requests
        for _ in range(4):
            result = self.auth_db.check_rate_limit(api_key, rpm_limit=5)
            assert result is True
        
        # Next request should be rate limited
        result = self.auth_db.check_rate_limit(api_key, rpm_limit=5)
        assert result is False
        
        # Verify rate limit records in the database
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rate_limits")
        count = cursor.fetchone()[0]
        assert count == 5  # 5 requests recorded


@pytest.mark.asyncio
class TestAuthDependencies:
    """Test the authentication dependencies."""
    
    @pytest.fixture
    def setup_test_env(self, monkeypatch):
        """Set up test environment with a real SQLite database."""
        # Create an in-memory SQLite database
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        
        # Create the necessary tables
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE api_keys (
            key_id TEXT PRIMARY KEY,
            key_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            is_active BOOLEAN DEFAULT TRUE
        )
        """)
        
        cursor.execute("""
        CREATE TABLE rate_limits (
            key TEXT NOT NULL,
            requests INTEGER DEFAULT 1,
            window_start TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """)
        
        # Add indexes
        cursor.execute("CREATE INDEX idx_rate_limits_key ON rate_limits(key)")
        cursor.execute("CREATE INDEX idx_rate_limits_expires ON rate_limits(expires_at)")
        
        # Create a valid API key for testing
        key_id = str(uuid.uuid4())
        api_key = str(uuid.uuid4())
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        created_at = datetime.now().isoformat()
        
        # Insert the key into the database
        cursor.execute(
            """INSERT INTO api_keys (key_id, key_hash, name, created_at, is_active)
               VALUES (?, ?, ?, ?, ?)""",
            (key_id, key_hash, "test_key", created_at, True)
        )
        conn.commit()
        
        # Create a custom AuthDB class that uses our connection
        class TestAuthDB(AuthDB):
            def __init__(self):
                self.db_type = "sqlite"
                self.db_path = ":memory:"
                self._conn = conn
            
            @contextmanager
            def get_connection(self):
                try:
                    yield self._conn
                finally:
                    pass  # Don't close the connection
        
        # Create a test instance and patch it into the auth module
        test_auth_db = TestAuthDB()
        from src.mcp import auth
        monkeypatch.setattr(auth, "auth_db", test_auth_db)
        
        # Create a mock API_KEY_HEADER for testing
        class MockAPIKeyHeader:
            def __call__(self, request):
                if "X-API-Key" in request.headers:
                    return request.headers["X-API-Key"]
                return None
        
        # Patch the API_KEY_HEADER
        monkeypatch.setattr(auth, "API_KEY_HEADER", MockAPIKeyHeader())
        
        return {
            "api_key": api_key,
            "key_id": key_id,
            "conn": conn,
            "auth_db": test_auth_db
        }
    
    async def test_get_api_key_auth_disabled(self, setup_test_env, monkeypatch):
        """Test API key extraction when auth is disabled."""
        from src.mcp.auth import get_api_key
        from src.mcp import auth
        
        # Disable authentication
        monkeypatch.setattr(auth.config.mcp, "auth_enabled", False)
        
        # Create a mock request with no API key
        class MockRequest:
            headers = {}
        
        # When auth is disabled, it returns a dummy key
        api_key = await get_api_key(MockRequest())
        assert isinstance(api_key, APIKey)
        assert api_key.key_id == "dummy"
        assert api_key.name == "anonymous"
    
    async def test_get_api_key_auth_enabled(self, setup_test_env, monkeypatch):
        """Test API key extraction when auth is enabled."""
        from src.mcp.auth import get_api_key
        from src.mcp import auth
        
        # Enable authentication
        monkeypatch.setattr(auth.config.mcp, "auth_enabled", True)
        
        # Use the API key string directly
        api_key_str = setup_test_env["api_key"]
        
        # Should return the APIKey object
        api_key = await get_api_key(api_key_str)
        assert isinstance(api_key, APIKey)
        assert api_key.name == "test_key"
    
    async def test_get_current_key_auth_disabled(self, setup_test_env, monkeypatch):
        """Test current key validation when auth is disabled."""
        from src.mcp.auth import get_current_key
        from src.mcp import auth
        
        # Disable authentication
        monkeypatch.setattr(auth.config.mcp, "auth_enabled", False)
        
        # When auth is disabled, it returns a dummy key
        api_key = await get_current_key(None)
        assert isinstance(api_key, APIKey)
        assert api_key.key_id == "dummy"
        assert api_key.name == "anonymous"
    
    async def test_get_current_key_auth_enabled_valid(self, setup_test_env, monkeypatch):
        """Test current key validation when auth is enabled with valid key."""
        from src.mcp.auth import get_current_key, get_api_key
        from src.mcp import auth
        
        # Enable authentication
        monkeypatch.setattr(auth.config.mcp, "auth_enabled", True)
        
        # Use the API key string directly
        api_key_str = setup_test_env["api_key"]
        
        # First get the API key
        api_key = await get_api_key(api_key_str)
        
        # Then validate it
        key_obj = await get_current_key(api_key)
        assert isinstance(key_obj, APIKey)
        assert key_obj.name == "test_key"
    
    async def test_get_current_key_auth_enabled_invalid(self, setup_test_env, monkeypatch):
        """Test current key validation when auth is enabled with invalid key."""
        from src.mcp.auth import get_current_key
        from src.mcp import auth
        
        # Enable authentication
        monkeypatch.setattr(auth.config.mcp, "auth_enabled", True)
        
        # Use an invalid API key (None)
        with pytest.raises(HTTPException) as excinfo:
            await get_current_key(None)
        
        # Should raise 401 Unauthorized
        assert excinfo.value.status_code == 401
