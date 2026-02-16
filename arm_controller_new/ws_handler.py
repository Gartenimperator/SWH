# WebSocket Application Handler
# Bridges WebSocket frames <-> MovementManager

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import json
from websocket import (
    read_frame, build_text_frame, build_close_frame, build_pong_frame,
    OP_TEXT, OP_CLOSE, OP_PING, OP_BINARY
)
from movement_manager import get_manager
from config import DEFAULT_SPEED_US

# Single-connection guard
_active_connection = False


async def handle_websocket_connection(reader, writer):
    """Main WebSocket connection handler.

    Reads frames, dispatches commands to MovementManager.
    Safety: finally block always stops the arm on disconnect.

    Args:
        reader: asyncio StreamReader (after handshake)
        writer: asyncio StreamWriter (after handshake)
    """
    global _active_connection

    # Reject second connection
    if _active_connection:
        writer.write(build_close_frame(1013))  # Try Again Later
        await writer.drain()
        return

    _active_connection = True
    manager = get_manager()

    async def send_msg(text):
        """Send a text message to the client."""
        writer.write(build_text_frame(text))
        await writer.drain()

    try:
        # Send initial state
        await send_msg(json.dumps(manager.get_state()))

        # Frame read loop
        while True:
            opcode, payload = await read_frame(reader)

            if opcode is None or opcode == OP_CLOSE:
                break

            if opcode == OP_PING:
                writer.write(build_pong_frame(payload))
                await writer.drain()
                continue

            if opcode == OP_TEXT:
                await _dispatch_command(payload.decode(), manager, send_msg)

    except (asyncio.CancelledError, Exception) as e:
        print(f"WebSocket error: {e}")

    finally:
        # Safety: always stop arm on disconnect
        await manager.stop()
        _active_connection = False
        print("WebSocket connection closed")


async def _dispatch_command(raw, manager, send_fn):
    """Parse and dispatch a client command.

    Args:
        raw: Raw JSON string from client
        manager: MovementManager instance
        send_fn: Async callable to send response
    """
    try:
        msg = json.loads(raw)
    except ValueError:
        await send_fn(json.dumps({"type": "error", "message": "Invalid JSON"}))
        return

    cmd = msg.get("cmd")

    if cmd == "start":
        action = msg.get("action")
        direction = msg.get("direction", 1)
        speed = msg.get("speed", DEFAULT_SPEED_US)

        if action not in ("rotate", "tilt"):
            await send_fn(json.dumps({
                "type": "error",
                "message": "action must be 'rotate' or 'tilt'"
            }))
            return

        if direction not in (1, -1):
            await send_fn(json.dumps({
                "type": "error",
                "message": "direction must be 1 or -1"
            }))
            return

        ok = manager.start(action, direction, int(speed), send_fn)
        if not ok:
            await send_fn(json.dumps({
                "type": "error",
                "message": "Already moving — send stop first"
            }))

    elif cmd == "stop":
        await manager.stop()

    elif cmd == "home":
        speed = msg.get("speed", DEFAULT_SPEED_US)
        ok = await manager.home(int(speed), send_fn)
        if not ok:
            await send_fn(json.dumps({
                "type": "error",
                "message": "Cannot home — currently moving"
            }))

    elif cmd == "state":
        await send_fn(json.dumps(manager.get_state()))

    else:
        await send_fn(json.dumps({
            "type": "error",
            "message": f"Unknown command: {cmd}"
        }))
