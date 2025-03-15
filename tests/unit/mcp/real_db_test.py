"""
Tests for the MCP authentication module using real PostgreSQL database connections.
This file contains a simplified approach to testing with real database connections.
"""
import os
import pytest
import uuid
from datetime import datetime, timedelta

# Import the API key model
from src.mcp.auth import APIKey, AuthDB
from src.utils.config import config

# Skip these tests if psycopg2 is not installed
pytest.importorskip("psycopg2")

# Set environment variables for testing
os.environ["HADES_ENV"] = "test"

@pytest.fixture(scope="module")
def real_auth_db():
    """Create a real AuthDB instance for testing."""
    # Use the actual AuthDB class with its fallback mechanism
    # If PostgreSQL is not available, it will fall back to SQLite in-memory
    auth_db = AuthDB()
    
    # Explicitly initialize the database tables
    auth_db.init_db()
    
    # Create a test API key
    key_id, api_key = auth_db.create_api_key("test_key")
    
    # Return both the AuthDB instance and the test API key
    yield {
        "db": auth_db,
        "api_key": api_key,
        "key_id": key_id
    }
    
    # Clean up is handled by the SQLite in-memory database
    # which is discarded after the tests

class TestRealAuthDB:
    """Test the AuthDB class with real database connections."""

    def test_create_api_key(self, real_auth_db):
        """Test API key creation."""
        auth_db = real_auth_db["db"]
        
        # Create a key with no expiration
        key_id1, api_key1 = auth_db.create_api_key("test_key_1")
        assert key_id1 is not None
        assert api_key1 is not None
        
        # Create a key with expiration
        key_id2, api_key2 = auth_db.create_api_key("test_key_2", expiry_days=30)
        assert key_id2 is not None
        assert api_key2 is not None
        
        # Validate the keys
        key1 = auth_db.validate_api_key(api_key1)
        assert key1 is not None
        assert key1.name == "test_key_1"
        assert key1.expires_at is None
        
        key2 = auth_db.validate_api_key(api_key2)
        assert key2 is not None
        assert key2.name == "test_key_2"
        assert key2.expires_at is not None

    def test_validate_api_key(self, real_auth_db):
        """Test API key validation."""
        auth_db = real_auth_db["db"]
        api_key = real_auth_db["api_key"]
        
        # Test valid key
        result = auth_db.validate_api_key(api_key)
        assert result is not None
        assert result.name == "test_key"
        assert result.is_active is True
        
        # Test invalid key
        result = auth_db.validate_api_key("invalid_key")
        assert result is None

    def test_check_rate_limit(self, real_auth_db):
        """Test rate limiting."""
        auth_db = real_auth_db["db"]
        key_id = real_auth_db["key_id"]
        
        # First request should be allowed
        assert auth_db.check_rate_limit(key_id, max_requests=5, period_minutes=1) is None
        
        # Make multiple requests
        for _ in range(4):
            assert auth_db.check_rate_limit(key_id, max_requests=5, period_minutes=1) is None
        
        # Next request should be rate limited
        reset_time = auth_db.check_rate_limit(key_id, max_requests=5, period_minutes=1)
        assert reset_time is not None
        assert isinstance(reset_time, datetime)

@pytest.mark.asyncio
class TestRealAuthDependencies:
    """Test the authentication dependencies with real database."""
    
    async def test_get_api_key_auth_disabled(self, real_auth_db, monkeypatch):
        """Test API key extraction when auth is disabled."""
        from src.mcp.auth import get_api_key
        
        # Disable authentication
        monkeypatch.setenv("ENABLE_AUTH", "false")
        
        # Create a mock request with no API key
        class MockRequest:
            headers = {}
        
        # Should return None when auth is disabled
        api_key = await get_api_key(MockRequest())
        assert api_key is None
    
    async def test_get_api_key_auth_enabled(self, real_auth_db, monkeypatch):
        """Test API key extraction when auth is enabled."""
        from src.mcp.auth import get_api_key
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Create a mock request with API key
        api_key = real_auth_db["api_key"]
        class MockRequest:
            headers = {"X-API-Key": api_key}
        
        # Should return the API key
        extracted_key = await get_api_key(MockRequest())
        assert extracted_key == api_key
    
    async def test_get_current_key_auth_disabled(self, real_auth_db, monkeypatch):
        """Test current key validation when auth is disabled."""
        from src.mcp.auth import get_current_key
        
        # Disable authentication
        monkeypatch.setenv("ENABLE_AUTH", "false")
        
        # Should return None when auth is disabled
        api_key = await get_current_key(None)
        assert api_key is None
    
    async def test_get_current_key_auth_enabled_valid(self, real_auth_db, monkeypatch):
        """Test current key validation when auth is enabled with valid key."""
        from src.mcp.auth import get_current_key
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Use a valid API key
        api_key = real_auth_db["api_key"]
        
        # Should return an APIKey object
        key_obj = await get_current_key(api_key)
        assert isinstance(key_obj, APIKey)
        assert key_obj.name == "test_key"
    
    async def test_get_current_key_auth_enabled_invalid(self, real_auth_db, monkeypatch):
        """Test current key validation when auth is enabled with invalid key."""
        from src.mcp.auth import get_current_key
        from fastapi import HTTPException
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Use an invalid API key
        with pytest.raises(HTTPException) as excinfo:
            await get_current_key("invalid_key")
        
        # Should raise 401 Unauthorized
        assert excinfo.value.status_code == 401
    
    async def test_check_rate_limit_auth_disabled(self, real_auth_db, monkeypatch):
        """Test rate limiting when auth is disabled."""
        from src.mcp.auth import check_rate_limit
        
        # Disable authentication
        monkeypatch.setenv("ENABLE_AUTH", "false")
        
        # Should not rate limit when auth is disabled
        await check_rate_limit(None)
    
    async def test_check_rate_limit_auth_enabled_within_limit(self, real_auth_db, monkeypatch):
        """Test rate limiting when auth is enabled and within limit."""
        from src.mcp.auth import check_rate_limit
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Create a valid APIKey object
        api_key = real_auth_db["api_key"]
        auth_db = real_auth_db["db"]
        key_obj = auth_db.validate_api_key(api_key)
        
        # Should not rate limit when within limit
        await check_rate_limit(key_obj)
