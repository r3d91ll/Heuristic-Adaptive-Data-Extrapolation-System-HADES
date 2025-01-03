"""Hybrid search service combining vector and database search."""

import logging
from typing import Dict, Any, List, Optional

from hades.core.config import HybridSearchConfig
from hades.core.exceptions import MCPError
from hades.services.database import DatabaseService
from hades.services.vector import VectorService

logger = logging.getLogger(__name__)

class HybridSearchService:
    """Service for hybrid search combining vector and database search."""

    def __init__(
        self,
        config: HybridSearchConfig,
        db_service: DatabaseService,
        vector_service: VectorService
    ):
        """Initialize hybrid search service."""
        self.config = config.model_dump()
        self._db_service = db_service
        self._vector_service = vector_service
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize hybrid search service."""
        try:
            if self._initialized:
                return

            await self._db_service.initialize()
            await self._vector_service.initialize()
            self._initialized = True
            logger.info("Hybrid search service initialized successfully")
        except MCPError as e:
            logger.error(f"Failed to initialize hybrid search service: {e}")
            self._initialized = False
            raise
        except Exception as e:
            logger.error(f"Failed to initialize hybrid search service: {e}")
            self._initialized = False
            raise MCPError("INIT_ERROR", f"Failed to initialize hybrid search service: {e}")

    async def search(
        self,
        vector: List[float],
        filter_query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and database search."""
        if not self._initialized:
            raise MCPError("NOT_INITIALIZED", "not initialized")

        if not vector:
            raise MCPError("VALIDATION_ERROR", "vector cannot be empty")

        if top_k <= 0:
            raise MCPError("VALIDATION_ERROR", "top_k must be positive")

        try:
            # Perform vector search
            vector_results = await self._vector_service.search(vector, top_k)

            if not vector_results:
                return []

            # Extract IDs from vector search results
            ids = [result["_id"] for result in vector_results]
            scores = {result["_id"]: result["score"] for result in vector_results}

            # Build AQL query with filter
            query = f"""
            FOR doc IN {self.config["collection"]}
            FILTER doc.{self.config["id_field"]} IN @ids
            AND ({filter_query})
            RETURN doc
            """
            bind_vars = {"ids": ids}

            # Execute database query
            results = await self._db_service.execute_query(query, bind_vars)

            # Add scores to results
            for result in results:
                result["score"] = scores.get(result["_id"], 0)

            # Sort results by score
            results.sort(key=lambda x: x["score"], reverse=True)
            return results

        except MCPError as e:
            # Re-raise MCPError with original code
            raise
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise MCPError(
                "SEARCH_ERROR",
                f"Hybrid search failed: {e}",
                {"vector": vector, "filter_query": filter_query, "top_k": top_k}
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        if not self._initialized:
            return {"status": "error", "message": "not initialized"}
        try:
            db_health = await self._db_service.health_check()
            vector_health = await self._vector_service.health_check()

            if db_health["status"] != "ok" or vector_health["status"] != "ok":
                return {
                    "status": "error",
                    "message": f"Service degraded - DB: {db_health.get('message', 'Unknown error')}, Vector: {vector_health.get('message', 'Unknown error')}"
                }

            return {
                "status": "ok",
                "message": f"DB healthy: {db_health.get('message', '')}, Vector healthy: {vector_health.get('message', '')}",
                "db_version": db_health.get("version"),
                "vector_version": vector_health.get("version")
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            } 