"""
Initial database setup script for HADES.
"""
import argparse
import sys
import uuid
from datetime import datetime, timezone

from src.db.connection import DBConnection
from src.utils.logger import get_logger
from src.utils.versioning import VersionMetadata

logger = get_logger(__name__)


def setup_database() -> None:
    """Initialize the ArangoDB database with required collections and indexes."""
    try:
        logger.info("Starting database initialization")
        db_connection = DBConnection()
        db_connection.initialize_database()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


def create_change_logs_collection() -> None:
    """Set up the change_logs collection."""
    try:
        logger.info("Setting up change_logs collection")

        # Create a test entry to verify the collection is working
        db_connection = DBConnection()
        with db_connection.get_db() as db:
            if db.collection("change_logs").count() == 0:
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
        sys.exit(1)


def update_existing_documents_with_versioning() -> None:
    """Add versioning metadata to existing documents if they don't have it."""
    try:
        logger.info("Updating existing documents with version metadata")

        db_connection = DBConnection()
        with db_connection.get_db() as db:
            # Process entities collection
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
        sys.exit(1)


def main() -> None:
    """Main entry point for database setup."""
    parser = argparse.ArgumentParser(description="Set up the HADES database")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate database if it exists"
    )
    parser.add_argument(
        "--with-versioning", action="store_true",
        help="Initialize versioning for existing documents"
    )
    args = parser.parse_args()

    if args.force:
        logger.warning("Force flag set - this will delete existing data!")
        # Implementation for force recreation would go here
        # For safety, we're leaving this out for now

    # Initialize the database structure
    setup_database()

    # Set up change logs collection
    create_change_logs_collection()

    # Add versioning to existing documents if requested
    if args.with_versioning:
        update_existing_documents_with_versioning()


if __name__ == "__main__":
    main()
