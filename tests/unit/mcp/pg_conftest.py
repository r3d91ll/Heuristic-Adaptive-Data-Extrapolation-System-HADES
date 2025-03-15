"""
PostgreSQL-specific pytest fixtures for MCP server tests.
This file contains fixtures that use real PostgreSQL connections instead of mocks.
"""
import os
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Import the AuthDB class and APIKey model from the MCP module
from src.mcp.auth import AuthDB, APIKey

# Try to import test environment variables from setup script
try:
    from tests.pg_test_env import PG_TEST_PARAMS as DEFAULT_PG_PARAMS
except ImportError:
    # Default connection parameters if setup script hasn't been run
    import getpass
    system_user = getpass.getuser()  # This will be 'todd' on your system
    
    DEFAULT_PG_PARAMS = {
        "dbname": "hades_test",
        "user": system_user,  # Use system username for peer authentication
        "password": "",  # Empty password for peer authentication
        "host": "localhost",
        "port": "5432"
    }

def get_pg_params():
    """Get PostgreSQL connection parameters from environment or defaults."""
    # First check environment variables
    params = {
        "dbname": os.environ.get("PGDATABASE") or os.environ.get("HADES_TEST_DB_NAME", DEFAULT_PG_PARAMS["dbname"]),
        "user": os.environ.get("PGUSER") or os.environ.get("HADES_TEST_DB_USER", DEFAULT_PG_PARAMS["user"]),
        "password": os.environ.get("PGPASSWORD") or os.environ.get("HADES_TEST_DB_PASSWORD", DEFAULT_PG_PARAMS["password"]),
        "host": os.environ.get("PGHOST") or os.environ.get("HADES_TEST_DB_HOST", DEFAULT_PG_PARAMS["host"]),
        "port": os.environ.get("PGPORT") or os.environ.get("HADES_TEST_DB_PORT", DEFAULT_PG_PARAMS["port"])
    }
    
    return params

@pytest.fixture(scope="session")
def pg_connection_params():
    """Return PostgreSQL connection parameters."""
    return get_pg_params()

@pytest.fixture(scope="session")
def create_test_database(pg_connection_params):
    """Create the test database if it doesn't exist."""
    # Connect to default postgres database to create our test database
    params = pg_connection_params.copy()
    params["dbname"] = "postgres"
    
    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if test database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (pg_connection_params["dbname"],))
        if not cursor.fetchone():
            # Create test database
            cursor.execute(f"CREATE DATABASE {pg_connection_params['dbname']}")
            print(f"Created test database: {pg_connection_params['dbname']}")
        
        cursor.close()
        conn.close()
        
        # Return success
        return True
    except Exception as e:
        print(f"Error creating test database: {e}")
        return False

@pytest.fixture(scope="session")
def real_pg_connection(create_test_database, pg_connection_params):
    """Create a real PostgreSQL connection for testing."""
    if not create_test_database:
        pytest.skip("Could not create test database")
    
    try:
        # Connect to test database
        conn = psycopg2.connect(**pg_connection_params)
        yield conn
        
        # Cleanup after tests
        conn.close()
    except Exception as e:
        pytest.skip(f"Could not connect to PostgreSQL: {e}")

@pytest.fixture
def real_auth_db(real_pg_connection):
    """Create a real AuthDB instance with test database connection."""
    # Initialize the database tables
    auth_db = AuthDB(connection=real_pg_connection)
    auth_db.init_db()
    
    # Create a test API key for use in tests
    key_id, api_key = auth_db.create_api_key("test")
    
    # Return both the AuthDB instance and the test API key
    result = {
        "db": auth_db,
        "api_key": api_key,
        "key_id": key_id,
        "connection": real_pg_connection
    }
    
    yield result
    
    # Clean up tables after tests
    with real_pg_connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE api_keys CASCADE")
        cursor.execute("TRUNCATE TABLE rate_limits CASCADE")
    real_pg_connection.commit()

@pytest.fixture
def real_server_auth(real_auth_db):
    """Create a patch for server authentication using real database."""
    from fastapi import Depends, Request
    from src.mcp.auth import get_api_key, get_current_key, check_rate_limit
    
    # Create a real API key for testing
    auth_db = real_auth_db["db"]
    api_key = real_auth_db["api_key"]
    
    # Return the real auth_db and API key
    return {
        "auth_db": auth_db,
        "api_key": api_key
    }
