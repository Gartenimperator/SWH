# WiFi and Web Server module for Tentacle Arm Controller
# Raspberry Pi Pico W asyncio-based HTTP server

import network
import time

# MicroPython uses uasyncio, but recent versions also support 'asyncio'
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from config import WIFI_SSID, WIFI_PASSWORD, WEB_PORT


# WiFi connection state
_wlan = None
_ip_address = None


def connect_wifi(ssid=None, password=None, timeout_sec=30):
    """Connect to WiFi network with timeout/retry.

    Args:
        ssid: WiFi network name (default from config)
        password: WiFi password (default from config)
        timeout_sec: Connection timeout in seconds

    Returns:
        IP address string if connected, None otherwise
    """
    global _wlan, _ip_address

    if ssid is None:
        ssid = WIFI_SSID
    if password is None:
        password = WIFI_PASSWORD

    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)

    print(f"Connecting to WiFi: {ssid}")
    _wlan.connect(ssid, password)

    # Wait for connection with timeout
    start = time.time()
    while not _wlan.isconnected():
        if time.time() - start > timeout_sec:
            print("WiFi connection timeout")
            return None
        time.sleep(0.5)
        print(".", end="")

    _ip_address = _wlan.ifconfig()[0]
    print(f"\nConnected! IP: {_ip_address}")
    return _ip_address


def get_wifi_status():
    """Get current WiFi connection status."""
    if _wlan is None:
        return {'connected': False, 'ip': None}
    return {
        'connected': _wlan.isconnected(),
        'ip': _ip_address if _wlan.isconnected() else None
    }


def parse_http_request(data):
    """Parse raw HTTP request data into components.

    Returns:
        Dict with keys: method, path, headers, body
    """
    try:
        text = data.decode('utf-8')
    except:
        return None

    lines = text.split('\r\n')
    if not lines:
        return None

    # Parse request line
    request_line = lines[0].split(' ')
    if len(request_line) < 2:
        return None

    method = request_line[0]
    path = request_line[1]

    # Parse headers
    headers = {}
    body_start = 0
    for i, line in enumerate(lines[1:], 1):
        if line == '':
            body_start = i + 1
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()

    # Get body
    body = '\r\n'.join(lines[body_start:]) if body_start < len(lines) else ''

    return {
        'method': method,
        'path': path,
        'headers': headers,
        'body': body
    }


def build_http_response(status_code, content_type, body):
    """Build HTTP response string.

    Args:
        status_code: HTTP status code (200, 404, etc.)
        content_type: MIME type (text/html, application/json, etc.)
        body: Response body string

    Returns:
        Bytes for response
    """
    status_messages = {
        200: 'OK',
        400: 'Bad Request',
        404: 'Not Found',
        500: 'Internal Server Error'
    }
    status_msg = status_messages.get(status_code, 'Unknown')

    response = f"HTTP/1.1 {status_code} {status_msg}\r\n"
    response += f"Content-Type: {content_type}\r\n"
    response += f"Content-Length: {len(body)}\r\n"
    response += "Connection: close\r\n"
    response += "Access-Control-Allow-Origin: *\r\n"
    response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
    response += "Access-Control-Allow-Headers: Content-Type\r\n"
    response += "\r\n"
    response += body

    return response.encode('utf-8')


async def handle_client(reader, writer):
    """Handle incoming HTTP client connection.

    Routes requests to handlers defined in routes module.
    """
    try:
        # Read request with timeout
        data = await asyncio.wait_for(reader.read(2048), timeout=5.0)
        if not data:
            return

        request = parse_http_request(data)
        if request is None:
            response = build_http_response(400, 'text/plain', 'Bad Request')
            writer.write(response)
            await writer.drain()
            return

        # Handle CORS preflight
        if request['method'] == 'OPTIONS':
            response = build_http_response(200, 'text/plain', '')
            writer.write(response)
            await writer.drain()
            return

        # Import routes here to avoid circular imports
        from routes import route_request

        status, content_type, body = route_request(request)
        response = build_http_response(status, content_type, body)
        writer.write(response)
        await writer.drain()

    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_server(host='0.0.0.0', port=None):
    """Start the HTTP server.

    Args:
        host: Bind address (default 0.0.0.0 for all interfaces)
        port: Server port (default from config)

    Returns:
        Server object
    """
    if port is None:
        port = WEB_PORT

    server = await asyncio.start_server(handle_client, host, port)
    print(f"HTTP server running on {host}:{port}")
    return server
