"""Connection manager for the MCP server."""

import logging
from typing import Dict, Any
from ..core.exceptions import MCPError
from ..services.database import DatabaseService
from ..services.vector import VectorService

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages database and vector store connections."""

    def __init__(
        self,
        db_service: DatabaseService,
        vector_service: VectorService,
        retry_delay: float = 1.0,
        max_retries: int = 3
    ):
        """Initialize connection manager."""
        self.db_service = db_service
        self.vector_service = vector_service
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all connections."""
        try:
            await self.db_service.initialize()
            await self.vector_service.initialize()
            self._initialized = True
            logger.info("All connections initialized successfully")
        except Exception as e:
            self._initialized = False
            logger.error("Failed to initialize connections: %s", e, exc_info=True)
            raise MCPError(
                "INIT_ERROR",
                f"Connection failed: {e}"
            )

    async def shutdown(self) -> None:
        """Shut down all connections."""
        errors = []
        try:
            await self.db_service.shutdown()
        except Exception as e:
            errors.append(e)
            logger.error("Error during database shutdown: %s", e, exc_info=True)

        try:
            await self.vector_service.shutdown()
        except Exception as e:
            errors.append(e)
            logger.error("Error during vector service shutdown: %s", e, exc_info=True)

        self._initialized = False

        if errors:
            raise MCPError(
                "SHUTDOWN_ERROR",
                f"Shutdown failed: {errors[0]}"
            )
        logger.info("All connections shut down successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all connections."""
        if not self._initialized:
            return {"status": "not_initialized"}

        try:
            db_health = await self.db_service.health_check()
            vector_health = await self.vector_service.health_check()

            status = "ok"
            if db_health["status"] != "ok" or vector_health["status"] != "ok":
                status = "degraded"

            return {
                "status": status,
                "services": {
                    "database": db_health,
                    "vector": vector_health
                }
            }
        except Exception as e:
            logger.error("Health check failed: %s", e, exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            } 