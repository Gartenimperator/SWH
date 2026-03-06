# Main entry point for Tentacle Arm Controller
# Raspberry Pi Pico W - physical joystick + gamepad control

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from motors import init_motors
from event_bus import EventBus
from arm_controller import ArmController
from led_controller import LEDController
from joystick_controller import Joystick
from touchpad_controller import Gamepad


async def main():
    print("Initializing motors...")
    init_motors()
    print("Motors initialized.")

    bus = EventBus()
    led = LEDController()

    asyncio.create_task(led.run())
    asyncio.create_task(Joystick(bus).run())
    asyncio.create_task(Gamepad(bus).run())

    arm = ArmController(bus, led)
    arm.calibrate()
    asyncio.create_task(arm.run())

    print("Tentacle Arm Controller ready.")
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
