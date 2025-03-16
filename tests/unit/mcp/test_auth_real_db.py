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
            assert any('idx_rate_limits_key_id' in name for name in index_names)

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
            # Hash the key as done in the AuthDB class
            import hashlib
            key_hash = hashlib.sha256(expired_key.encode()).hexdigest()
            expired_date = (datetime.now() - timedelta(days=1))
            
            cursor.execute(
                "INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (expired_key_id, key_hash, "expired_test", datetime.now(), expired_date, True)
            )
            conn.commit()
        
        # Test expired key
        result = auth_db.validate_api_key(expired_key)
        assert result is None

    def test_check_rate_limit(self, real_auth_db):
        """Test rate limiting with real database."""
        auth_db = real_auth_db["db"]
        api_key = real_auth_db["api_key"]
        
        # First request should be allowed
        assert auth_db.check_rate_limit(api_key, rpm_limit=5) is True
        
        # Make multiple requests
        for _ in range(4):
            assert auth_db.check_rate_limit(api_key, rpm_limit=5) is True
        
        # Next request should be rate limited
        result = auth_db.check_rate_limit(api_key, rpm_limit=5)
        assert result is False
        
        # Manually reset rate limit for testing
        conn = real_auth_db["connection"]
        with conn.cursor() as cursor:
            # Hash the key as done in the AuthDB class
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            cursor.execute("DELETE FROM rate_limits WHERE key_id = %s", (key_hash,))
            conn.commit()
        
        # After reset, request should be allowed again
        assert auth_db.check_rate_limit(api_key, rpm_limit=5) is True


class TestAuthDependenciesRealPG:
    """Test the authentication dependencies with real PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_get_api_key_auth_disabled(self, real_server_auth, monkeypatch):
        """Test API key extraction when auth is disabled."""
        from src.mcp.auth import get_api_key
        from src.utils.config import config
        
        # Disable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", False)
        
        # Create a mock request with no API key
        class MockRequest:
            headers = {}
        
        # Should return a dummy key when auth is disabled
        api_key = await get_api_key("")
        assert api_key is not None
        assert api_key.key_id == "dummy"
        assert api_key.name == "anonymous"
    
    @pytest.mark.asyncio
    async def test_get_api_key_auth_enabled(self, real_server_auth, monkeypatch):
        """Test API key extraction when auth is enabled."""
        from src.mcp.auth import get_api_key, auth_db
        from src.utils.config import config
        
        # Enable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", True)
        
        # Patch the global auth_db instance to use our test database
        original_auth_db = auth_db
        monkeypatch.setattr("src.mcp.auth.auth_db", real_server_auth["auth_db"])
        
        try:
            # Use the API key from the fixture
            api_key = real_server_auth["api_key"]
            
            # Should return a valid APIKey object
            result = await get_api_key(api_key)
            assert result is not None
            assert result.name == "test"
        finally:
            # Restore the original auth_db instance
            monkeypatch.setattr("src.mcp.auth.auth_db", original_auth_db)
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_disabled(self, real_server_auth, monkeypatch):
        """Test current key validation when auth is disabled."""
        from src.mcp.auth import get_current_key
        from src.utils.config import config
        
        # Disable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", False)
        
        # Should return a dummy key when auth is disabled
        api_key = await get_current_key(None)
        assert api_key is not None
        assert api_key.key_id == "dummy"
        assert api_key.name == "anonymous"
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_enabled_valid(self, real_server_auth, monkeypatch):
        """Test current key validation when auth is enabled with valid key."""
        from src.mcp.auth import get_current_key
        from src.utils.config import config
        
        # Enable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", True)
        
        # Create a valid APIKey object
        from src.mcp.auth import APIKey
        valid_key = APIKey(
            key_id=real_server_auth["key_id"],
            name="test",
            created_at=datetime.now()
        )
        
        # Should return the same APIKey object
        key_obj = await get_current_key(valid_key)
        assert key_obj is valid_key
        assert key_obj.name == "test"
    
    @pytest.mark.asyncio
    async def test_get_current_key_auth_enabled_invalid(self, real_server_auth, monkeypatch):
        """Test current key validation when auth is enabled with invalid key."""
        from src.mcp.auth import get_current_key
        from src.utils.config import config
        from fastapi import HTTPException
        
        # Enable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", True)
        
        # Pass None as the API key
        invalid_key = None
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await get_current_key(invalid_key)
        
        # Verify the exception details
        assert excinfo.value.status_code == 401
        assert "Invalid or missing API key" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_disabled(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is disabled."""
        from src.mcp.auth import check_rate_limit
        from src.utils.config import config
        from fastapi import Request
        
        # Disable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", False)
        
        # Create a mock request
        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Key": "dummy_key"}
        
        # Create a valid APIKey object
        from src.mcp.auth import APIKey
        api_key = APIKey(
            key_id="dummy",
            name="test",
            created_at=datetime.now()
        )
        
        # Should not raise an exception when auth is disabled
        mock_request = MockRequest()
        result = await check_rate_limit(mock_request, api_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_enabled_within_limit(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is enabled and within limit."""
        from src.mcp.auth import check_rate_limit, auth_db
        from src.utils.config import config
        from fastapi import Request
        
        # Enable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", True)
        
        # Create a valid APIKey object
        api_key = real_server_auth["api_key"]
        key_id = real_server_auth["key_id"]
        api_key_obj = APIKey(
            key_id=key_id,
            name="test",
            created_at=datetime.now(),
            is_active=True
        )
        
        # Create a mock request with API key
        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Key": api_key}
        
        # Reset rate limits for this test
        conn = real_server_auth["connection"]
        with conn.cursor() as cursor:
            # Hash the key as done in the AuthDB class
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            cursor.execute("DELETE FROM rate_limits WHERE key_id = %s", (key_hash,))
            conn.commit()
        
        # Patch the rate limit check to always return True
        original_check = auth_db.check_rate_limit
        monkeypatch.setattr(auth_db, "check_rate_limit", lambda key, **kwargs: True)
        
        # Should not raise an exception
        mock_request = MockRequest()
        result = await check_rate_limit(mock_request, api_key_obj)
        assert result is None
        
        # Restore the original method
        monkeypatch.setattr(auth_db, "check_rate_limit", original_check)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_auth_enabled_exceeded_limit(self, real_server_auth, monkeypatch):
        """Test rate limiting when auth is enabled and limit exceeded."""
        from src.mcp.auth import check_rate_limit, auth_db
        from src.utils.config import config
        from fastapi import HTTPException, Request
        
        # Enable authentication
        monkeypatch.setattr(config.mcp, "auth_enabled", True)
        
        # Create a valid APIKey object
        api_key = real_server_auth["api_key"]
        key_id = real_server_auth["key_id"]
        api_key_obj = APIKey(
            key_id=key_id,
            name="test",
            created_at=datetime.now(),
            is_active=True
        )
        
        # Create a mock request with API key
        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Key": api_key}
        
        # Patch the rate limit check to always return False (rate limit exceeded)
        original_check = auth_db.check_rate_limit
        monkeypatch.setattr(auth_db, "check_rate_limit", lambda key, **kwargs: False)
        
        # Should raise HTTPException with status code 429
        with pytest.raises(HTTPException) as excinfo:
            mock_request = MockRequest()
            await check_rate_limit(mock_request, api_key_obj)
        
        # Verify the exception details
        assert excinfo.value.status_code == 429
        assert "Rate limit exceeded" in excinfo.value.detail
        
        # Restore the original method
        monkeypatch.setattr(auth_db, "check_rate_limit", original_check)
