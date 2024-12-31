#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import json
import signal
import logging
import functools
from typing import Any, Dict, List, Optional, Callable, TypeVar, cast, Union
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone
import asyncio

try:
    from pydantic import BaseModel, Field, validator, ValidationError, field_validator
    from pydantic_settings import BaseSettings
except ImportError as e:
    logging.error("Pydantic import error: %s", e, exc_info=True)
    sys.exit(1)

try:
    from mcp.server.fastmcp.server import FastMCP
    from mcp.client.stdio import StdioServerParameters
    from mcp.types import CallToolRequest, ListToolsRequest
except ImportError as e:
    logging.error("MCP module import error: %s", e)
    FastMCP = None  # Or handle it gracefully

try:
    import pymilvus
    from pymilvus import connections
except ImportError:
    pymilvus = None
    connections = None

try:
    from arango import ArangoClient
except ImportError:
    class ArangoClient:  # Provide a dummy class
        def __init__(self, *args, **kwargs):
            pass

# Type variables for generics
T = TypeVar('T')

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger('VectorDBMCPServer')

class DatabaseConfig(BaseSettings):
    """Configuration for ArangoDB connection."""
    url: str = Field(
        default="http://localhost:8529",
        env="ARANGO_URL",
        description="ArangoDB connection URL"
    )
    database: str = Field(
        default="_system",
        env="ARANGO_DB",
        description="ArangoDB database name"
    )
    username: str = Field(
        default="root",
        env="ARANGO_USER",
        description="ArangoDB username"
    )
    password: str = Field(
        default="",
        env="ARANGO_PASSWORD",
        description="ArangoDB password"
    )
    container_name: str = Field(
        default="hades_arangodb",
        env="ARANGO_CONTAINER_NAME",
        description="ArangoDB container name"
    )
    port: int = Field(
        default=8529,
        env="ARANGO_PORT",
        description="ArangoDB port number"
    )
    root_password: str = Field(
        default="your_secure_password",
        env="ARANGO_ROOT_PASSWORD",
        description="ArangoDB root password"
    )
    data_volume: str = Field(
        default="hades_arango_data",
        env="ARANGO_DATA_VOLUME",
        description="ArangoDB data volume name"
    )
    apps_volume: str = Field(
        default="hades_arango_apps",
        env="ARANGO_APPS_VOLUME",
        description="ArangoDB apps volume name"
    )

    model_config = {
        'env_file': '.env',
        'case_sensitive': False,
        'extra': 'allow',
        'env_prefix': '',
        'env_nested_delimiter': '__'
    }

class MilvusConfig(BaseSettings):
    """Configuration for Milvus connection."""
    host: str = Field(
        default="localhost",
        env="MILVUS_HOST",
        description="Milvus host"
    )
    port: int = Field(
        default=19530,
        env="MILVUS_PORT",
        description="Milvus port"
    )
    username: str = Field(
        default="root",
        env="MILVUS_USER",
        description="Milvus username"
    )
    password: str = Field(
        default="your_secure_password",
        env="MILVUS_PASSWORD",
        description="Milvus password"
    )
    container_name: str = Field(
        default="hades_milvus",
        env="MILVUS_CONTAINER_NAME",
        description="Milvus container name"
    )
    data_volume: str = Field(
        default="hades_milvus_data",
        env="MILVUS_DATA_VOLUME",
        description="Milvus data volume name"
    )

    model_config = {
        'env_file': '.env',
        'case_sensitive': False,
        'extra': 'allow',
        'env_prefix': '',
        'env_nested_delimiter': '__'
    }

    @field_validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

