#!/usr/bin/env python3
import asyncio
import json
import websockets
import sys
import os
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
SERVER_URI = "ws://localhost:8765"

class TestClient:
    def __init__(self, server_uri="ws://localhost:8765"):
        self.server_uri = server_uri
        self.websocket = None
        self.authenticated = False
        self.token = None
    
    async def connect(self):
        """Connect to the MCP server."""
        try:
            self.websocket = await websockets.connect(self.server_uri)
            logger.info(f"Connected to MCP server at {self.server_uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def close(self):
        """Close the connection to the MCP server."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Closed connection to MCP server")
            self.websocket = None
            self.authenticated = False
            self.token = None
    
    async def send_request(self, request_data):
        """Send a request to the MCP server."""
        if not self.websocket:
            logger.error("Not connected to MCP server")
            return {"success": False, "error": "Not connected to MCP server"}
        
        try:
            # Convert the request data to JSON
            request_json = json.dumps(request_data)
            logger.info(f"Sending request: {request_json}")
            
            # Send the request
            await self.websocket.send(request_json)
            
            # Receive the response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            logger.info(f"Received response: {json.dumps(response_data, indent=2)}")
            
            return response_data
        except Exception as e:
            logger.exception(f"Error during communication with MCP server: {e}")
            return {"success": False, "error": str(e)}
    
    async def authenticate(self):
        """Authenticate with the MCP server."""
        auth_request = {
            "type": "authenticate",
            "username": "admin",
            "password": "password",
            "request_id": "auth-1"
        }
        
        response = await self.send_request(auth_request)
        
        if response.get("success", False):
            self.authenticated = True
            self.token = response.get("token")
            logger.info(f"Successfully authenticated, token: {self.token}")
        
        return response
    
    async def ingest_data(self):
        """Test the data ingestion functionality."""
        if not self.authenticated:
            logger.error("Not authenticated, please authenticate first")
            return {"success": False, "error": "Not authenticated"}
        
        # Sample data for testing
        test_data = [
            {
                "id": "entity1",
                "type": "person",
                "name": "John Doe",
                "properties": {
                    "age": 30,
                    "occupation": "Developer"
                },
                "relationships": [
                    {
                        "target": "entity2",
                        "type": "KNOWS",
                        "properties": {
                            "since": "2020-01-01"
                        }
                    }
                ]
            },
            {
                "id": "entity2",
                "type": "person",
                "name": "Jane Smith",
                "properties": {
                    "age": 28,
                    "occupation": "Data Scientist"
                },
                "relationships": [
                    {
                        "target": "entity3",
                        "type": "WORKS_WITH",
                        "properties": {
                            "project": "HADES"
                        }
                    }
                ]
            },
            {
                "id": "entity3",
                "type": "organization",
                "name": "TechCorp",
                "properties": {
                    "industry": "Software",
                    "founded": 2010
                }
            }
        ]
        
        # Prepare the ingest_data request
        ingest_request = {
            "type": "tool_call",
            "tool": "ingest_data",
            "params": {
                "data": test_data,
                "domain": "test_domain",
                "as_of_version": "1.0"
            },
            "request_id": "test-ingest-1"
        }
        
        return await self.send_request(ingest_request)
    
    async def retrieve_paths(self, query="Who is John Doe?", max_paths=3, domain_filter="test_domain"):
        """Test the PathRAG retrieval functionality.
        
        Args:
            query: The query to search for paths
            max_paths: Maximum number of paths to return
            domain_filter: Domain filter for the query
        """
        if not self.authenticated:
            logger.error("Not authenticated, please authenticate first")
            return {"success": False, "error": "Not authenticated"}
        
        retrieve_request = {
            "type": "tool_call",
            "tool": "pathrag_retrieve",
            "params": {
                "query": query,
                "max_paths": max_paths,
                "domain_filter": domain_filter
            },
            "request_id": "test-retrieve-1"
        }
        
        return await self.send_request(retrieve_request)

async def main():
    """Main function to run the test client."""
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <command> [query] [max_paths]")
        print("Available commands: auth, ingest, retrieve, full")
        print("For retrieve command, you can optionally specify a query entity and max_paths")
        print("Example: python test_client.py retrieve ArangoDB 5")
        return
    
    command = sys.argv[1].lower()
    
    # Check for optional query and max_paths parameters for retrieve command
    query = "ArangoDB"  # Default to our demo entity
    max_paths = 5
    
    if len(sys.argv) > 2 and (command == "retrieve" or command == "full"):
        query = sys.argv[2]
    
    if len(sys.argv) > 3 and (command == "retrieve" or command == "full"):
        try:
            max_paths = int(sys.argv[3])
        except ValueError:
            print(f"Invalid max_paths value: {sys.argv[3]}. Using default of 5.")
    
    client = TestClient()
    
    # Try to connect to the server
    if not await client.connect():
        print("Failed to connect to MCP server")
        return
    
    try:
        if command == "auth":
            # Test authentication only
            result = await client.authenticate()
            print(f"Authentication result: {json.dumps(result, indent=2)}")
        
        elif command == "ingest":
            # First authenticate
            auth_result = await client.authenticate()
            if not auth_result.get("success", False):
                print(f"Authentication failed: {auth_result}")
                return
            
            # Then ingest data
            ingest_result = await client.ingest_data()
            print(f"Data ingestion result: {json.dumps(ingest_result, indent=2)}")
        
        elif command == "retrieve":
            # First authenticate
            auth_result = await client.authenticate()
            if not auth_result.get("success", False):
                print(f"Authentication failed: {auth_result}")
                return
            
            # Then retrieve data using specified query and max_paths
            print(f"Retrieving paths for query: '{query}' with max_paths: {max_paths}")
            retrieve_result = await client.retrieve_paths(query=query, max_paths=max_paths)
            print(f"PathRAG retrieval result: {json.dumps(retrieve_result, indent=2)}")
        
        elif command == "full":
            # Run a full test: authenticate, ingest data, then retrieve paths
            print("\n=== Step 1: Authenticating ===\n")
            auth_result = await client.authenticate()
            if not auth_result.get("success", False):
                print(f"Authentication failed: {auth_result}")
                return
            
            print("\n=== Step 2: Ingesting Data ===\n")
            ingest_result = await client.ingest_data()
            print(f"Data ingestion result: {json.dumps(ingest_result, indent=2)}")
            
            print("\n=== Step 3: Retrieving Paths ===\n")
            print(f"Retrieving paths for query: '{query}' with max_paths: {max_paths}")
            retrieve_result = await client.retrieve_paths(query=query, max_paths=max_paths)
            print(f"PathRAG retrieval result: {json.dumps(retrieve_result, indent=2)}")
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: auth, ingest, retrieve, full")
    
    finally:
        # Always close the connection
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
