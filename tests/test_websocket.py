"""Simple WebSocket test script."""

import asyncio
import json
import websockets
import sys


async def test_websocket():
    """Test WebSocket connection."""
    task_id = "test-task-123"
    uri = f"ws://localhost:8000/ws/{task_id}"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully!")

            # Send auth message
            auth_message = {
                "type": "auth",
                "data": {
                    "task_id": task_id
                }
            }
            await websocket.send(json.dumps(auth_message))
            print("✓ Auth message sent")

            # Listen for messages
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(message)
                    print(f"📨 Received: {json.dumps(data, indent=2)}")
                except asyncio.TimeoutError:
                    print("⏱️  No messages received in 30 seconds")
                    break

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_websocket())