class ServerConfig(BaseSettings):
    """Configuration for server settings."""
    thread_pool_size: int = Field(
        default=5,
        env="SERVER_THREAD_POOL_SIZE",
        description="Thread pool size"
    )
    max_concurrent_requests: int = Field(
        default=100,
        env="SERVER_MAX_CONCURRENT_REQUESTS",
        description="Maximum concurrent requests"
    )
    request_timeout: float = Field(
        default=30.0,
        env="SERVER_REQUEST_TIMEOUT",
        description="Request timeout in seconds"
    )
    etcd_container_name: str = Field(
        default="hades_etcd",
        env="ETCD_CONTAINER_NAME",
        description="ETCD container name"
    )
    minio_container_name: str = Field(
        default="hades_minio",
        env="MINIO_CONTAINER_NAME",
        description="MinIO container name"
    )
    etcd_data_volume: str = Field(
        default="hades_etcd_data",
        env="ETCD_DATA_VOLUME",
        description="ETCD data volume name"
    )
    minio_data_volume: str = Field(
        default="hades_minio_data",
        env="MINIO_DATA_VOLUME",
        description="MinIO data volume name"
    )
    docker_network_name: str = Field(
        default="hades_network",
        env="DOCKER_NETWORK_NAME",
        description="Docker network name"
    )

    model_config = {
        'env_file': '.env',
        'case_sensitive': False,
        'extra': 'allow',
        'env_prefix': '',
        'env_nested_delimiter': '__'
    }

class QueryArgs(BaseModel):
    """Arguments for AQL query execution."""
    query: str = Field(
        ...,
        description="AQL query string",
        json_schema_extra={"env": "QUERY_ENV"}
    )
    bind_vars: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query bind variables"
    )

    model_config = {
        'extra': 'forbid'
    }

    @field_validator('query')
    def validate_query(cls, v: str) -> str:
        """
        Validate the query string.
        
        Args:
            cls: Class reference (automatically injected by Pydantic)
            v: Query string to validate
            
        Returns:
            Validated query string
            
        Raises:
            ValueError: If the query is empty or contains only whitespace
        """
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty")
        return v

class VectorSearchArgs(BaseModel):
    """Arguments for vector similarity search."""
    collection: str = Field(
        ...,
        description="Milvus collection name",
        json_schema_extra={"env": "MILVUS_COLLECTION_ENV"}
    )
    vector: List[float] = Field(
        ...,
        description="Query vector",
        json_schema_extra={"env": "VECTOR_ENV"}
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results",
        json_schema_extra={"env": "LIMIT_ENV"}
    )
    filters: Optional[str] = Field(
        default=None,
        description="Optional Milvus filter expression",
        json_schema_extra={"env": "FILTERS_ENV"}
    )

    model_config = {
        'extra': 'forbid'
    }

    @field_validator('vector')
    def validate_vector(cls, v: List[float]) -> List[float]:
        """
        Validate the vector parameter for vector search.
        
        Args:
            cls: Class reference (automatically injected by Pydantic)
            v: List of float values representing the vector
            
        Returns:
            The validated vector
            
        Raises:
            ValueError: If the vector is empty
        """
        if not v:
            raise ValueError("Vector cannot be empty")
        return v

class HybridSearchArgs(BaseModel):
    """Arguments for hybrid search across vector and document stores."""
    milvus_collection: str = Field(
        ...,
        description="Milvus collection for vector search",
        json_schema_extra={"env": "MILVUS_COLLECTION_ENV"}
    )
    arango_collection: str = Field(
        ...,
        description="ArangoDB collection for document data",
        json_schema_extra={"env": "ARANGO_COLLECTION_ENV"}
    )
    query_text: str = Field(
        ...,
        description="Search query text",
        json_schema_extra={"env": "QUERY_TEXT_ENV"}
    )
    vector: List[float] = Field(
        ...,
        description="Query vector for similarity search",
        json_schema_extra={"env": "VECTOR_ENV"}
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results",
        json_schema_extra={"env": "LIMIT_ENV"}
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional ArangoDB filters",
        json_schema_extra={"env": "FILTERS_ENV"}
    )

    model_config = {
        'extra': 'forbid'
    }

class MCPError(Exception):
    """Custom exception for MCP-related errors."""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.timestamp = datetime.now(timezone.utc)
        self.details = details or {}
        super().__init__(message)

