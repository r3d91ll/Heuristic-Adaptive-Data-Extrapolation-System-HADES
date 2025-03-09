"""
Authentication and rate limiting for the HADES MCP server.

This module implements token-based authentication and rate limiting
for the Model Context Protocol (MCP) server.
"""
import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union

import sqlite3
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
    """Authentication database manager."""
    
    def __init__(self):
        """Initialize the auth database."""
        self.db_path = config.mcp.auth.db_path
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self) -> None:
        """Initialize the database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create API keys table
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
            
            # Create rate limits table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                key TEXT NOT NULL,
                requests INTEGER DEFAULT 1,
                window_start TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """)
            
            # Add indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key)")
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
        
        created_at = datetime.now().isoformat()
        expires_at = None
        if expiry_days is not None:
            expires_at = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
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
            cursor.execute(
                """
                SELECT key_id, name, created_at, expires_at, is_active 
                FROM api_keys 
                WHERE key_hash = ?
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
            if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now():
                return None
            
            return APIKey(
                key_id=row["key_id"],
                name=row["name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
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
        window_start = (now - timedelta(minutes=1)).isoformat()
        expires_at = (now + timedelta(minutes=5)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean up expired rate limits
            cursor.execute(
                "DELETE FROM rate_limits WHERE expires_at < ?",
                (now.isoformat(),)
            )
            
            # Get current request count in the time window
            cursor.execute(
                """
                SELECT SUM(requests) as total_requests
                FROM rate_limits
                WHERE key = ? AND window_start >= ?
                """,
                (key_hash, window_start)
            )
            row = cursor.fetchone()
            
            total_requests = row["total_requests"] if row and row["total_requests"] else 0
            
            # If we're already over the limit, deny the request
            if total_requests >= rpm_limit:
                return False
            
            # Record this request
            cursor.execute(
                """
                INSERT INTO rate_limits (key, requests, window_start, expires_at)
                VALUES (?, 1, ?, ?)
                """,
                (key_hash, now.isoformat(), expires_at)
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
