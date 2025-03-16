import asyncio
import websockets
import json
import logging
from typing import Any, Dict, List, Optional, Callable

from src.utils.logger import get_logger
from src.core.security import Security
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

class MCPTool:
    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler

class MCPServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.security = Security()
        self.tools = {}
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
        self.register_tool("show_databases", self.show_databases)
        
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
    
    async def handle_tool_call(self, websocket, data: Dict[str, Any], session_data: Dict[str, Any], request_id: Optional[str]):
        """
        Handle tool call requests.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
            session_data: Session-specific data
            request_id: Optional request ID for response correlation
        """
        tool_name = data.get("tool")
        params = data.get("params", {})
        
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
    
    async def start(self):
        """Start the MCP WebSocket server."""
        logger.info(f"Starting MCP server on {self.host}:{self.port}")
        server = await websockets.serve(self.handle_client, self.host, self.port)
        
        # Keep the server running
        await server.wait_closed()
        
    def run(self):
        """Run the MCP server synchronously."""
        asyncio.run(self.start())

# Server instance to be used by other modules
mcp_server = MCPServer()

# Entry point when running this file directly
if __name__ == "__main__":
    mcp_server.run()
