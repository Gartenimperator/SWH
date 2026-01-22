# Main entry point for Tentacle Arm Controller
# Raspberry Pi Pico W - WiFi stepper motor control

# MicroPython uses uasyncio, but recent versions also support 'asyncio'
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from motors import init_motors
from webserver import connect_wifi, start_server
from config import WIFI_SSID, WIFI_PASSWORD


async def main():
    """Main entry point - connect WiFi, init motors, start server."""

    # Initialize motor pins
    print("Initializing motors...")
    init_motors()
    print("Motors initialized.")

    # Connect to WiFi
    print("Connecting to WiFi...")
    ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    if ip is None:
        print("Failed to connect to WiFi. Check credentials in config.py")
        print(f"  SSID: {WIFI_SSID}")
        return

    # Start HTTP server
    print("Starting web server...")
    server = await start_server()

    print("=" * 40)
    print(f"Tentacle Arm Controller Ready!")
    print(f"Open http://{ip}/ in your browser")
    print("=" * 40)

    # Run forever
    while True:
        await asyncio.sleep(3600)


# Run the main coroutine
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
