"""Database service for interacting with ArangoDB."""

import logging
from typing import Dict, Any, List, Optional
from arango import ArangoClient

from hades.core.config import DatabaseConfig
from hades.core.exceptions import MCPError

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for interacting with ArangoDB."""

    def __init__(self, config: DatabaseConfig):
        """Initialize database service."""
        self.config = config.model_dump()
        self._client = None
        self._db = None
        self._initialized = False

    def _create_client(self) -> ArangoClient:
        """Create an ArangoDB client."""
        try:
            client = ArangoClient(
                hosts=f"http://{self.config['host']}:{self.config['port']}"
            )
            # Test the connection by getting system database
            sys_db = client.db("_system")
            sys_db.version()  # This will raise an error if connection fails
            return client
        except Exception as e:
            logger.error(f"Failed to create ArangoDB client: {e}")
            raise MCPError("INIT_ERROR", str(e))

    async def initialize(self) -> None:
        """Initialize database service."""
        try:
            if self._initialized:
                return

            self._client = self._create_client()
            self._db = self._client.db(
                self.config["database"],
                username=self.config["username"],
                password=self.config["password"]
            )
            self._initialized = True
            logger.info("Database service initialized successfully")
        except MCPError as e:
            logger.error(f"Failed to initialize database service: {e}")
            self._initialized = False
            raise
        except Exception as e:
            logger.error(f"Failed to initialize database service: {e}")
            self._initialized = False
            raise MCPError("INIT_ERROR", f"Failed to initialize database service: {e}")

    async def shutdown(self) -> None:
        """Shut down database service."""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._db = None
                self._initialized = False
                logger.info("Database service shut down successfully")
        except Exception as e:
            logger.error(f"Failed to shut down database service: {e}")
            # Don't raise exception on shutdown errors, but ensure cleanup
            self._client = None
            self._db = None
            self._initialized = False

    async def execute_query(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute an AQL query."""
        if not self._initialized:
            raise MCPError("NOT_INITIALIZED", "Service must be initialized before use")

        try:
            bind_vars = bind_vars or {}
            cursor = self._db.aql.execute(query, bind_vars=bind_vars)
            return [doc for doc in cursor]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise MCPError(
                "QUERY_ERROR",
                f"Query execution failed: {e}",
                {"query": query, "bind_vars": bind_vars}
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        if not self._initialized:
            return {"status": "not_initialized"}
        try:
            version = self._db.version()
            return {
                "status": "ok",
                "version": version
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            } 