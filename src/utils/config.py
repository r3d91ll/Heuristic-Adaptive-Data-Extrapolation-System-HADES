"""
Configuration management for HADES.
"""
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseConfig(BaseModel):
    """ArangoDB configuration."""
    host: str = Field(default="http://localhost:8529")
    username: str = Field(default="root")
    password: str = Field(default="")
    database: str = Field(default="hades")


class PostgreSQLConfig(BaseModel):
    """PostgreSQL configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    username: str = Field(default="hades")
    password: str = Field(default="")
    database: str = Field(default="hades_auth")


class AuthConfig(BaseModel):
    """Authentication configuration."""
    db_type: str = Field(default="postgresql")  # "sqlite" or "postgresql"
    db_path: str = Field(default="auth.db")  # Used only for SQLite
    pg_config: PostgreSQLConfig = Field(default_factory=PostgreSQLConfig)  # Used only for PostgreSQL
    enabled: bool = Field(default=False)
    token_expiry_days: int = Field(default=30)
    rate_limit_rpm: int = Field(default=60)  # Requests per minute
    admin_keys: list[str] = Field(default_factory=list)  # List of admin key IDs
    

class MCPConfig(BaseModel):
    """MCP server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    auth_enabled: bool = Field(default=False)
    auth: AuthConfig = Field(default_factory=AuthConfig)


class AppConfig(BaseModel):
    """Main application configuration."""
    env: str = Field(default="development")
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.
    
    Environment variables are prefixed with HADES_ and are uppercased.
    For nested configs, use __ as a separator, e.g., HADES_DB__HOST.
    
    Returns:
        AppConfig: The loaded configuration
    """
    # Load configuration from environment variables
    env_vars: Dict[str, Any] = {}
    
    # Set auth db path from env variable if provided
    auth_db_path = os.getenv("HADES_AUTH_DB_PATH")
    if auth_db_path:
        if "mcp" not in env_vars:
            env_vars["mcp"] = {}
        if "auth" not in env_vars["mcp"]:
            env_vars["mcp"]["auth"] = {}
        env_vars["mcp"]["auth"]["db_path"] = auth_db_path
    
    # Set PostgreSQL config from env variables if provided
    pg_host = os.getenv("HADES_PG_HOST")
    pg_port = os.getenv("HADES_PG_PORT")
    pg_user = os.getenv("HADES_PG_USER")
    pg_pass = os.getenv("HADES_PG_PASSWORD")
    pg_db = os.getenv("HADES_PG_DATABASE")
    
    if any([pg_host, pg_port, pg_user, pg_pass, pg_db]):
        if "mcp" not in env_vars:
            env_vars["mcp"] = {}
        if "auth" not in env_vars["mcp"]:
            env_vars["mcp"]["auth"] = {}
        if "pg_config" not in env_vars["mcp"]["auth"]:
            env_vars["mcp"]["auth"]["pg_config"] = {}
        
        if pg_host:
            env_vars["mcp"]["auth"]["pg_config"]["host"] = pg_host
        if pg_port:
            env_vars["mcp"]["auth"]["pg_config"]["port"] = int(pg_port)
        if pg_user:
            env_vars["mcp"]["auth"]["pg_config"]["username"] = pg_user
        if pg_pass:
            env_vars["mcp"]["auth"]["pg_config"]["password"] = pg_pass
        if pg_db:
            env_vars["mcp"]["auth"]["pg_config"]["database"] = pg_db
    
    # Process environment variables
    for key, value in os.environ.items():
        if key.startswith("HADES_"):
            # Remove prefix and convert to lowercase
            clean_key = key[6:].lower()
            
            # Handle nested configs
            if "__" in clean_key:
                section, option = clean_key.split("__", 1)
                if section not in env_vars:
                    env_vars[section] = {}
                env_vars[section][option] = value
            else:
                env_vars[clean_key] = value
    
    # Convert to appropriate types
    if "debug" in env_vars:
        env_vars["debug"] = env_vars["debug"].lower() == "true"
    
    if "mcp" in env_vars:
        mcp_config = env_vars["mcp"]
        
        # Convert auth_enabled to boolean
        if "auth_enabled" in mcp_config:
            mcp_config["auth_enabled"] = mcp_config["auth_enabled"].lower() == "true"
        
        # Convert port to int
        if "port" in mcp_config:
            mcp_config["port"] = int(mcp_config["port"])
        
        # Handle auth config
        if "auth" in mcp_config:
            auth_config = mcp_config["auth"]
            
            # Convert enabled to boolean
            if "enabled" in auth_config:
                auth_config["enabled"] = auth_config["enabled"].lower() == "true"
            
            # Convert numeric values
            for key in ["token_expiry_days", "rate_limit_rpm"]:
                if key in auth_config:
                    auth_config[key] = int(auth_config[key])
            
            # Handle admin keys list
            if "admin_keys" in auth_config and isinstance(auth_config["admin_keys"], str):
                auth_config["admin_keys"] = [k.strip() for k in auth_config["admin_keys"].split(",")]
    
    # Create config with defaults and overrides
    config = AppConfig(**env_vars)
    
    logger.info(f"Configuration loaded for environment: {config.env}")
    return config


# Global config instance
config = load_config()
