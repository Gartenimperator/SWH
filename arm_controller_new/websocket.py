# WebSocket Protocol Implementation (RFC 6455)
# Pure protocol layer — no application logic

import hashlib
import struct

try:
    import ubinascii as binascii
except ImportError:
    import binascii

# WebSocket opcodes
OP_CONT = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

_WS_MAGIC = b"258EAFA5-E914-47DA-95CA-5AB9DC85B711"


def build_handshake_response(ws_key):
    """Build HTTP 101 Switching Protocols response for WebSocket upgrade.

    Args:
        ws_key: Value of Sec-WebSocket-Key header

    Returns:
        Bytes of the complete HTTP response
    """
    accept = hashlib.sha1(ws_key.encode() + _WS_MAGIC).digest()
    accept_b64 = binascii.b2a_base64(accept).strip().decode()

    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_b64}\r\n"
        "\r\n"
    )
    return response.encode()


async def read_frame(reader):
    """Read one WebSocket frame from the stream.

    Args:
        reader: asyncio StreamReader

    Returns:
        Tuple of (opcode, payload_bytes) or (None, None) on connection close
    """
    # Read first 2 bytes: FIN/opcode + mask/length
    header = await reader.readexactly(2)
    if len(header) < 2:
        return None, None

    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F

    # Extended payload length
    if length == 126:
        raw = await reader.readexactly(2)
        length = struct.unpack("!H", raw)[0]
    elif length == 127:
        raw = await reader.readexactly(8)
        length = struct.unpack("!Q", raw)[0]

    # Read mask key (client frames are always masked)
    mask_key = None
    if masked:
        mask_key = await reader.readexactly(4)

    # Read payload
    payload = await reader.readexactly(length) if length > 0 else b""

    # Unmask payload
    if masked and mask_key and length > 0:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

    return opcode, payload


def build_text_frame(text):
    """Build a WebSocket text frame (server → client, unmasked).

    Args:
        text: String to send

    Returns:
        Bytes of the complete frame
    """
    payload = text.encode()
    return _build_frame(OP_TEXT, payload)


def build_close_frame(code=1000):
    """Build a WebSocket close frame.

    Args:
        code: Close status code (default 1000 = normal)

    Returns:
        Bytes of the complete frame
    """
    payload = struct.pack("!H", code)
    return _build_frame(OP_CLOSE, payload)


def build_pong_frame(data):
    """Build a WebSocket pong frame (response to ping).

    Args:
        data: Ping payload to echo back

    Returns:
        Bytes of the complete frame
    """
    return _build_frame(OP_PONG, data)


def _build_frame(opcode, payload):
    """Build a WebSocket frame (server-side, unmasked).

    Args:
        opcode: Frame opcode
        payload: Frame payload bytes

    Returns:
        Bytes of the complete frame
    """
    length = len(payload)
    header = bytes([0x80 | opcode])  # FIN + opcode

    if length < 126:
        header += bytes([length])
    elif length < 65536:
        header += bytes([126]) + struct.pack("!H", length)
    else:
        header += bytes([127]) + struct.pack("!Q", length)

    return header + payload
