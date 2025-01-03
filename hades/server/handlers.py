"""Request handlers for the HADES server."""

import logging
from functools import wraps
from typing import Dict, Any, List, Optional, Callable, Awaitable

from hades.core.exceptions import MCPError
from hades.core.models import CallToolRequest, ListToolsRequest

logger = logging.getLogger(__name__)

def mcp_tool(description: str = None):
    """Decorator for MCP tool methods."""
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Dict[str, Any]]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MCPError:
                raise
            except Exception as e:
                logger.error("Tool execution failed: %s", e, exc_info=True)
                raise MCPError(
                    "TOOL_ERROR",
                    f"Tool execution failed: {e}",
                    {"tool": func.__name__}
                )
        wrapper.is_tool = True
        wrapper.description = description or func.__doc__ or "No description available"
        return wrapper
    return decorator

class RequestHandler:
    """Handler for MCP requests."""

    def __init__(self, services: Dict[str, Any]):
        """Initialize request handler."""
        self.services = services
        self._tools = {}
        self._register_tools()

    @property
    def db_service(self):
        """Get database service."""
        return self.services["db_service"]

    @property
    def vector_service(self):
        """Get vector service."""
        return self.services["vector_service"]

    @property
    def hybrid_service(self):
        """Get hybrid search service."""
        return self.services["hybrid_service"]

    def _register_tools(self) -> None:
        """Register available tools."""
        self._tools = {
            "execute_query": {
                "handler": self.execute_query,
                "description": "Execute database query",
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            },
            "vector_search": {
                "handler": self.vector_search,
                "description": "Perform vector similarity search",
                "schema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "vector": {"type": "array", "items": {"type": "number"}},
                        "top_k": {"type": "integer", "minimum": 1}
                    },
                    "required": ["collection", "vector"]
                }
            },
            "hybrid_search": {
                "handler": self.hybrid_search,
                "description": "Perform hybrid search",
                "schema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "vector": {"type": "array", "items": {"type": "number"}},
                        "filter_query": {"type": "string"},
                        "top_k": {"type": "integer", "minimum": 1}
                    },
                    "required": ["collection", "vector", "filter_query"]
                }
            }
        }

    @property
    def tools(self) -> Dict[str, Dict[str, Any]]:
        """Get registered tools."""
        return self._tools

    async def handle_request(self, request: CallToolRequest | ListToolsRequest) -> Dict[str, Any]:
        """Handle incoming request."""
        try:
            if isinstance(request, ListToolsRequest):
                return await self.handle_list_tools_request()
            elif isinstance(request, CallToolRequest):
                return await self.handle_tool_call(request)
            else:
                raise MCPError(
                    "INVALID_REQUEST",
                    f"Invalid request type: {type(request)}"
                )
        except MCPError as e:
            return {
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            }
        except Exception as e:
            logger.error("Request handling failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

    async def handle_list_tools_request(self) -> Dict[str, Any]:
        """Handle list tools request."""
        return {
            "success": True,
            "tools": [
                {
                    "name": name,
                    "description": info["description"],
                    "schema": info["schema"]
                }
                for name, info in self._tools.items()
            ]
        }

    async def handle_tool_call(self, request: CallToolRequest) -> Dict[str, Any]:
        """Handle tool call request."""
        if request.tool_name not in self._tools:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_TOOL",
                    "message": f"Unknown tool: {request.tool_name}"
                }
            }

        try:
            result = await self._tools[request.tool_name]["handler"](**request.args)
            return {
                "success": True,
                "result": result
            }
        except MCPError as e:
            if e.code == "VALIDATION_ERROR":
                return {
                    "success": False,
                    "error": {
                        "code": e.code,
                        "message": e.message,
                        "details": e.details
                    }
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(e)
                    }
                }
        except Exception as e:
            logger.error("Tool execution failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

    @mcp_tool("Execute database query")
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute database query."""
        return await self.services["db_service"].execute_query(query)

    @mcp_tool("Perform vector similarity search")
    async def vector_search(self, collection: str, vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        if not vector:
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector validation failed: vector cannot be empty",
                {"param": "vector"}
            )
        if top_k <= 0:
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector validation failed: top_k must be positive",
                {"param": "top_k"}
            )
        return await self.services["vector_service"].search(collection, vector, top_k)

    @mcp_tool("Perform hybrid search")
    async def hybrid_search(self, collection: str, vector: List[float], filter_query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform hybrid search."""
        if not vector:
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector validation failed: vector cannot be empty",
                {"param": "vector"}
            )
        if top_k <= 0:
            raise MCPError(
                "VALIDATION_ERROR",
                "Vector validation failed: top_k must be positive",
                {"param": "top_k"}
            )
        return await self.services["hybrid_service"].search(collection, vector, filter_query, top_k) 