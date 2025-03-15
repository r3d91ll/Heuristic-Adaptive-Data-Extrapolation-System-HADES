#!/usr/bin/env python3
"""
Migration script to transition from SQLite to PostgreSQL for HADES authentication.

This script:
1. Creates the necessary PostgreSQL database and tables
2. Migrates existing data from SQLite to PostgreSQL
3. Validates the migration was successful
"""
import argparse
import hashlib
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate authentication data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=config.mcp.auth.db_path,
        help="Path to SQLite database file (default: from config)"
    )
    parser.add_argument(
        "--pg-host",
        type=str,
        default=config.mcp.auth.pg_config.host,
        help="PostgreSQL host (default: from config)"
    )
    parser.add_argument(
        "--pg-port",
        type=int,
        default=config.mcp.auth.pg_config.port,
        help="PostgreSQL port (default: from config)"
    )
    parser.add_argument(
        "--pg-user",
        type=str,
        default=config.mcp.auth.pg_config.username,
        help="PostgreSQL username (default: from config)"
    )
    parser.add_argument(
        "--pg-password",
        type=str,
        default=config.mcp.auth.pg_config.password,
        help="PostgreSQL password (default: from config)"
    )
    parser.add_argument(
        "--pg-database",
        type=str,
        default=config.mcp.auth.pg_config.database,
        help="PostgreSQL database name (default: from config)"
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create the PostgreSQL database if it doesn't exist"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if target tables already have data"
    )
    
    return parser.parse_args()


@contextmanager
def get_sqlite_connection(db_path):
    """Get a connection to the SQLite database."""
    if not os.path.exists(db_path):
        logger.error(f"SQLite database file not found: {db_path}")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


@contextmanager
def get_pg_connection(host, port, user, password, database):
    """Get a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database
        )
        conn.cursor_factory = psycopg2.extras.DictCursor
        yield conn
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def create_pg_database(host, port, user, password, database):
    """Create the PostgreSQL database if it doesn't exist."""
    try:
        # Connect to the default 'postgres' database to create our database
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if cursor.fetchone():
                logger.info(f"Database '{database}' already exists")
                return
            
            # Create database
            cursor.execute(f"CREATE DATABASE {database}")
            logger.info(f"Database '{database}' created successfully")
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL database: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def create_pg_tables(host, port, user, password, database):
    """Create the necessary PostgreSQL tables."""
    with get_pg_connection(host, port, user, password, database) as conn:
        with conn.cursor() as cursor:
            # Create API keys table
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
            
            # Create rate limits table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                key TEXT NOT NULL,
                requests INTEGER DEFAULT 1,
                window_start TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
            """)
            
            # Add indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_expires ON rate_limits(expires_at)")
            
            conn.commit()
            logger.info("PostgreSQL tables created successfully")


def check_existing_data(host, port, user, password, database, force):
    """Check if there's already data in the PostgreSQL tables."""
    with get_pg_connection(host, port, user, password, database) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM api_keys")
            api_key_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rate_limits")
            rate_limit_count = cursor.fetchone()[0]
            
            if api_key_count > 0 or rate_limit_count > 0:
                if not force:
                    logger.error(
                        f"PostgreSQL tables already contain data: "
                        f"{api_key_count} API keys, {rate_limit_count} rate limits. "
                        f"Use --force to override."
                    )
                    sys.exit(1)
                else:
                    logger.warning(
                        f"Overwriting existing PostgreSQL data: "
                        f"{api_key_count} API keys, {rate_limit_count} rate limits."
                    )
                    # Clear existing data
                    cursor.execute("DELETE FROM rate_limits")
                    cursor.execute("DELETE FROM api_keys")
                    conn.commit()


