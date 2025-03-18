
import asyncio
import websockets
import json
import logging
import os
import sys
import signal
from typing import Any, Dict, List, Optional, Callable, TextIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.utils.logger import get_logger
from src.core.security import Security
from src.db.connection import get_db_connection
from src.rag.path_rag import PathRAG

logger = logging.getLogger(__name__)

class MCPTool:
    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler

class MCPServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        # Load environment variables
        load_dotenv()
        
        # Log environment variables for debugging
        logger.info(f"ArangoDB URL: {os.environ.get('HADES_ARANGO_URL', 'http://localhost:8529')}")
        logger.info(f"ArangoDB Host: {os.environ.get('HADES_ARANGO_HOST', 'localhost')}")
        logger.info(f"ArangoDB Port: {os.environ.get('HADES_ARANGO_PORT', '8529')}")
        logger.info(f"ArangoDB User: {os.environ.get('HADES_ARANGO_USER', 'hades')}")
        logger.info(f"ArangoDB DB: {os.environ.get('HADES_ARANGO_DATABASE', 'hades_graph')}")
        
        self.host = host
        self.port = port
        self.security = Security()
        self.tools = {}
        
        # We'll create a fresh PathRAG instance for each method call rather than reusing
        # to avoid URL scheme issues
        self.register_default_tools()
        
    def register_tool(self, name: str, handler: Callable):
        """
        Register a new tool with the MCP server.
        
        Args:
            name: The name of the tool
            handler: The callable handler for the tool
        """
        logger.info(f"Registering tool: {name}")
        self.tools[name] = MCPTool(name, handler)
        
    def register_default_tools(self):
        """Register the default set of tools."""
        # Register database tools
        self.register_tool("show_databases", self.show_databases)
        
        # Register PathRAG tools
        self.register_tool("ingest_data", self.ingest_data)
        self.register_tool("pathrag_retrieve", self.pathrag_retrieve)
        
    async def show_databases(self, params: Dict[str, Any], session_data: Dict[str, Any]):
        """
        Tool handler to list all available databases.
        
        Args:
            params: Parameters for the tool
            session_data: Session data including authentication info
            
        Returns:
            Dict containing the list of databases
        """
        logger.info(f"Executing show_databases tool")
        
        # Check authentication
        if not session_data.get("authenticated", False):
            return {
                "success": False,
                "error": "Not authenticated"
            }
            
        # Get database connection
        db_connection = get_db_connection()
        
        # Get database list from PostgreSQL
        try:
            postgres_dbs = await db_connection.get_postgres_databases()
        except Exception as e:
            logger.error(f"Error getting PostgreSQL databases: {str(e)}")
            postgres_dbs = []
            
        # Get database list from ArangoDB
        try:
            arango_dbs = await db_connection.get_arango_databases()
        except Exception as e:
            logger.error(f"Error getting ArangoDB databases: {str(e)}")
            arango_dbs = []
            
        return {
            "success": True,
            "databases": {
                "postgresql": postgres_dbs,
                "arangodb": arango_dbs
            }
        }
    
    async def handle_client(self, websocket):
        """
        Handle client connection and messages.
        
        Args:
            websocket: The WebSocket connection
            path: The connection path
        """
        session_data = {
            "authenticated": False,
            "user_id": None
        }
        
        logger.info(f"Client connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(websocket, data, session_data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "success": False,
                        "error": "Invalid JSON message"
                    }))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        
    async def process_message(self, websocket, data: Dict[str, Any], session_data: Dict[str, Any]):
        """
        Process a message from a client.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
            session_data: Session-specific data
        """
        message_type = data.get("type")
        request_id = data.get("request_id", None)
        
        if message_type == "authenticate":
            await self.handle_authentication(websocket, data, session_data, request_id)
        elif message_type == "tool_call":
            await self.handle_tool_call(websocket, data, session_data, request_id)
        elif message_type == "discover":
            await self.handle_discover(websocket, data, session_data, request_id)
        else:
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": f"Unknown message type: {message_type}"
            }))
    
    async def handle_authentication(self, websocket, data: Dict[str, Any], session_data: Dict[str, Any], request_id: Optional[str]):
        """
        Handle authentication requests.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
            session_data: Session-specific data
            request_id: Optional request ID for response correlation
        """
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": "Username and password are required"
            }))
            return
        
        auth_result = self.security.authenticate(username, password)
        
        if auth_result["success"]:
            session_data["authenticated"] = True
            session_data["user_id"] = username
            session_data["token"] = auth_result["token"]
            
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": True,
                "token": auth_result["token"]
            }))
        else:
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": auth_result.get("error", "Authentication failed")
            }))
    
    async def ingest_data(self, params: Dict[str, Any], session_data: Dict[str, Any]):
        """
        Tool handler to ingest data into the knowledge graph using PathRAG.
        
        Args:
            params: Parameters for the tool including:
                - data: List of data points to ingest
                - domain: Domain to associate with the data
                - as_of_version: Optional version to tag the data with
            session_data: Session data including authentication info
            
        Returns:
            Dict containing the ingestion status and metadata
        """
        logger.info(f"Executing ingest_data tool")
        
        # Check authentication
        if not session_data.get("authenticated", False):
            return {
                "success": False,
                "error": "Not authenticated"
            }
        
        # Extract parameters
        data_points = params.get("data", [])
        domain = params.get("domain", "general")
        as_of_version = params.get("as_of_version")
        
        # Validate parameters
        if not data_points:
            return {
                "success": False,
                "error": "No data provided for ingestion"
            }
        
        if not isinstance(data_points, list):
            return {
                "success": False,
                "error": "Data must be a list of data points"
            }
        
        try:
            # Create a new instance of the path_rag for this request to avoid URL scheme issues
            from src.rag.path_rag import PathRAG
            
            # Get our environment URL
            arango_url = os.environ.get('HADES_ARANGO_URL', 'http://localhost:8529')
            logger.info(f"Creating fresh PathRAG instance with URL: {arango_url} for ingestion")
            
            # Initialize PathRAG - it will use our URL from the environment
            fresh_path_rag = PathRAG()
            
            # Call the PathRAG ingestion method
            result = fresh_path_rag.ingest_data(
                data=data_points,
                domain=domain,
                as_of_version=as_of_version
            )
        except Exception as e:
            logger.error(f"Error in ingest_data: {e}")
            return {
                "success": False,
                "error": f"Error ingesting data: {str(e)}"
            }
        
        return result
    
    async def pathrag_retrieve(self, params: Dict[str, Any], session_data: Dict[str, Any]):
        """
        Tool handler to retrieve paths using PathRAG.
        
        Args:
            params: Parameters for the tool including:
                - query: The query to retrieve paths for
                - max_paths: Maximum number of paths to retrieve
                - domain_filter: Optional domain filter
                - as_of_version: Optional version to query against
            session_data: Session data including authentication info
            
        Returns:
            Dict containing the retrieved paths and metadata
        """
        logger.info(f"Executing pathrag_retrieve tool")
        
        # Check authentication
        if not session_data.get("authenticated", False):
            return {
                "success": False,
                "error": "Not authenticated"
            }
        
        # Extract parameters
        query = params.get("query", "")
        max_paths = params.get("max_paths", 5)
        domain_filter = params.get("domain_filter")
        as_of_version = params.get("as_of_version")
        
        # Validate parameters
        if not query:
            return {
                "success": False,
                "error": "Query is required"
            }
        
        try:
            # Create a new instance of the path_rag for this request to avoid URL scheme issues
            from src.rag.path_rag import PathRAG
            from src.db.arangodb_connection_fix_v2 import DirectArangoAPI
            
            # Create a DirectArangoAPI instance with our environment URL
            # This ensures we use the full URL with scheme
            arango_url = os.environ.get('HADES_ARANGO_URL', 'http://localhost:8529')
            logger.info(f"Creating fresh PathRAG instance with URL: {arango_url}")
            
            # Initialize PathRAG with proper URL from environment
            # Just create the PathRAG instance; it will use our URL from the environment
            fresh_path_rag = PathRAG()
            
            # Call the PathRAG service using the fresh instance
            result = fresh_path_rag.retrieve_paths(
                query=query,
                max_paths=max_paths,
                domain_filter=domain_filter,
                as_of_version=as_of_version
            )
            
            logger.info(f"PathRAG retrieve result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error retrieving paths: {e}")
            return {
                "success": False,
                "error": f"Error retrieving paths: {str(e)}"
            }
    
    async def handle_tool_call(self, websocket, data: Dict[str, Any], session_data: Dict[str, Any], request_id: Optional[str]):
        """
        Handle tool call requests.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
            session_data: Session-specific data
            request_id: Optional request ID for response correlation
        """
        tool_name = data.get("name")
        params = data.get("arguments", {})
        
        if not tool_name:
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": "Tool name is required"
            }))
            return
        
        if tool_name not in self.tools:
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }))
            return
        
        try:
            tool = self.tools[tool_name]
            result = await tool.handler(params, session_data)
            
            await websocket.send(json.dumps({
                "request_id": request_id,
                **result
            }))
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            await websocket.send(json.dumps({
                "request_id": request_id,
                "success": False,
                "error": f"Error executing tool: {str(e)}"
            }))
    
    def describe_tools(self):
        """Generate tool descriptions in MCP format."""
        tool_descriptions = []
        
        # Describe the ingest_data tool
        ingest_data_tool = {
            "name": "ingest_data",
            "description": "Ingest data into the knowledge graph using PathRAG",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "description": "List of data points to ingest"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain to associate with the data",
                        "default": "general"
                    },
                    "as_of_version": {
                        "type": "string",
                        "description": "Optional version to tag the data with"
                    }
                },
                "required": ["data"]
            }
        }
        
        # Describe the pathrag_retrieve tool
        pathrag_retrieve_tool = {
            "name": "pathrag_retrieve",
            "description": "Retrieve paths from the knowledge graph using PathRAG",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to retrieve paths for"
                    },
                    "max_paths": {
                        "type": "integer",
                        "description": "Maximum number of paths to retrieve",
                        "default": 5
                    },
                    "domain_filter": {
                        "type": "string",
                        "description": "Optional domain filter"
                    },
                    "as_of_version": {
                        "type": "string",
                        "description": "Optional version to query against"
                    }
                },
                "required": ["query"]
            }
        }
        
        # Describe the show_databases tool
        show_databases_tool = {
            "name": "show_databases",
            "description": "List all available databases",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
        
        tool_descriptions.extend([ingest_data_tool, pathrag_retrieve_tool, show_databases_tool])
        return tool_descriptions
    
    async def handle_discover(self, websocket, data: Dict[str, Any], session_data: Dict[str, Any], request_id: Optional[str]):
        """
        Handle tool discovery requests.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
            session_data: Session-specific data
            request_id: Optional request ID for response correlation
        """
        logger.info(f"Handling discover request")
        
        # Generate tool descriptions
        tool_descriptions = self.describe_tools()
        
        # Send the discovery response
        await websocket.send(json.dumps({
            "request_id": request_id,
            "success": True,
            "tools": tool_descriptions
        }))
    
    async def start(self):
        """Start the MCP WebSocket server."""
        logger.info(f"Starting MCP server on {self.host}:{self.port}")
        logger.info(f"Registered tools: {', '.join(self.tools.keys())}")
        server = await websockets.serve(self.handle_client, self.host, self.port)
        
        # Keep the server running
        await server.wait_closed()
    
    async def run_stdio(self):
        """Run the MCP server using stdio transport for Windsurf integration."""
        logger.info("Starting MCP server with stdio transport")
        logger.info(f"Registered tools: {', '.join(self.tools.keys())}")
        
        loop = asyncio.get_event_loop()
        
        # Set up signal handling for clean shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        try:
            # Create reader and writer for stdin/stdout
            stdin_reader = asyncio.StreamReader()
            stdin_protocol = asyncio.StreamReaderProtocol(stdin_reader)
            await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin)
            
            stdout_transport, stdout_protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout
            )
            stdout_writer = asyncio.StreamWriter(stdout_transport, stdout_protocol, None, loop)
            
            # Set up logging to stderr
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            # Send server ready message to stderr
            print("MCP server ready (stdio mode)", file=sys.stderr)
            sys.stderr.flush()
            
            await self.handle_stdio(stdin_reader, stdout_writer)
        except Exception as e:
            logger.error(f"Error in stdio transport: {str(e)}")
            print(f"Fatal error: {str(e)}", file=sys.stderr)
            sys.stderr.flush()
            raise
    
    async def handle_stdio(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle communication over stdin/stdout for the MCP server."""
        session_data = {
            "authenticated": True,  # Auto-authenticate for stdio transport
            "user_id": "stdio-user"
        }
        
        logger.info("Stdio client connected")
        
        # Send server capabilities upon startup
        # This is part of the implicit protocol expected by some MCP clients
        server_info = {
            "jsonrpc": "2.0", 
            "method": "serverInfo", 
            "params": {
                "name": "HADES MCP Server",
                "version": "1.0.0", 
                "capabilities": {
                    "tools": {"listChanged": True},
                    "prompts": False,
                    "resources": False
                }
            }
        }
        writer.write((json.dumps(server_info) + '\n').encode('utf-8'))
        await writer.drain()

        # Add a delay to ensure proper sequencing
        await asyncio.sleep(0.1)
        
        # Instead of automatically announcing tools, wait for a list_tools request
        # The client will explicitly request tools when it's ready
        
        while True:
            try:
                # Read a line from stdin
                line = await reader.readline()
                logger.info(f"Received: {line}")
                
                if not line:
                    logger.info("Received empty line, ending session")
                    break
                    
                # Parse JSON-RPC message
                try:
                    data = json.loads(line.decode('utf-8'))
                    response = await self.process_stdio_message(data, session_data)
                    
                    # Write response to stdout
                    logger.info(f"Sending response: {response}")
                    writer.write((json.dumps(response) + '\n').encode('utf-8'))
                    await writer.drain()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)} for input: {line.decode('utf-8')}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
                    await writer.drain()
                    
            except Exception as e:
                logger.error(f"Error handling stdio message: {str(e)}")
                # Don't break, try to continue processing messages
                
        logger.info("Stdio client disconnected")
    
    async def process_stdio_message(self, data: Dict[str, Any], session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JSON-RPC message from stdio and return a response."""
        method = data.get("method")
        params = data.get("params", {})
        id = data.get("id")
        
        # Standard JSON-RPC response format
        response = {
            "jsonrpc": "2.0",
            "id": id
        }
        
        try:
            if method == "initialize":
                # Get the protocol version from the client request
                protocol_version = params.get("protocolVersion", "2024-11-05")
                logger.info(f"Client requested protocol version: {protocol_version}")
                
                # Handle initialization
                response["result"] = {
                    "serverInfo": {
                        "name": "HADES MCP Server",
                        "version": "1.0.1"
                    },
                    "capabilities": {
                        "tools": {"listChanged": True}
                    },
                    "protocolVersion": protocol_version
                }
            elif method == "shutdown":
                # Handle shutdown
                response["result"] = None
            elif method == "tools/list":
                # List available tools (using tools/list method as per MCP spec)
                tools = self.describe_tools()
                logger.info(f"Sending tool list with {len(tools)} tools: {[t['name'] for t in tools]}")
                response["result"] = {
                    "tools": tools
                }
            elif method == "tools/call":
                # Execute a tool (using tools/call method as per MCP spec)
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name in self.tools:
                    try:
                        result = await self.tools[tool_name].handler(tool_args, session_data)
                        # Format the result according to MCP protocol
                        # Convert our existing result format to MCP content format
                        success = result.get("success", True)
                        if success:
                            text_content = json.dumps(result, indent=2)
                            response["result"] = {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": text_content
                                    }
                                ]
                            }
                        else:
                            # Report errors according to MCP protocol
                            error_text = result.get("error", "Unknown error")
                            response["result"] = {
                                "isError": True,
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Error: {error_text}"
                                    }
                                ]
                            }
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {str(e)}")
                        response["result"] = {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error executing tool: {str(e)}"
                                }
                            ]
                        }
                else:
                    response["error"] = {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
            elif method == "resources/list":
                # Handle resources/list - Return empty array to indicate no resources are available
                logger.info("Received resources/list request, returning empty array")
                response["result"] = {
                    "resources": []
                }
            elif method == "resources/templates/list":
                # Handle resources/templates/list - Return empty array to indicate no templates are available
                logger.info("Received resources/templates/list request, returning empty array")
                response["result"] = {
                    "templates": []
                }
            elif method == "notifications/initialized":
                # Handle notifications/initialized - Acknowledge but return no result
                logger.info("Received notifications/initialized request")
                response["result"] = None
            else:
                # Unknown method
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            response["error"] = {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
            
        return response
    
    async def shutdown(self):
        """Gracefully shut down the server."""
        logger.info("Shutting down MCP server")
        # Perform any cleanup here
        asyncio.get_running_loop().stop()
        
    def run(self):
        """Run the MCP server synchronously."""
        asyncio.run(self.start())
    
    def run_stdio_sync(self):
        """Run the MCP server with stdio transport synchronously."""
        asyncio.run(self.run_stdio())

# Server instance to be used by other modules
mcp_server = MCPServer()

# Entry point when running this file directly
if __name__ == "__main__":
    # Check if we should use stdio transport (for Windsurf/Codeium)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        mcp_server.run_stdio_sync()
    else:
        mcp_server.run()
