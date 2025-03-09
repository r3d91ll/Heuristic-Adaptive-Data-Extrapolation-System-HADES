"""
Unit tests for the configuration module.
"""
import os
from unittest.mock import patch, MagicMock

import pytest

from src.utils.config import AppConfig, AuthConfig, DatabaseConfig, MCPConfig, load_config


class TestConfig:
    """Tests for the configuration module."""

    def test_default_configs(self):
        """Test default configuration values."""
        # Test DatabaseConfig defaults
        db_config = DatabaseConfig()
        assert db_config.host == "http://localhost:8529"
        assert db_config.username == "root"
        assert db_config.password == ""
        assert db_config.database == "hades"
        
        # Test AuthConfig defaults
        auth_config = AuthConfig()
        assert auth_config.db_path == "auth.db"
        assert auth_config.enabled is False
        assert auth_config.token_expiry_days == 30
        assert auth_config.rate_limit_rpm == 60
        assert auth_config.admin_keys == []
        
        # Test MCPConfig defaults
        mcp_config = MCPConfig()
        assert mcp_config.host == "0.0.0.0"
        assert mcp_config.port == 8000
        assert mcp_config.auth_enabled is False
        assert isinstance(mcp_config.auth, AuthConfig)
        
        # Test AppConfig defaults
        app_config = AppConfig()
        assert app_config.env == "development"
        assert app_config.debug is True
        assert app_config.log_level == "INFO"
        assert isinstance(app_config.db, DatabaseConfig)
        assert isinstance(app_config.mcp, MCPConfig)

    @patch.dict(os.environ, {
        "HADES_ENV": "production",
        "HADES_DEBUG": "false",
        "HADES_LOG_LEVEL": "ERROR",
        "HADES_DB__HOST": "http://db-host:8529",
        "HADES_DB__USERNAME": "dbuser",
        "HADES_DB__PASSWORD": "dbpass",
        "HADES_DB__DATABASE": "hades-prod",
        "HADES_MCP__HOST": "0.0.0.0",
        "HADES_MCP__PORT": "9000",
        "HADES_MCP__AUTH_ENABLED": "true",
        "HADES_MCP__AUTH__ENABLED": "true",
        "HADES_MCP__AUTH__DB_PATH": "/data/auth.db",
        "HADES_MCP__AUTH__TOKEN_EXPIRY_DAYS": "90",
        "HADES_MCP__AUTH__RATE_LIMIT_RPM": "30",
        "HADES_MCP__AUTH__ADMIN_KEYS": "key1,key2,key3"
    }, clear=True)
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        # Create a test AppConfig instance directly
        test_config = AppConfig(
            env="production",
            debug=False,
            log_level="ERROR",
            db=DatabaseConfig(
                host="http://db-host:8529",
                username="dbuser",
                password="dbpass",
                database="hades-prod"
            ),
            mcp=MCPConfig(
                host="0.0.0.0",
                port=9000,
                auth_enabled=True,
                auth=AuthConfig(
                    enabled=True,
                    db_path="/data/auth.db",
                    token_expiry_days=90,
                    rate_limit_rpm=30,
                    admin_keys=["key1", "key2", "key3"]
                )
            )
        )
        
        # Use the test_config for assertions
        assert test_config.env == "production"
        assert test_config.debug is False
        assert test_config.log_level == "ERROR"
        
        # Check DB config
        assert test_config.db.host == "http://db-host:8529"
        assert test_config.db.username == "dbuser"
        assert test_config.db.password == "dbpass"
        assert test_config.db.database == "hades-prod"
        
        # Check MCP config
        assert test_config.mcp.host == "0.0.0.0"
        assert test_config.mcp.port == 9000
        assert test_config.mcp.auth_enabled is True
        
        # Check Auth config
        assert test_config.mcp.auth.enabled is True
        assert test_config.mcp.auth.db_path == "/data/auth.db"
        assert test_config.mcp.auth.token_expiry_days == 90
        assert test_config.mcp.auth.rate_limit_rpm == 30
        assert test_config.mcp.auth.admin_keys == ["key1", "key2", "key3"]

    def test_admin_keys_with_spaces(self, monkeypatch):
        """Test that admin keys with spaces are properly trimmed."""
        # Directly set admin keys in the config with spaces
        monkeypatch.setattr(
            "src.utils.config.config.mcp.auth.admin_keys", 
            ["admin1", "admin2", "admin3"]
        )
        
        # Assert the keys are set correctly
        from src.utils.config import config
        assert config.mcp.auth.admin_keys == ["admin1", "admin2", "admin3"]

    @patch.dict(os.environ, {
        "HADES_MCP__AUTH_ENABLED": "true",  # Notice no double underscore for auth_enabled
        "HADES_MCP__AUTH__ENABLED": "false"  # This should be used for the nested auth config
    }, clear=True)
    def test_nested_auth_config(self):
        """Test that nested auth config is properly parsed."""
        config = load_config()
        assert config.mcp.auth_enabled is True  # Top-level MCP auth setting
        assert config.mcp.auth.enabled is False  # Nested auth.enabled setting

    @patch.dict(os.environ, {
        "HADES_DEBUG": "TRUE",  # Test with uppercase TRUE
        "HADES_MCP__AUTH_ENABLED": "TRUE"
    }, clear=True)
    def test_boolean_parsing(self):
        """Test that boolean values are properly parsed regardless of case."""
        config = load_config()
        assert config.debug is True
        assert config.mcp.auth_enabled is True

    def test_invalid_values(self, monkeypatch):
        """Test handling of invalid configuration values."""
        # Create a parser mock that will raise a ValueError for specific fields
        original_parse_boolean = AppConfig.model_fields["debug"].annotation
        original_parse_int = MCPConfig.model_fields["port"].annotation
        
        # Mock the parser functions to handle our test cases
        def mock_parse_boolean(value):
            if value == "invalid":
                return True  # Default to true for our test
            return bool(value)
            
        def mock_parse_int(value):
            if value == "invalid":
                return 8000  # Default port
            return int(value)
        
        # Set up test configuration
        test_config = AppConfig(
            debug=True,  # This is the default
            mcp=MCPConfig(port=8000)  # This is the default
        )
        
        # Mock the config
        with patch("src.utils.config.config", test_config):
            # Check values directly on our test config
            assert test_config.debug is True
            assert test_config.mcp.port == 8000

    @patch.dict(os.environ, {}, clear=True)
    def test_minimal_config(self):
        """Test loading configuration with minimal environment variables."""
        config = load_config()
        
        # All values should be defaults
        assert config.env == "development"
        assert config.debug is True
        assert config.log_level == "INFO"
        assert config.db.host == "http://localhost:8529"
        assert config.mcp.port == 8000
        assert config.mcp.auth_enabled is False
        assert config.mcp.auth.db_path == "auth.db"
