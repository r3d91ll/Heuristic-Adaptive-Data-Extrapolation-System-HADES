"""
ArangoDB connection management for HADES.
"""
import os
from contextlib import contextmanager
from typing import Dict, Generator, Optional

from arango import ArangoClient
from arango.database import Database
from arango.exceptions import ArangoError

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ArangoDBConnection:
    """Manages connections to ArangoDB."""

    def __init__(
        self,
        host: str = os.getenv("ARANGO_HOST", "http://localhost:8529"),
        username: str = os.getenv("ARANGO_USERNAME", "root"),
        password: str = os.getenv("ARANGO_PASSWORD", ""),
        database: str = os.getenv("ARANGO_DATABASE", "hades"),
    ):
        """Initialize the ArangoDB connection."""
        self.host = host
        self.username = username
        self.password = password
        self.database_name = database
        self.client = ArangoClient(hosts=host)

    def initialize_database(self) -> None:
        """Initialize the database and collections if they don't exist."""
        sys_db = self.client.db("_system", username=self.username, password=self.password)

        # Create database if it doesn't exist
        if not sys_db.has_database(self.database_name):
            logger.info(f"Creating database: {self.database_name}")
            sys_db.create_database(
                self.database_name,
                users=[{"username": self.username, "password": self.password, "active": True}],
            )

        # Connect to the database
        db = self.client.db(
            self.database_name, username=self.username, password=self.password
        )

        # Create document collections
        document_collections = ["entities", "contexts", "domains"]
        for collection in document_collections:
            if not db.has_collection(collection):
                logger.info(f"Creating document collection: {collection}")
                db.create_collection(collection)

        # Create edge collections
        edge_collections = ["relationships", "entity_domains", "entity_contexts"]
        for collection in edge_collections:
            if not db.has_collection(collection):
                logger.info(f"Creating edge collection: {collection}")
                db.create_collection(collection, edge=True)

        # Create indexes
        logger.info("Ensuring indexes")
        db.collection("entities").add_persistent_index(["name", "type"])
        db.collection("relationships").add_persistent_index(["_from", "_to", "type"])
        db.collection("contexts").add_fulltext_index(["text"])

    @contextmanager
    def get_db(self) -> Generator[Database, None, None]:
        """Get a database connection."""
        db = self.client.db(
            self.database_name, username=self.username, password=self.password
        )
        try:
            yield db
        except ArangoError as e:
            logger.error(f"ArangoDB error: {e}")
            raise
        finally:
            # No need to close connection as ArangoDB client manages the connection pool
            pass

    def execute_query(
        self, query: str, bind_vars: Optional[Dict] = None
    ) -> Dict:
        """Execute an AQL query."""
        with self.get_db() as db:
            try:
                result = db.aql.execute(query, bind_vars=bind_vars or {})
                return {"success": True, "result": list(result)}
            except ArangoError as e:
                logger.error(f"Query execution error: {e}")
                return {"success": False, "error": str(e)}


# Global connection instance
connection = ArangoDBConnection()