class ConnectionManager:
    """Manages database connections with retry logic."""
    
    def __init__(
        self,
        db_config: DatabaseConfig,
        milvus_config: MilvusConfig,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.db_config = db_config
        self.milvus_config = milvus_config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None
        self._db = None
        self._milvus_connected = False
        self._lock = asyncio.Lock()

    async def get_db(self):
        """Get ArangoDB connection with retry logic."""
        async with self._lock:
            if not self._db:
                for attempt in range(self.max_retries):
                    try:
                        self._client = ArangoClient(hosts=self.db_config.url)
                        self._db = self._client.db(
                            self.db_config.database,
                            username=self.db_config.username,
                            password=self.db_config.password
                        )
                        break
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise MCPError(
                                "DB_CONNECTION_ERROR",
                                "Failed to connect to ArangoDB: %s" % e
                            )
                        await asyncio.sleep(self.retry_delay)
            return self._db

    async def ensure_milvus(self):
        """Ensure Milvus connection with retry logic."""
        async with self._lock:
            if not self._milvus_connected:
                for attempt in range(self.max_retries):
                    try:
                        connections.connect(
                            alias="default",
                            host=self.milvus_config.host,
                            port=self.milvus_config.port,
                            user=self.milvus_config.username,
                            password=self.milvus_config.password
                        )
                        self._milvus_connected = True
                        break
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise MCPError(
                                "MILVUS_CONNECTION_ERROR",
                                "Failed to connect to Milvus: %s" % e
                            )
                        await asyncio.sleep(self.retry_delay)

    def close(self):
        """Close all connections."""
        if self._client:
            self._client.close()
        if self._milvus_connected:
            connections.disconnect("default")
        self._client = None
        self._db = None
        self._milvus_connected = False

def mcp_tool(description: str):
    """
    Decorator to mark a method as an MCP tool, 
    attaching metadata used by VectorDBMCPServer.
    """
    def decorator(func: Callable):
        func.is_tool = True
        func.description = description
        return func
    return decorator

class VectorDBMCPServer(FastMCP):
    """Main server class implementing the MCP protocol for vector database operations."""

    def __init__(self):
        super().__init__(name="vector-db-mcp-server")
        
        # Load configurations
        self.server_config = ServerConfig()
        self.db_config = DatabaseConfig()
        self.milvus_config = MilvusConfig()
        
        # Initialize connection manager
        self.conn_manager = ConnectionManager(
            self.db_config,
            self.milvus_config
        )
        
        # Initialize thread pool for blocking operations
        self._executor = ThreadPoolExecutor(
            max_workers=self.server_config.thread_pool_size
        )
        
        # Initialize tools registry with caching
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._tool_schemas_cache: Dict[str, Dict[str, Any]] = {}
        self._register_tools()
        
        # Set server metadata and capabilities after initialization
        self.metadata = {
            "version": "0.1.0",
            "health_check": "/health"
        }
        self.capabilities = {
            "tools": self.tools,
            "async": True
        }
        
        # Register request handlers
        self.register_handler(ListToolsRequest, self.handle_list_tools)
        self.register_handler(CallToolRequest, self.handle_call_tool)

    def _register_tools(self) -> None:
        """
        Dynamically register all methods decorated with @mcp_tool.
        Caches tool schemas for performance.
        """
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, 'is_tool') and attr.is_tool:
                tool_name = attr_name.lower()
                
                # Use cached schema if available
                if tool_name in self._tool_schemas_cache:
                    schema = self._tool_schemas_cache[tool_name]
                else:
                    schema = self._get_tool_schema(attr)
                    self._tool_schemas_cache[tool_name] = schema
                
                self.tools[tool_name] = {
                    "description": attr.description,
                    "handler": attr,
                    "schema": schema
                }
        
        logger.info("Registered %d tools: %s", len(self.tools), list(self.tools.keys()))

    def register_handler(self, request_type, handler):
        """
        Register a request handler for the given request type.
        
        Args:
            request_type: Type of the request to handle (e.g., ListToolsRequest)
            handler: Callable that handles the request
        """
        if not hasattr(self, '_handlers'):
            self._handlers = {}
        self._handlers[request_type] = handler

    def handle_request(self, request):
        """
        Handle an incoming request using the registered handlers.
        
        Args:
            request: The request object to handle
            
        Returns:
            Response from the handler or error if no handler is found
        """
        handler = self._handlers.get(type(request))
        if handler:
            return handler(request)
        else:
            raise MCPError("REQUEST_TYPE_NOT_FOUND", f"No handler registered for {type(request)}")

    @staticmethod
    def _get_tool_schema(func: Callable) -> Dict[str, Any]:
        """
        Extract JSON schema from function signature using Pydantic models.
        Handles complex types and nested structures.
        """
        import inspect
        sig = inspect.signature(func)
        
        # Get the first parameter that's a Pydantic model
        for param in sig.parameters.values():
            if hasattr(param.annotation, 'model_json_schema'):
                return param.annotation.model_json_schema()
        
        # Create basic schema from annotations
        return {
            "type": "object",
            "properties": {
                name: VectorDBMCPServer._annotation_to_json_schema(param.annotation)
                for name, param in sig.parameters.items()
                if name != 'self'
            },
            "required": [
                name for name, param in sig.parameters.items()
                if name != 'self' and param.default == inspect.Parameter.empty
            ]
        }

    @staticmethod
    def _annotation_to_json_schema(annotation: Any) -> Dict[str, Any]:
        """Convert Python type annotations to JSON schema types."""
        from typing import get_origin, get_args
        
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            if type(None) in args:
                return {
                    "anyOf": [
                        VectorDBMCPServer._annotation_to_json_schema(arg)
                        for arg in args if arg != type(None)
                    ]
                }
        
        type_map = {
            str: {"type": "string"},
            int: {"type": "number", "multipleOf": 1},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            List[float]: {
                "type": "array",
                "items": {"type": "number"}
            },
            Dict[str, Any]: {
                "type": "object",
                "additionalProperties": True
            }
        }
        
        return type_map.get(annotation, {"type": "string"})

    @mcp_tool("Execute an AQL query with parameter binding and error handling")
    async def execute_query(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute an AQL query using proper parameter binding and error handling.
        
        Args:
            query: AQL query string
            bind_vars: Optional dictionary of bind variables
            
        Returns:
            List of query results
            
        Raises:
            MCPError: If query execution fails
        """
        try:
            db = await self.conn_manager.get_db()
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: db.aql.execute(query, bind_vars=bind_vars or {})
            )
        except Exception as e:
            logger.error("Query execution failed: %s", e, exc_info=True)
            raise MCPError(
                "QUERY_ERROR",
                "Query execution failed: %s" % e,
                {"query": query, "bind_vars": bind_vars}
            ) from e

    @mcp_tool("Perform hybrid search across vector and document stores")
    async def hybrid_search(
        self,
        args: HybridSearchArgs
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and document filtering.
        
        Args:
            args: HybridSearchArgs containing search parameters
            
        Returns:
            List of matched documents
            
        Raises:
            MCPError: If search operation fails
        """
        try:
            # Ensure Milvus connection
            await self.conn_manager.ensure_milvus()
            
            # Vector search implementation
            collection = pymilvus.Collection(args.milvus_collection)
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }
            
            # Execute vector search
            vector_results = collection.search(
                data=[args.vector],
                anns_field="embedding",
                param=search_params,
                limit=args.limit,
                expr=None  # We'll handle filtering in ArangoDB
            )
            
            # Extract document IDs from vector search results
            doc_ids = [str(hit.id) for hit in vector_results[0]]
            
            # Prepare AQL query with filters
            filter_conditions = []
            filter_binds = {}
            
            if args.filters:
                for key, value in args.filters.items():
                    param_name = "filter_%s" % key
                    filter_conditions.append("doc.%s == @%s" % (key, param_name))
                    filter_binds[param_name] = value
            
            filter_clause = " AND ".join(filter_conditions)
            
            aql = """
            FOR doc IN %s
            FILTER doc._key IN @keys
            %s
            RETURN doc
            """ % (
                args.arango_collection,
                "FILTER %s" % filter_clause if filter_conditions else ""
            )
            
            bind_vars = {"keys": doc_ids, **filter_binds}
            
            # Execute document lookup
            return await self.execute_query(aql, bind_vars)
            
        except Exception as e:
            logger.error("Hybrid search failed: %s", e, exc_info=True)
            raise MCPError(
                "HYBRID_SEARCH_ERROR",
                "Hybrid search failed: %s" % e,
                {
                    "milvus_collection": args.milvus_collection,
                    "arango_collection": args.arango_collection
                }
            )

    async def handle_list_tools(self, request: ListToolsRequest) -> Dict[str, List[Dict[str, Any]]]:
        """
        Handle tool listing requests.
        
        Args:
            request: ListToolsRequest object
            
        Returns:
            Dictionary containing list of available tools and their metadata
        """
        return {
            "tools": [
                {
                    "name": name,
                    "description": info["description"],
                    "inputSchema": info["schema"]
                }
                for name, info in self.tools.items()
            ]
        }

    async def handle_call_tool(self, request: CallToolRequest) -> Dict[str, Any]:
        """
        Handle tool execution requests with comprehensive error handling.
        
        Args:
            request: CallToolRequest object containing tool name and arguments
            
        Returns:
            Dictionary containing tool execution results or error details
        """
        request_id = "req_%d" % int(time.time() * 1000)
        logger.info("Processing tool call %s: %s", request_id, request.params.name)
        
        try:
            # Validate tool existence
            if request.params.name not in self.tools:
                raise MCPError(
                    "TOOL_NOT_FOUND",
                    "Tool '%s' not found" % request.params.name
                )

            tool = self.tools[request.params.name]
            
            # Validate arguments using tool's schema
            try:
                schema_model = tool.get("pydantic_model")
                if schema_model:
                    validated_args = schema_model.model_validate(request.params.arguments)
                else:
                    validated_args = request.params.arguments
            except ValidationError as e:
                logger.error("Validation error in %s: %s", request_id, e)
                return {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid arguments",
                        "details": e.errors()
                    },
                    "request_id": request_id
                }

            # Execute tool with timeout
            try:
                result = await asyncio.wait_for(
                    tool["handler"](validated_args),
                    timeout=self.server_config.request_timeout
                )
                return {
                    "success": True,
                    "result": result,
                    "request_id": request_id
                }
            except asyncio.TimeoutError:
                raise MCPError(
                    "TIMEOUT_ERROR",
                    "Tool execution timed out after %s" % self.server_config.request_timeout
                )

        except MCPError as e:
            logger.error("Tool error in %s: %s", request_id, e)
            return {
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                },
                "request_id": request_id
            }
        except Exception as e:
            logger.error("Unexpected error in %s: %s", request_id, e, exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {"error": str(e)}
                },
                "request_id": request_id
            }
        finally:
            logger.info("Completed tool call %s", request_id)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of server and dependencies.
        
        Returns:
            Dictionary containing health status details
        """
        status = {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "connections": {
                "arango": False,
                "milvus": False
            }
        }
        
        try:
            db = await self.conn_manager.get_db()
            status["connections"]["arango"] = True
        except Exception as e:
            status["status"] = "degraded"
            status["errors"] = {"arango": "%s" % e}
            
        try:
            await self.conn_manager.ensure_milvus()
            status["connections"]["milvus"] = True
        except Exception as e:
            status["status"] = "degraded"
            status["errors"] = status.get("errors", {})
            status["errors"]["milvus"] = "%s" % e
            
        return status

    def close(self) -> None:
        """Clean up resources and connections."""
        logger.info("Shutting down server...")
        self.conn_manager.close()
        self._executor.shutdown(wait=True)
        logger.info("Server shutdown complete")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received signal %d, initiating shutdown...", signum)
        self.close()
        sys.exit(0)

    def connect(self, transport):
        """Connect the server to the specified transport."""
        try:
            self.transport = transport
            self.start_time = time.time()
            # self.run_forever()
        except Exception as e:
            logger.error("Server connection failed: %s", e, exc_info=True)
            sys.exit(1)

    def run(self) -> None:
        """Start the server with stdio transport."""
        try:
            # Configure signal handlers
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
            
            # Initialize transport
            transport = StdioServerParameters(
                command="python",
                args=["HADES_MCP_Server.py"]
            )
            self.connect(transport)
            
            logger.info("Vector DB MCP Server running")
            logger.info("Connected to ArangoDB: %s", self.db_config.database)
            logger.info("Connected to Milvus: %s:%s", self.milvus_config.host, self.milvus_config.port)
            
        except Exception as e:
            logger.error("Server initialization failed: %s", e, exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    server = VectorDBMCPServer()
    try:
        server.run()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        server.close()
