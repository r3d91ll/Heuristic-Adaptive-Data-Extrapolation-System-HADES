"""
Unit tests for the MCP authentication module.
"""
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
pytest.importorskip("pytest_asyncio")
import pytest_asyncio
from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader

from src.mcp.auth import (APIKey, AuthDB, auth_db, check_rate_limit,
                          get_api_key, get_current_key)


class TestAuthDB:
    """Tests for the AuthDB class."""

    def test_init_db(self, auth_db_setup):
        """Test database initialization."""
        # Use the initialized in-memory database from the fixture
        conn = auth_db_setup["conn"]
        cursor = conn.cursor()
        
        # Set row_factory to enable dictionary access
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cursor = conn.cursor()
        
        # Check if the tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limits'"
        )
        assert cursor.fetchone() is not None
        
        # Check if indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rate_limits_key'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rate_limits_expires'"
        )
        assert cursor.fetchone() is not None

    def test_create_api_key(self, auth_db_setup):
        """Test API key creation."""
        test_db = auth_db_setup["db"]
        
        # Create a key with no expiration
        key_id1, api_key1 = test_db.create_api_key("test_key_1")
        assert key_id1 is not None
        assert api_key1 is not None
        
        # Create a key with expiration
        key_id2, api_key2 = test_db.create_api_key("test_key_2", expiry_days=30)
        assert key_id2 is not None
        assert api_key2 is not None
        
        # Verify keys were stored
        with test_db.get_connection() as conn:
            # Set row_factory to enable dictionary access
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM api_keys")
            row = cursor.fetchone()
            assert row["count"] == 3  # Including the key created in the fixture
            
            # Verify expiry is set correctly
            cursor.execute("SELECT expires_at FROM api_keys WHERE name = ?", ("test_key_2",))
            row = cursor.fetchone()
            assert row["expires_at"] is not None
            
            # Verify no expiry
            cursor.execute("SELECT expires_at FROM api_keys WHERE name = ?", ("test_key_1",))
            row = cursor.fetchone()
            assert row["expires_at"] is None

    def test_validate_api_key(self, auth_db_setup):
        """Test API key validation."""
        test_db = auth_db_setup["db"]
        api_key = auth_db_setup["api_key"]
        
        # Test valid key
        result = test_db.validate_api_key(api_key)
        assert result is not None
        assert result.name == "test"
        assert result.is_active is True
        
        # Test invalid key
        result = test_db.validate_api_key("invalid_key")
        assert result is None
        
        # Test empty key
        result = test_db.validate_api_key("")
        assert result is None
        
        # Create an expired key
        expired_name = "expired_key"
        expired_date = (datetime.now() - timedelta(days=1)).isoformat()
        key_id = str(uuid.uuid4())
        expired_key = str(uuid.uuid4())
        key_hash = hashlib.sha256(expired_key.encode()).hexdigest()
        
        with test_db.get_connection() as conn:
            # Set row_factory to enable dictionary access
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO api_keys 
                (key_id, key_hash, name, created_at, expires_at, is_active) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key_id, key_hash, expired_name, datetime.now().isoformat(), expired_date, True)
            )
            conn.commit()
        
        # Test expired key
        result = test_db.validate_api_key(expired_key)
        assert result is None
        
        # Create an inactive key
        inactive_name = "inactive_key"
        inactive_key = str(uuid.uuid4())
        key_hash = hashlib.sha256(inactive_key.encode()).hexdigest()
        
        with test_db.get_connection() as conn:
            # Set row_factory to enable dictionary access
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO api_keys 
                (key_id, key_hash, name, created_at, expires_at, is_active) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), key_hash, inactive_name, datetime.now().isoformat(), None, False)
            )
            conn.commit()
        
        # Test inactive key
        result = test_db.validate_api_key(inactive_key)
        assert result is None

    def test_check_rate_limit(self, auth_db_setup):
        """Test rate limiting."""
        test_db = auth_db_setup["db"]
        api_key = auth_db_setup["api_key"]
        
        # Test within limit
        assert test_db.check_rate_limit(api_key, rpm_limit=10) is True
        
        # Generate multiple requests
        for i in range(9):  # We already have 1 request, so 9 more = 10 total
            assert test_db.check_rate_limit(api_key, rpm_limit=10) is True
        
        # This should exceed the limit
        assert test_db.check_rate_limit(api_key, rpm_limit=10) is False
        
        # Test empty key
        assert test_db.check_rate_limit("", rpm_limit=10) is False
        
        # Test rate limit cleanup
        with test_db.get_connection() as conn:
            # Set row_factory to enable dictionary access
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()
            
            # Set all rate limits to be expired
            cursor.execute(
                "UPDATE rate_limits SET expires_at = ?", 
                ((datetime.now() - timedelta(minutes=10)).isoformat(),)
            )
            conn.commit()
        
        # After cleanup, we should be able to make requests again
        assert test_db.check_rate_limit(api_key, rpm_limit=10) is True


