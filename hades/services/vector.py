"""Vector search service for similarity search."""

import logging
from typing import Dict, Any, List, Optional
from pymilvus import Collection, connections

from hades.core.config import MilvusConfig
from hades.core.exceptions import MCPError

logger = logging.getLogger(__name__)

class VectorService:
    """Service for vector similarity search."""

    def __init__(self, config: MilvusConfig):
        """Initialize vector service."""
        self.config = config.model_dump()
        self._client = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    def _create_client(self) -> Collection:
        """Create Milvus client."""
        try:
            connections.connect(
                alias="default",
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"]
            )
            return Collection(self.config["collection"])
        except MCPError as e:
            logger.error(f"Failed to create Milvus client: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Milvus client: {e}")
            raise MCPError("INIT_ERROR", f"Failed to create Milvus client: {e}")

    async def initialize(self) -> None:
        """Initialize vector service."""
        try:
            if self._initialized:
                return

            self._client = self._create_client()
            self._initialized = True
            logger.info("Vector service initialized successfully")
        except MCPError as e:
            logger.error(f"Failed to initialize vector service: {e}")
            self._initialized = False
            raise
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            self._initialized = False
            raise MCPError("INIT_ERROR", f"Failed to initialize vector service: {e}")

    async def shutdown(self) -> None:
        """Shut down vector service."""
        try:
            if self._client:
                connections.disconnect("default")
            self._client = None
            self._initialized = False
            logger.info("Vector service shut down successfully")
        except Exception as e:
            logger.error(f"Failed to shut down vector service: {e}")
            raise MCPError("SHUTDOWN_ERROR", f"Failed to shut down vector service: {e}")

    async def search(
        self,
        vector: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        if not self._initialized:
            raise MCPError("NOT_INITIALIZED", "Service must be initialized before use")
        
        # Validate vector
        if not isinstance(vector, list):
            raise MCPError(
                "VALIDATION_ERROR",
                "Invalid vector type",
                {"vector": vector}
            )
        if not vector:
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector cannot be empty",
                {"vector": vector}
            )
        if not all(isinstance(x, (int, float)) for x in vector):
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector must contain only numbers",
                {"vector": vector}
            )
        
        # Validate top_k
        if not isinstance(top_k, int) or top_k <= 0:
            raise MCPError(
                "VALIDATION_ERROR",
                "top_k must be positive",
                {"top_k": top_k}
            )

        try:
            results = self._client.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=top_k
            )
            if not results or not results[0]:
                return []
            return [
                {"id": str(hit.id), "distance": hit.distance}
                for hit in results[0]
            ]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise MCPError(
                "SEARCH_ERROR",
                f"Vector search failed: {e}",
                {"vector": vector, "top_k": top_k}
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        if not self._initialized:
            return {"status": "not_initialized"}
        try:
            info = self._client.server_info()
            return {
                "status": "ok",
                "version": info["version"]
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            } 