import asyncio
import json
import websockets

async def test_discovery():
    """Test the MCP discovery endpoint."""
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Send a discovery request
        discovery_request = {
            "type": "discover",
            "request_id": "discover-1"
        }
        
        print(f"Sending discovery request: {json.dumps(discovery_request)}")
        await websocket.send(json.dumps(discovery_request))
        
        # Receive the response
        response = await websocket.recv()
        response_data = json.loads(response)
        
        print(f"Received discovery response: {json.dumps(response_data, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_discovery())
