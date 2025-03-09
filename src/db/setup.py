"""
Initial database setup script for HADES.
"""
import argparse
import sys

from src.db.connection import connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


def setup_database() -> None:
    """Initialize the ArangoDB database with required collections and indexes."""
    try:
        logger.info("Starting database initialization")
        connection.initialize_database()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for database setup."""
    parser = argparse.ArgumentParser(description="Set up the HADES database")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate database if it exists"
    )
    args = parser.parse_args()

    if args.force:
        logger.warning("Force flag set - this will delete existing data!")
        # Implementation for force recreation would go here
        # For safety, we're leaving this out for now

    setup_database()


if __name__ == "__main__":
    main()
