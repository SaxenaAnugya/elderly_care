"""Test script to verify WebSocket connection works."""
import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection to the server."""
    uri = "ws://localhost:8000/ws/test"
    
    try:
        print(f"Connecting to {uri}...")
        # Add origin header for testing
        async with websockets.connect(
            uri,
            extra_headers={"Origin": "http://localhost:3000"}
        ) as websocket:
            print("✓ Connected successfully!")
            
            # Wait for initial message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✓ Received: {data}")
            
            # Send a test message
            await websocket.send("Hello from test script!")
            
            # Wait for echo
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Echo received: {data}")
            
            print("✓ WebSocket test passed!")
            return True
            
    except ConnectionRefusedError:
        print("✗ Connection refused - server is not running!")
        print("  Start the server with: python backend/api_server.py")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing WebSocket connection...")
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)

