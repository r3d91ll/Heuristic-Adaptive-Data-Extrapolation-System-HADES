#!/usr/bin/env python3
"""
Consolidated database setup script for HADES.

This script initializes both PostgreSQL and ArangoDB databases for the HADES system.
It sets up the necessary schemas, collections, and indexes for both databases.
"""
import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from arango import ArangoClient
from dotenv import load_dotenv

from src.db.connection import DBConnection
from src.utils.logger import get_logger
from src.utils.versioning import VersionMetadata
from src.utils.config import config

logger = get_logger(__name__)


class DatabaseSetup:
    """Handles setup for all HADES databases."""

    def __init__(self, force: bool = False):
        """
        Initialize the database setup.
        
        Args:
            force: Whether to force recreate databases if they exist
        """
        self.force = force
        
        # Load environment variables from .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        if os.path.exists(env_path):
            logger.info(f"Loading environment variables from {env_path}")
            load_dotenv(env_path)
        
        # PostgreSQL configuration
        self.pg_config = {
            "host": os.getenv("HADES_PG_HOST", "localhost"),
            "port": os.getenv("HADES_PG_PORT", "5432"),
            "user": os.getenv("HADES_PG_USER", "hades"),
            "password": os.getenv("HADES_PG_PASSWORD", "o$n^3W%QD0HGWxH!"),
            "database": os.getenv("HADES_PG_DATABASE", "hades_test")
        }
        
        # ArangoDB configuration
        self.arango_config = {
            "host": os.getenv("HADES_ARANGO_HOST", "http://localhost:8529"),
            "username": os.getenv("HADES_ARANGO_USER", "hades"),
            "password": os.getenv("HADES_ARANGO_PASSWORD", "dpvL#tocbHQeKBd4"),
            "database": os.getenv("HADES_ARANGO_DATABASE", "hades_graph")
        }

    def setup_all(self) -> None:
        """Set up all databases for HADES."""
        try:
            logger.info("Starting HADES database setup")
            
            # Set up PostgreSQL
            self.setup_postgresql()
            
            # Set up ArangoDB
            self.setup_arangodb()
            
            logger.info("HADES database setup completed successfully")
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            sys.exit(1)

    def setup_postgresql(self) -> None:
        """Set up PostgreSQL database for HADES."""
        logger.info("Setting up PostgreSQL database")
        
        try:
            # Connect to PostgreSQL server
            conn = psycopg2.connect(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
                database="postgres",  # Connect to default database first
                connect_timeout=5
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (self.pg_config["database"],))
            db_exists = cursor.fetchone()
            
            # Create database if it doesn't exist or force is True
            if not db_exists or self.force:
                if db_exists and self.force:
                    logger.warning(f"Force flag set - dropping existing database {self.pg_config['database']}")
                    cursor.execute(f"DROP DATABASE IF EXISTS {self.pg_config['database']}")
                
                logger.info(f"Creating PostgreSQL database {self.pg_config['database']}")
                cursor.execute(f"CREATE DATABASE {self.pg_config['database']} OWNER {self.pg_config['user']}")
            else:
                logger.info(f"PostgreSQL database {self.pg_config['database']} already exists")
            
            # Close connection to server
            cursor.close()
            conn.close()
            
            # Connect to the target database
            conn = psycopg2.connect(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
                database=self.pg_config["database"]
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            logger.info("Creating PostgreSQL tables")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                key_hash VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                key_id VARCHAR(255) NOT NULL REFERENCES api_keys(key_id),
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key_id, timestamp)
            )
            """)
            
            # Close connection
            cursor.close()
            conn.close()
            
            logger.info("PostgreSQL setup completed successfully")
        except Exception as e:
            logger.error(f"PostgreSQL setup failed: {e}")
            raise

    def setup_arangodb(self) -> None:
        """Set up ArangoDB database for HADES."""
        logger.info("Setting up ArangoDB database")
        
        try:
            # Initialize ArangoDB using the DBConnection class
            self.setup_arangodb_collections()
            
            # Create change logs collection
            self.create_change_logs_collection()
            
            # Update existing documents with versioning
            self.update_existing_documents_with_versioning()
            
            logger.info("ArangoDB setup completed successfully")
        except Exception as e:
            logger.error(f"ArangoDB setup failed: {e}")
            raise

    def setup_arangodb_collections(self) -> None:
        """Initialize the ArangoDB database with required collections and indexes."""
        try:
            logger.info("Starting ArangoDB initialization")
            db_connection = DBConnection()
            db_connection.initialize_database()
            logger.info("ArangoDB initialization completed successfully")
        except Exception as e:
            logger.error(f"ArangoDB initialization failed: {e}")
            raise

    def create_change_logs_collection(self) -> None:
        """Set up the change_logs collection."""
        try:
            logger.info("Setting up change_logs collection")

            # Create a test entry to verify the collection is working
            db_connection = DBConnection()
            with db_connection.get_db() as db:
                if db.has_collection("change_logs") and db.collection("change_logs").count() == 0:
                    logger.info("Adding test entry to change_logs")

                    test_entry = {
                        "_key": str(uuid.uuid4()),
                        "entity_id": "test/entity",
                        "previous_version": None,
                        "new_version": "v0.1.0",
                        "commit_id": str(uuid.uuid4()),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "changes": {
                            "added": {"name": "Test Entity"},
                            "removed": {},
                            "modified": {}
                        },
                        "commit_message": "Initial test entry for change_logs"
                    }

                    db.collection("change_logs").insert(test_entry)
                    logger.info("Test entry added to change_logs")
        except Exception as e:
            logger.error(f"Failed to set up change_logs collection: {e}")
            raise

    def update_existing_documents_with_versioning(self) -> None:
        """Add versioning metadata to existing documents if they don't have it."""
        try:
            logger.info("Updating existing documents with version metadata")

            db_connection = DBConnection()
            with db_connection.get_db() as db:
                # Process collections
                for collection in ["entities", "relationships", "contexts", "domains"]:
                    if db.has_collection(collection):
                        logger.info(f"Processing {collection} collection")

                        # Get all documents without version metadata
                        query = f"""
                        FOR doc IN {collection}
                            FILTER doc.version == null
                            RETURN doc
                        """

                        cursor = db.aql.execute(query)
                        docs_to_update = list(cursor)

                        if docs_to_update:
                            logger.info(f"Adding version metadata to {len(docs_to_update)} documents in {collection}")

                            # Update each document with version metadata
                            for doc in docs_to_update:
                                # Create version metadata
                                version_meta = VersionMetadata.create_metadata("v0.1.0")

                                # Update the document
                                db.collection(collection).update(
                                    doc["_key"],
                                    version_meta
                                )
                        else:
                            logger.info(f"No documents in {collection} need version metadata")
        except Exception as e:
            logger.error(f"Failed to update existing documents with versioning: {e}")
            raise


def main() -> None:
    """Main entry point for database setup."""
    parser = argparse.ArgumentParser(description="Set up HADES databases")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate databases if they exist"
    )
    parser.add_argument(
        "--postgresql-only", action="store_true", help="Set up only PostgreSQL database"
    )
    parser.add_argument(
        "--arangodb-only", action="store_true", help="Set up only ArangoDB database"
    )
    args = parser.parse_args()

    # Create database setup instance
    db_setup = DatabaseSetup(force=args.force)
    
    # Set up databases based on arguments
    if args.postgresql_only:
        logger.info("Setting up PostgreSQL database only")
        db_setup.setup_postgresql()
    elif args.arangodb_only:
        logger.info("Setting up ArangoDB database only")
        db_setup.setup_arangodb()
    else:
        logger.info("Setting up all HADES databases")
        db_setup.setup_all()


if __name__ == "__main__":
    main()