def migrate_api_keys(sqlite_path, pg_host, pg_port, pg_user, pg_password, pg_database):
    """Migrate API keys from SQLite to PostgreSQL."""
    with get_sqlite_connection(sqlite_path) as sqlite_conn:
        with get_pg_connection(pg_host, pg_port, pg_user, pg_password, pg_database) as pg_conn:
            # Get API keys from SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT * FROM api_keys")
            api_keys = sqlite_cursor.fetchall()
            
            if not api_keys:
                logger.info("No API keys found in SQLite database")
                return 0
            
            # Insert API keys into PostgreSQL
            pg_cursor = pg_conn.cursor()
            for key in api_keys:
                # Convert ISO string to datetime for PostgreSQL
                created_at = datetime.fromisoformat(key["created_at"])
                expires_at = datetime.fromisoformat(key["expires_at"]) if key["expires_at"] else None
                
                pg_cursor.execute(
                    """
                    INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        key["key_id"],
                        key["key_hash"],
                        key["name"],
                        created_at,
                        expires_at,
                        bool(key["is_active"])
                    )
                )
            
            pg_conn.commit()
            logger.info(f"Migrated {len(api_keys)} API keys")
            return len(api_keys)


def migrate_rate_limits(sqlite_path, pg_host, pg_port, pg_user, pg_password, pg_database):
    """Migrate rate limits from SQLite to PostgreSQL."""
    with get_sqlite_connection(sqlite_path) as sqlite_conn:
        with get_pg_connection(pg_host, pg_port, pg_user, pg_password, pg_database) as pg_conn:
            # Get rate limits from SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT * FROM rate_limits")
            rate_limits = sqlite_cursor.fetchall()
            
            if not rate_limits:
                logger.info("No rate limits found in SQLite database")
                return 0
            
            # Insert rate limits into PostgreSQL
            pg_cursor = pg_conn.cursor()
            for limit in rate_limits:
                # Convert ISO string to datetime for PostgreSQL
                window_start = datetime.fromisoformat(limit["window_start"])
                expires_at = datetime.fromisoformat(limit["expires_at"])
                
                pg_cursor.execute(
                    """
                    INSERT INTO rate_limits (key, requests, window_start, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        limit["key"],
                        limit["requests"],
                        window_start,
                        expires_at
                    )
                )
            
            pg_conn.commit()
            logger.info(f"Migrated {len(rate_limits)} rate limits")
            return len(rate_limits)


def validate_migration(sqlite_path, pg_host, pg_port, pg_user, pg_password, pg_database):
    """Validate that the migration was successful."""
    with get_sqlite_connection(sqlite_path) as sqlite_conn:
        with get_pg_connection(pg_host, pg_port, pg_user, pg_password, pg_database) as pg_conn:
            # Check API key counts
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT COUNT(*) FROM api_keys")
            sqlite_api_key_count = sqlite_cursor.fetchone()[0]
            
            pg_cursor = pg_conn.cursor()
            pg_cursor.execute("SELECT COUNT(*) FROM api_keys")
            pg_api_key_count = pg_cursor.fetchone()[0]
            
            if sqlite_api_key_count != pg_api_key_count:
                logger.warning(
                    f"API key count mismatch: "
                    f"SQLite has {sqlite_api_key_count}, PostgreSQL has {pg_api_key_count}"
                )
            else:
                logger.info(f"API key counts match: {sqlite_api_key_count}")
            
            # Check rate limit counts
            sqlite_cursor.execute("SELECT COUNT(*) FROM rate_limits")
            sqlite_rate_limit_count = sqlite_cursor.fetchone()[0]
            
            pg_cursor.execute("SELECT COUNT(*) FROM rate_limits")
            pg_rate_limit_count = pg_cursor.fetchone()[0]
            
            if sqlite_rate_limit_count != pg_rate_limit_count:
                logger.warning(
                    f"Rate limit count mismatch: "
                    f"SQLite has {sqlite_rate_limit_count}, PostgreSQL has {pg_rate_limit_count}"
                )
            else:
                logger.info(f"Rate limit counts match: {sqlite_rate_limit_count}")
            
            return (
                sqlite_api_key_count == pg_api_key_count and
                sqlite_rate_limit_count == pg_rate_limit_count
            )


def main():
    """Main entry point for the migration script."""
    args = parse_args()
    
    logger.info("Starting migration from SQLite to PostgreSQL")
    
    # Create database if requested
    if args.create_db:
        logger.info(f"Creating PostgreSQL database '{args.pg_database}'")
        create_pg_database(args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database)
    
    # Create tables
    logger.info("Creating PostgreSQL tables")
    create_pg_tables(args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database)
    
    # Check for existing data
    check_existing_data(args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database, args.force)
    
    # Migrate data
    api_key_count = migrate_api_keys(args.sqlite_path, args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database)
    rate_limit_count = migrate_rate_limits(args.sqlite_path, args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database)
    
    # Validate migration
    logger.info("Validating migration")
    if validate_migration(args.sqlite_path, args.pg_host, args.pg_port, args.pg_user, args.pg_password, args.pg_database):
        logger.info("Migration validation successful")
    else:
        logger.warning("Migration validation failed - counts don't match")
    
    logger.info(f"Migration complete: {api_key_count} API keys, {rate_limit_count} rate limits")
    logger.info("To use PostgreSQL, set HADES_MCP__AUTH__DB_TYPE=postgresql in your environment")


if __name__ == "__main__":
    main()
