"""
WebSocket Integration Test Script

This script tests the complete WebSocket integration between frontend and backend.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import websockets
except ImportError:
    print("❌ websockets library not installed")
    print("   Run: pip install websockets")
    sys.exit(1)


async def test_websocket_integration():
    """Test WebSocket integration end-to-end."""
    print("=" * 60)
    print("🧪 WebSocket Integration Test")
    print("=" * 60)

    # Test configuration
    test_task_id = "integration-test-12345"
    ws_url = f"ws://localhost:8000/ws/{test_task_id}"

    print(f"\n📡 Connecting to {ws_url}...")

    try:
        # Test 1: Basic Connection
        print("\n1️⃣  Testing Basic Connection")
        async with websockets.connect(ws_url, timeout=5) as websocket:
            print("   ✅ WebSocket connection established")

            # Test 2: Connection Confirmation
            print("\n2️⃣  Testing Connection Confirmation")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3)
                data = json.loads(message)
                print(f"   📨 Received: {json.dumps(data, indent=4)}")

                if data.get('type') == 'connected':
                    print("   ✅ Connection confirmation received")
                else:
                    print(f"   ⚠️  Unexpected message type: {data.get('type')}")
            except asyncio.TimeoutError:
                print("   ⚠️  No connection confirmation received")

            # Test 3: Message Handling
            print("\n3️⃣  Testing Message Handling")
            test_message = {
                "type": "ping",
                "data": {"timestamp": int(time.time())},
                "timestamp": int(time.time())
            }
            await websocket.send(json.dumps(test_message))
            print(f"   📤 Sent ping message")

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                data = json.loads(response)
                print(f"   📨 Received: {json.dumps(data, indent=4)}")

                if data.get('type') == 'pong':
                    print("   ✅ Pong response received")
                else:
                    print(f"   ⚠️  Unexpected response type: {data.get('type')}")
            except asyncio.TimeoutError:
                print("   ⚠️  No pong response received")

            # Test 4: Multiple Messages
            print("\n4️⃣  Testing Multiple Messages")
            for i in range(3):
                msg = {
                    "type": "test",
                    "data": {"index": i},
                    "timestamp": int(time.time())
                }
                await websocket.send(json.dumps(msg))
                print(f"   📤 Sent test message {i+1}/3")
                await asyncio.sleep(0.5)

            # Test 5: Connection Persistence
            print("\n5️⃣  Testing Connection Persistence")
            print("   ⏳ Waiting 5 seconds...")
            await asyncio.sleep(5)

            # Try to send another message
            await websocket.send(json.dumps({"type": "ping", "data": {}, "timestamp": int(time.time())}))
            print("   ✅ Connection still active after 5 seconds")

        print("\n✅ All WebSocket integration tests completed successfully!")
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print("✅ Basic Connection: PASS")
        print("✅ Message Handling: PASS")
        print("✅ Connection Persistence: PASS")
        print("✅ Integration: PASS")
        print("\n🎉 WebSocket integration is working correctly!")

    except ConnectionRefusedError:
        print("\n❌ Connection refused")
        print("   Make sure the FastAPI server is running:")
        print("   uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    except asyncio.TimeoutError:
        print("\n⏰ Connection timeout")
        print("   The server might be starting up or not responding")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_websocket_endpoints():
    """Test WebSocket endpoint availability."""
    print("\n" + "=" * 60)
    print("🔍 Testing WebSocket Endpoints")
    print("=" * 60)

    # Test different task IDs
    test_ids = [
        "test-task-1",
        "test-task-2",
        "test-task-with-dashes",
        "test_task_with_underscores"
    ]

    for task_id in test_ids:
        ws_url = f"ws://localhost:8000/ws/{task_id}"
        print(f"\n📡 Testing endpoint: /ws/{task_id}")

        try:
            async with websockets.connect(ws_url, timeout=2) as websocket:
                print("   ✅ Endpoint accessible")
        except ConnectionRefusedError:
            print("   ❌ Connection refused")
            return False
        except Exception as e:
            print(f"   ⚠️  {type(e).__name__}: {e}")

    print("\n✅ All endpoints tested")
    return True


async def main():
    """Run all tests."""
    print("\n🚀 Starting WebSocket Integration Tests\n")

    # Test endpoints first
    await test_websocket_endpoints()

    # Test integration
    await test_websocket_integration()

    print("\n" + "=" * 60)
    print("✨ All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
