"""
Authentication and rate limiting for the HADES MCP server.

This module implements token-based authentication and rate limiting
for the Model Context Protocol (MCP) server.

PostgreSQL is used for managing authentication and rate limiting, keeping these 
concerns separate from the main knowledge graph data stored in ArangoDB. 
This separation of concerns provides a robust, scalable solution that's optimized 
for the specific needs of API key management and request limiting.

The module also supports SQLite as a fallback option for development and testing.
"""
import hashlib
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union, Any

import sqlite3
import psycopg2
import psycopg2.extras
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKey(BaseModel):
    """API key model."""
    key_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True


class AuthDB:
    """
    Authentication database manager supporting both PostgreSQL and SQLite.
    
    This class manages API keys, authentication, and rate limiting through a dedicated
    database. PostgreSQL is the preferred backend for production use, providing robust
    performance and scalability. SQLite is supported as a fallback for development
    and testing environments.
    
    These authentication and security concerns are kept separate from the main 
    knowledge graph data stored in ArangoDB, following the principle of using the 
    right tool for the right job.
    """
    
    def __init__(self):
        """Initialize the auth database."""
        self.db_type = config.mcp.auth.db_type
        self.db_path = config.mcp.auth.db_path
        self.pg_config = config.mcp.auth.pg_config
        
        # For testing environments, try to connect to PostgreSQL first
        # If it fails, fall back to SQLite
        if self.db_type == "postgresql" and os.environ.get("HADES_ENV") == "test":
            try:
                # Try to connect to PostgreSQL
                conn = psycopg2.connect(
                    host=self.pg_config.host,
                    port=self.pg_config.port,
                    user=self.pg_config.username,
                    password=self.pg_config.password,
                    dbname=self.pg_config.database,
                    connect_timeout=3  # Short timeout for testing
                )
                conn.close()
                logger.info("Successfully connected to PostgreSQL for testing")
            except Exception as e:
                logger.warning(f"PostgreSQL connection failed in test environment: {e}")
                logger.info("Falling back to SQLite for testing")
                self.db_type = "sqlite"
                self.db_path = ":memory:"
        
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Get a connection to the database (PostgreSQL or SQLite)."""
        conn = None
        try:
            if self.db_type == "sqlite":
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
            else:  # postgresql
                conn = psycopg2.connect(
                    host=self.pg_config.host,
                    port=self.pg_config.port,
                    user=self.pg_config.username,
                    password=self.pg_config.password,
                    dbname=self.pg_config.database
                )
                conn.cursor_factory = psycopg2.extras.DictCursor
            yield conn
        finally:
            if conn:
                conn.close()
    
    def init_db(self) -> None:
        """Initialize the database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == "sqlite":
                # Create API keys table for SQLite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
                """)
                
                # Create rate limits table for SQLite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key_id TEXT NOT NULL,
                    requests INTEGER DEFAULT 1,
                    window_start TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """)
                
                # Add indexes for SQLite
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key_id ON rate_limits(key_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_expires ON rate_limits(expires_at)")
            else:  # postgresql
                # Create API keys table for PostgreSQL
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
                """)
                
                # Create rate limits table for PostgreSQL
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key_id TEXT NOT NULL,
                    requests INTEGER DEFAULT 1,
                    window_start TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
                """)
                
                # Add indexes for PostgreSQL
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key_id ON rate_limits(key_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_expires ON rate_limits(expires_at)")
            
            conn.commit()
    
    def create_api_key(self, name: str, expiry_days: Optional[int] = None) -> Tuple[str, str]:
        """
        Create a new API key.
        
        Args:
            name: Name or purpose of the key
            expiry_days: Number of days until the key expires (None for no expiration)
            
        Returns:
            Tuple of key_id and the actual API key
        """
        key_id = str(uuid.uuid4())
        api_key = str(uuid.uuid4())
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        created_at = datetime.now()
        expires_at = None
        if expiry_days is not None:
            expires_at = created_at + timedelta(days=expiry_days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == "sqlite":
                # Format datetime as ISO string for SQLite
                created_at_str = created_at.isoformat()
                expires_at_str = expires_at.isoformat() if expires_at else None
                
                cursor.execute(
                    """
                    INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (key_id, key_hash, name, created_at_str, expires_at_str, True)
                )
            else:  # postgresql
                cursor.execute(
                    """
                    INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (key_id, key_hash, name, created_at, expires_at, True)
                )
            
            conn.commit()
        
        return key_id, api_key
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Validate an API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            APIKey object if valid, None otherwise
        """
        if not api_key:
            return None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == "sqlite":
                cursor.execute(
                    """
                    SELECT key_id, name, created_at, expires_at, is_active 
                    FROM api_keys 
                    WHERE key_hash = ?
                    """,
                    (key_hash,)
                )
            else:  # postgresql
                cursor.execute(
                    """
                    SELECT key_id, name, created_at, expires_at, is_active 
                    FROM api_keys 
                    WHERE key_hash = %s
                    """,
                    (key_hash,)
                )
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Check if the key is active
            if not row["is_active"]:
                return None
            
            # Check if the key has expired
            now = datetime.now()
            expires_at = None
            
            if self.db_type == "sqlite" and row["expires_at"]:
                # Convert ISO string to datetime for SQLite
                expires_at = datetime.fromisoformat(row["expires_at"])
                if expires_at < now:
                    return None
            elif self.db_type == "postgresql" and row["expires_at"]:
                # PostgreSQL returns datetime objects directly
                expires_at = row["expires_at"]
                if expires_at < now:
                    return None
            
            # Create APIKey object
            created_at = row["created_at"]
            if self.db_type == "sqlite":
                # Convert ISO string to datetime for SQLite
                created_at = datetime.fromisoformat(created_at)
                if row["expires_at"]:
                    expires_at = datetime.fromisoformat(row["expires_at"])
            
            return APIKey(
                key_id=row["key_id"],
                name=row["name"],
                created_at=created_at,
                expires_at=expires_at,
                is_active=bool(row["is_active"])
            )
    
    def check_rate_limit(self, api_key: str, rpm_limit: int = None) -> bool:
        """
        Check if a key has exceeded its rate limit.
        
        Args:
            api_key: The API key to check
            rpm_limit: Requests per minute limit (defaults to config value)
            
        Returns:
            True if within limits, False if exceeded
        """
        if rpm_limit is None:
            rpm_limit = config.mcp.auth.rate_limit_rpm
        if not api_key:
            return False
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        now = datetime.now()
        window_start = now - timedelta(minutes=1)
        expires_at = now + timedelta(minutes=5)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean up expired rate limits
            if self.db_type == "sqlite":
                cursor.execute(
                    "DELETE FROM rate_limits WHERE expires_at < ?",
                    (now.isoformat(),)
                )
            else:  # postgresql
                cursor.execute(
                    "DELETE FROM rate_limits WHERE expires_at < %s",
                    (now,)
                )
            
            # Get current request count in the time window
            if self.db_type == "sqlite":
                cursor.execute(
                    """
                    SELECT SUM(requests) as total_requests
                    FROM rate_limits
                    WHERE key_id = ? AND window_start >= ?
                    """,
                    (key_hash, window_start.isoformat())
                )
            else:  # postgresql
                cursor.execute(
                    """
                    SELECT SUM(requests) as total_requests
                    FROM rate_limits
                    WHERE key_id = %s AND window_start >= %s
                    """,
                    (key_hash, window_start)
                )
            
            row = cursor.fetchone()
            total_requests = row["total_requests"] if row and row["total_requests"] else 0
            
            # If we're already over the limit, deny the request
            if total_requests >= rpm_limit:
                return False
            
            # Record this request
            if self.db_type == "sqlite":
                cursor.execute(
                    """
                    INSERT INTO rate_limits (key_id, requests, window_start, expires_at)
                    VALUES (?, 1, ?, ?)
                    """,
                    (key_hash, now.isoformat(), expires_at.isoformat())
                )
            else:  # postgresql
                cursor.execute(
                    """
                    INSERT INTO rate_limits (key_id, requests, window_start, expires_at)
                    VALUES (%s, 1, %s, %s)
                    """,
                    (key_hash, now, expires_at)
                )
            
            conn.commit()
            
            return True


# Global auth DB instance
auth_db = AuthDB()


async def get_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> Optional[APIKey]:
    """
    Dependency for validating API keys.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        APIKey if valid, None otherwise
    """
    if not config.mcp.auth_enabled:
        # If auth is not enabled, return a dummy key
        return APIKey(
            key_id="dummy",
            name="anonymous",
            created_at=datetime.now(),
        )
    
    if not api_key:
        return None
    
    return auth_db.validate_api_key(api_key)


async def get_current_key(
    api_key: Optional[APIKey] = Depends(get_api_key),
) -> APIKey:
    """
    Dependency for requiring a valid API key.
    
    Args:
        api_key: The validated API key
        
    Returns:
        APIKey if valid
        
    Raises:
        HTTPException if invalid
    """
    if not config.mcp.auth_enabled:
        # If auth is not enabled, return a dummy key
        return APIKey(
            key_id="dummy",
            name="anonymous",
            created_at=datetime.now(),
        )
    
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    return api_key


async def check_rate_limit(
    request: Request,
    api_key: APIKey = Depends(get_current_key),
) -> None:
    """
    Dependency for checking rate limits.
    
    Args:
        request: The FastAPI request
        api_key: The validated API key
        
    Raises:
        HTTPException if rate limit exceeded
    """
    if not config.mcp.auth_enabled:
        return
    
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    if not auth_db.check_rate_limit(raw_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
        )
