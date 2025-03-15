"""
Tests for the MCP authentication module using real PostgreSQL database connections.
"""
import pytest
import uuid
from datetime import datetime, timedelta

# Import the API key model
from src.mcp.auth import APIKey

# Import the pg_conftest fixtures
pytest.importorskip("psycopg2")  # Skip these tests if psycopg2 is not installed

class TestAuthDBRealPG:
    """Test the AuthDB class with real PostgreSQL connections."""

    def test_init_db(self, real_auth_db):
        """Test database initialization."""
        # The real_auth_db fixture already initializes the database
        # We just need to verify the tables exist
        auth_db = real_auth_db["db"]
        conn = real_auth_db["connection"]
        
        with conn.cursor() as cursor:
            # Check if api_keys table exists
            cursor.execute("SELECT to_regclass('public.api_keys')")
            assert cursor.fetchone()[0] == 'api_keys'
            
            # Check if rate_limits table exists
            cursor.execute("SELECT to_regclass('public.rate_limits')")
            assert cursor.fetchone()[0] == 'rate_limits'
            
            # Check if rate_limits index exists
            cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'rate_limits'")
            index_names = [row[0] for row in cursor.fetchall()]
            assert any('idx_rate_limits_key' in name for name in index_names)

    def test_create_api_key(self, real_auth_db):
        """Test API key creation with real database."""
        auth_db = real_auth_db["db"]
        conn = real_auth_db["connection"]
        
        # Create a key with no expiration
        key_id1, api_key1 = auth_db.create_api_key("test_key_1")
        assert key_id1 is not None
        assert api_key1 is not None
        
        # Create a key with expiration
        key_id2, api_key2 = auth_db.create_api_key("test_key_2", expiry_days=30)
        assert key_id2 is not None
        assert api_key2 is not None
        
        # Verify keys were stored
        with conn.cursor() as cursor:
            # Count total keys (including the one from fixture)
            cursor.execute("SELECT COUNT(*) FROM api_keys")
            count = cursor.fetchone()[0]
            assert count == 3  # 1 from fixture + 2 from this test
            
            # Verify expiry is set correctly for test_key_2
            cursor.execute("SELECT expires_at FROM api_keys WHERE name = %s", ("test_key_2",))
            expires_at = cursor.fetchone()[0]
            assert expires_at is not None
            
            # Verify no expiry for test_key_1
            cursor.execute("SELECT expires_at FROM api_keys WHERE name = %s", ("test_key_1",))
            expires_at = cursor.fetchone()[0]
            assert expires_at is None

    def test_validate_api_key(self, real_auth_db):
        """Test API key validation with real database."""
        auth_db = real_auth_db["db"]
        api_key = real_auth_db["api_key"]
        
        # Test valid key
        result = auth_db.validate_api_key(api_key)
        assert result is not None
        assert result.name == "test"
        assert result.is_active is True
        
        # Test invalid key
        result = auth_db.validate_api_key("invalid_key")
        assert result is None
        
        # Create an expired key
        conn = real_auth_db["connection"]
        with conn.cursor() as cursor:
            expired_key_id = str(uuid.uuid4())
            expired_key = f"expired_{uuid.uuid4()}"
            expired_date = (datetime.now() - timedelta(days=1)).isoformat()
            
            cursor.execute(
                "INSERT INTO api_keys (key_id, api_key, name, created_at, expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (expired_key_id, expired_key, "expired_test", datetime.now().isoformat(), expired_date, True)
            )
            conn.commit()
        
        # Test expired key
        result = auth_db.validate_api_key(expired_key)
        assert result is None

    def test_check_rate_limit(self, real_auth_db):
        """Test rate limiting with real database."""
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
        
        # Manually reset rate limit for testing
        conn = real_auth_db["connection"]
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM rate_limits WHERE key_id = %s", (key_id,))
            conn.commit()
        
        # After reset, request should be allowed again
        assert auth_db.check_rate_limit(key_id, max_requests=5, period_minutes=1) is None


class TestAuthDependenciesRealPG:
    """Test the authentication dependencies with real PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_get_api_key_auth_disabled(self, real_server_auth, monkeypatch):
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
    
    @pytest.mark.asyncio
    async def test_get_api_key_auth_enabled(self, real_server_auth, monkeypatch):
        """Test API key extraction when auth is enabled."""
        from src.mcp.auth import get_api_key
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Create a mock request with API key
        api_key = real_server_auth["api_key"]
        class MockRequest:
            headers = {"X-API-Key": api_key}
        
        # Should return the API key
        extracted_key = await get_api_key(MockRequest())
        assert extracted_key == api_key
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_disabled(self, real_server_auth, monkeypatch):
        """Test current key validation when auth is disabled."""
        from src.mcp.auth import get_current_key
        
        # Disable authentication
        monkeypatch.setenv("ENABLE_AUTH", "false")
        
        # Should return None when auth is disabled
        api_key = await get_current_key(None)
        assert api_key is None
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_enabled_valid(self, real_server_auth, monkeypatch):
        """Test current key validation when auth is enabled with valid key."""
        from src.mcp.auth import get_current_key
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Use a valid API key
        api_key = real_server_auth["api_key"]
        
        # Should return an APIKey object
        key_obj = await get_current_key(api_key)
        assert isinstance(key_obj, APIKey)
        assert key_obj.name == "test"
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_enabled_invalid(self, real_server_auth, monkeypatch):
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
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_disabled(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is disabled."""
        from src.mcp.auth import check_rate_limit
        
        # Disable authentication
        monkeypatch.setenv("ENABLE_AUTH", "false")
        
        # Should not rate limit when auth is disabled
        await check_rate_limit(None)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_enabled_within_limit(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is enabled and within limit."""
        from src.mcp.auth import check_rate_limit
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Create a valid APIKey object
        api_key = real_server_auth["api_key"]
        key_id = real_server_auth["auth_db"].validate_api_key(api_key).key_id
        api_key_obj = APIKey(
            key_id=key_id,
            name="test",
            created_at=datetime.now().isoformat(),
            is_active=True
        )
        
        # Reset rate limits for this test
        conn = real_server_auth["auth_db"].connection
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM rate_limits WHERE key_id = %s", (key_id,))
            conn.commit()
        
        # Should not rate limit when within limit
        await check_rate_limit(api_key_obj)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_enabled_exceeded_limit(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is enabled and limit exceeded."""
        from src.mcp.auth import check_rate_limit
        from fastapi import HTTPException
        
        # Enable authentication
        monkeypatch.setenv("ENABLE_AUTH", "true")
        
        # Create a valid APIKey object
        api_key = real_server_auth["api_key"]
        key_id = real_server_auth["auth_db"].validate_api_key(api_key).key_id
        api_key_obj = APIKey(
            key_id=key_id,
            name="test",
            created_at=datetime.now().isoformat(),
            is_active=True
        )
        
        # Manually set rate limit to exceeded
        auth_db = real_server_auth["auth_db"]
        conn = auth_db.connection
        
        # First, clear any existing rate limits
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM rate_limits WHERE key_id = %s", (key_id,))
            conn.commit()
        
        # Then add enough requests to exceed the limit
        for _ in range(10):  # Default is 5 requests per minute
            auth_db.check_rate_limit(key_id)
        
        # Should rate limit when limit exceeded
        with pytest.raises(HTTPException) as excinfo:
            await check_rate_limit(api_key_obj)
        
        # Should raise 429 Too Many Requests
        assert excinfo.value.status_code == 429
