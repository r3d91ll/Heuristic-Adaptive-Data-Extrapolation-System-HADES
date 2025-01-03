"""Main MCP server implementation."""

import logging
import signal
import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Union

from ..core.config import ServerConfig, DatabaseConfig, MilvusConfig
from ..core.exceptions import MCPError
from ..core.models import CallToolRequest, ListToolsRequest
from .connection import ConnectionManager
from .handlers import RequestHandler
from ..services.hybrid import HybridSearchService

logger = logging.getLogger(__name__)

class MCPServer:
    """Base MCP server implementation."""

    def __init__(
        self,
        server_config: Optional[ServerConfig] = None,
        db_config: Optional[DatabaseConfig] = None,
        milvus_config: Optional[MilvusConfig] = None
    ):
        """Initialize the MCP server."""
        self.name = "mcp-server"
        self.server_config = server_config or ServerConfig()
        self.db_config = db_config or DatabaseConfig()
        self.milvus_config = milvus_config or MilvusConfig()
        
        # Initialize components
        self.conn_manager = ConnectionManager(
            self.db_config,
            self.milvus_config
        )
        self._executor = ThreadPoolExecutor(
            max_workers=self.server_config.thread_pool_size
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        self.start_time = time.time()

    async def initialize(self) -> None:
        """Initialize server components."""
        try:
            # Initialize connections
            await self.conn_manager.initialize()
            
            # Initialize services
            self.hybrid_service = HybridSearchService(
                self.conn_manager.db_service,
                self.conn_manager.vector_service
            )
            await self.hybrid_service.initialize()
            
            # Initialize request handler with services dictionary
            self.handler = RequestHandler({
                "db_service": self.conn_manager.db_service,
                "vector_service": self.conn_manager.vector_service,
                "hybrid_service": self.hybrid_service
            })
            
            logger.info("Server initialized successfully")
        except Exception as e:
            logger.error("Server initialization failed: %s", e, exc_info=True)
            raise MCPError(
                "SERVER_INIT_ERROR",
                f"Server initialization failed: {e}"
            )

    def close(self) -> None:
        """Clean up server resources."""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            logger.info("Server shut down successfully")
        except Exception as e:
            logger.error("Error during server shutdown: %s", e, exc_info=True)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.close()
        sys.exit(0)

    async def handle_request(
        self,
        request: Union[CallToolRequest, ListToolsRequest]
    ) -> Dict[str, Any]:
        """Handle incoming requests."""
        try:
            return await self.handler.handle_request(request)
        except Exception as e:
            logger.error("Request handling failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "REQUEST_ERROR",
                    "message": str(e)
                }
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        try:
            uptime = time.time() - self.start_time
            conn_status = await self.conn_manager.health_check()
            
            status = "ok"
            if conn_status["status"] != "ok":
                status = "degraded"
            
            return {
                "status": status,
                "uptime": uptime,
                "connections": conn_status
            }
        except Exception as e:
            logger.error("Health check failed: %s", e, exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            } 