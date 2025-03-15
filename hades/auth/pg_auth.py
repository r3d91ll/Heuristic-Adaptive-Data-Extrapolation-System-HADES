"""
PostgreSQL-based authentication module for HADES.

This module provides authentication and rate limiting functionality
using a PostgreSQL database to store API keys and rate limit information.
"""
import os
import time
import hashlib
import secrets
import logging
from typing import Optional, Dict, Tuple, Any
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import APIKeyHeader

# Setup logging
logger = logging.getLogger(__name__)

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Database connection parameters
DB_PARAMS = {
    "dbname": os.environ.get("HADES_TEST_DB_NAME", "hades_test"),
    "user": os.environ.get("HADES_TEST_DB_USER", "hades"),
    "password": os.environ.get("HADES_TEST_DB_PASSWORD", ""),
    "host": os.environ.get("HADES_TEST_DB_HOST", "localhost"),
    "port": os.environ.get("HADES_TEST_DB_PORT", "5432")
}

# Rate limiting defaults
DEFAULT_RATE_LIMIT = 100  # requests per window
RATE_LIMIT_WINDOW = 3600  # seconds (1 hour)


def get_db_connection():
    """Get a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(**DB_PARAMS, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> Tuple[str, str]:
    """Generate a new API key and its hash.
    
    Returns:
        Tuple[str, str]: (key_id, api_key)
    """
    # Generate a random key ID (16 bytes = 32 hex chars)
    key_id = secrets.token_hex(16)
    
    # Generate a random API key (32 bytes = 64 hex chars)
    api_key = secrets.token_hex(32)
    
    return key_id, api_key


def create_api_key(name: str) -> Dict[str, str]:
    """Create a new API key in the database.
    
    Args:
        name: A name to identify the API key
        
    Returns:
        Dict with key_id and api_key
    """
    key_id, api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO api_keys (key_id, key_hash, name)
                VALUES (%s, %s, %s)
                """,
                (key_id, key_hash, name)
            )
        conn.commit()
        return {"key_id": key_id, "api_key": api_key}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating API key"
        )
    finally:
        conn.close()


def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify an API key against the database.
    
    Args:
        api_key: The API key to verify
        
    Returns:
        Dict with key information if valid, None otherwise
    """
    if not api_key:
        return None
        
    key_hash = hash_api_key(api_key)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT key_id, name, created_at, last_used
                FROM api_keys
                WHERE key_hash = %s
                """,
                (key_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                # Update last_used timestamp
                cursor.execute(
                    """
                    UPDATE api_keys
                    SET last_used = CURRENT_TIMESTAMP
                    WHERE key_id = %s
                    """,
                    (result["key_id"],)
                )
                conn.commit()
                return dict(result)
            return None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error verifying API key: {e}")
        return None
    finally:
        conn.close()


def check_rate_limit(key_id: str, endpoint: str) -> bool:
    """Check if the request is within rate limits.
    
    Args:
        key_id: The API key ID
        endpoint: The endpoint being accessed
        
    Returns:
        bool: True if within limits, False otherwise
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current rate limit info
            cursor.execute(
                """
                SELECT count, window_start
                FROM rate_limits
                WHERE key_id = %s AND endpoint = %s
                """,
                (key_id, endpoint)
            )
            result = cursor.fetchone()
            
            current_time = datetime.now(timezone.utc)
            
            if result:
                window_start = result["window_start"]
                count = result["count"]
                
                # Check if window has expired
                window_seconds = (current_time - window_start).total_seconds()
                
                if window_seconds > RATE_LIMIT_WINDOW:
                    # Reset window
                    cursor.execute(
                        """
                        UPDATE rate_limits
                        SET count = 1, window_start = CURRENT_TIMESTAMP
                        WHERE key_id = %s AND endpoint = %s
                        """,
                        (key_id, endpoint)
                    )
                    conn.commit()
                    return True
                
                # Check if under limit
                if count < DEFAULT_RATE_LIMIT:
                    # Increment count
                    cursor.execute(
                        """
                        UPDATE rate_limits
                        SET count = count + 1
                        WHERE key_id = %s AND endpoint = %s
                        """,
                        (key_id, endpoint)
                    )
                    conn.commit()
                    return True
                
                return False
            else:
                # Create new rate limit entry
                cursor.execute(
                    """
                    INSERT INTO rate_limits (key_id, endpoint, count, window_start)
                    VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                    """,
                    (key_id, endpoint)
                )
                conn.commit()
                return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error checking rate limit: {e}")
        return True  # Allow request on error
    finally:
        conn.close()


async def get_api_key(
    request: Request,
    api_key_header: str = Depends(API_KEY_HEADER)
) -> Dict[str, Any]:
    """Dependency for FastAPI routes that require API key authentication.
    
    Args:
        request: The FastAPI request
        api_key_header: The API key from the X-API-Key header
        
    Returns:
        Dict with key information
        
    Raises:
        HTTPException: If authentication fails
    """
    if os.environ.get("ENABLE_AUTH", "true").lower() != "true":
        # Authentication disabled
        return {"key_id": "disabled", "name": "Auth Disabled"}
    
    # Verify API key
    key_info = verify_api_key(api_key_header)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check rate limit
    endpoint = request.url.path
    if not check_rate_limit(key_info["key_id"], endpoint):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return key_info


# Command-line interface for key management
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load environment variables
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env.test"
    if env_file.exists():
        load_dotenv(env_file)
    
    if len(sys.argv) < 2:
        print("Usage: python pg_auth.py [create|list|delete] [name]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: python pg_auth.py create <name>")
            sys.exit(1)
        
        name = sys.argv[2]
        result = create_api_key(name)
        print(f"Created API key for '{name}':")
        print(f"Key ID: {result['key_id']}")
        print(f"API Key: {result['api_key']}")
        print("\nStore this API key securely. It will not be shown again.")
    
    elif command == "list":
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT key_id, name, created_at, last_used
                    FROM api_keys
                    ORDER BY created_at DESC
                    """
                )
                keys = cursor.fetchall()
                
                if not keys:
                    print("No API keys found.")
                else:
                    print(f"Found {len(keys)} API keys:")
                    for key in keys:
                        last_used = key["last_used"] or "Never"
                        print(f"ID: {key['key_id']}, Name: {key['name']}, Created: {key['created_at']}, Last used: {last_used}")
        finally:
            conn.close()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python pg_auth.py delete <key_id>")
            sys.exit(1)
        
        key_id = sys.argv[2]
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM rate_limits WHERE key_id = %s
                    """,
                    (key_id,)
                )
                cursor.execute(
                    """
                    DELETE FROM api_keys WHERE key_id = %s
                    RETURNING name
                    """,
                    (key_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    conn.commit()
                    print(f"Deleted API key '{result['name']}' with ID {key_id}")
                else:
                    print(f"No API key found with ID {key_id}")
        finally:
            conn.close()
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python pg_auth.py [create|list|delete] [name]")
        sys.exit(1)