class TestAuthDependencies:
    """Tests for the FastAPI authentication dependencies."""

    @pytest_asyncio.fixture
    async def mock_request(self):
        """Create a mock request for testing."""
        mock_req = MagicMock(spec=Request)
        mock_req.headers = {"X-API-Key": "test-key"}
        return mock_req
        
    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_get_api_key_auth_disabled(self, mock_config):
        """Test get_api_key when auth is disabled."""
        # Mock config to disable auth
        mock_config.mcp.auth_enabled = False
        
        # Call dependency function
        result = await get_api_key("some_key")
        
        # Should return a dummy key
        assert result is not None
        assert result.key_id == "dummy"
        assert result.name == "anonymous"

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    @patch("src.mcp.auth.auth_db")
    async def test_get_api_key_auth_enabled(self, mock_auth_db, mock_config):
        """Test get_api_key when auth is enabled."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Mock validation to return a valid key
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        mock_auth_db.validate_api_key.return_value = valid_key
        
        # Call dependency function
        result = await get_api_key("valid_key")
        
        # Should return the validated key
        assert result == valid_key
        mock_auth_db.validate_api_key.assert_called_once_with("valid_key")
        
        # Test with invalid key
        mock_auth_db.validate_api_key.reset_mock()
        mock_auth_db.validate_api_key.return_value = None
        
        result = await get_api_key("invalid_key")
        assert result is None
        mock_auth_db.validate_api_key.assert_called_once_with("invalid_key")

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_get_current_key_auth_disabled(self, mock_config):
        """Test get_current_key when auth is disabled."""
        # Mock config to disable auth
        mock_config.mcp.auth_enabled = False
        
        # Call dependency function
        result = await get_current_key(None)
        
        # Should return a dummy key
        assert result is not None
        assert result.key_id == "dummy"
        assert result.name == "anonymous"

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_get_current_key_auth_enabled_valid(self, mock_config):
        """Test get_current_key with valid key when auth is enabled."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Create a valid API key
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        
        # Call dependency function
        result = await get_current_key(valid_key)
        
        # Should return the valid key
        assert result == valid_key

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_get_current_key_auth_enabled_invalid(self, mock_config):
        """Test get_current_key with invalid key when auth is enabled."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Call dependency function with invalid key (None)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_key(None)
        
        # Should raise 401 Unauthorized
        assert exc_info.value.status_code == 401
        assert "Invalid or missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_check_rate_limit_auth_disabled(self, mock_config):
        """Test check_rate_limit when auth is disabled."""
        # Mock config to disable auth
        mock_config.mcp.auth_enabled = False
        
        # Create mock request and API key
        mock_request = MagicMock(spec=Request)
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        
        # Call dependency function
        # Should not raise an exception
        await check_rate_limit(mock_request, valid_key)

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    @patch("src.mcp.auth.auth_db")
    async def test_check_rate_limit_auth_enabled_within_limit(self, mock_auth_db, mock_config):
        """Test check_rate_limit when within rate limit."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Create mock request with API key in headers
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "valid_key"}
        
        # Create a valid API key
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        
        # Mock check_rate_limit to return True
        mock_auth_db.check_rate_limit.return_value = True
        
        # Call dependency function
        # Should not raise an exception
        await check_rate_limit(mock_request, valid_key)
        
        # Verify rate limit check was called
        mock_auth_db.check_rate_limit.assert_called_once_with("valid_key")

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    @patch("src.mcp.auth.auth_db")
    async def test_check_rate_limit_auth_enabled_exceeded_limit(self, mock_auth_db, mock_config):
        """Test check_rate_limit when rate limit is exceeded."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Create mock request with API key in headers
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "valid_key"}
        
        # Create a valid API key
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        
        # Mock check_rate_limit to return False (limit exceeded)
        mock_auth_db.check_rate_limit.return_value = False
        
        # Call dependency function
        # Should raise 429 Too Many Requests
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(mock_request, valid_key)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        
        # Verify rate limit check was called
        mock_auth_db.check_rate_limit.assert_called_once_with("valid_key")

    @pytest.mark.asyncio
    @patch("src.mcp.auth.config")
    async def test_check_rate_limit_auth_enabled_missing_key(self, mock_config):
        """Test check_rate_limit when API key is missing from headers."""
        # Mock config to enable auth
        mock_config.mcp.auth_enabled = True
        
        # Create mock request with no API key in headers
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        
        # Create a valid API key
        valid_key = APIKey(
            key_id="test_id",
            name="test_name",
            created_at=datetime.now(),
        )
        
        # Call dependency function
        # Should raise 401 Unauthorized
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(mock_request, valid_key)
        
        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail
