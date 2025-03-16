#!/usr/bin/env python
# MCP Test Client
# This script tests connection to the MCP server and calls the show_databases tool

import asyncio
import websockets
import json
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_mcp_server():
    """Connect to MCP server and call the show_databases tool."""
    print("Connecting to MCP server at ws://localhost:8765...")
    
    async with websockets.connect("ws://localhost:8765") as websocket:
        print("Connected to MCP server")
        
        # Authenticate (if enabled)
        auth_message = {
            "type": "authenticate",
            "username": "admin",
            "password": "password"
        }
        
        await websocket.send(json.dumps(auth_message))
        response = await websocket.recv()
        print(f"Authentication response: {response}")
        
        auth_result = json.loads(response)
        if not auth_result.get("success", False):
            print("Authentication failed!")
            return
            
        # Call the show_databases tool
        tool_message = {
            "type": "tool_call",
            "request_id": "test-request-1",
            "tool": "show_databases",
            "params": {}
        }
        
        print("\nCalling show_databases tool...")
        await websocket.send(json.dumps(tool_message))
        response = await websocket.recv()
        print(f"Tool response: {json.dumps(json.loads(response), indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
