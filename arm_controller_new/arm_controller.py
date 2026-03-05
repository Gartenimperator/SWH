try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from motors import move_multiple_steppers, move_stepper
from coordinate_controller import get_controller
from config import (DEFAULT_SPEED_US, ELEVATION_STEP_UNITS, ROTATION_STEP_DEGREES,
                    CLOCKWISE, COUNTERCLOCKWISE, GAMEPAD_MANUAL_STEPS,
                    JOYSTICK_SAMPLE_DELAY)

# LED mode shown when each motor is selected
MOTOR_LED_MODES = {
    'x': 'red',
    'y': 'green',
    'z': 'blue',
}


class ArmController:
    def __init__(self, bus, led):
        self._bus = bus
        self._led = led
        self._coord = get_controller()
        self.debug = False
        self._nx = 0.0  # current joystick state, updated by events
        self._ny = 0.0

    async def run(self):
        asyncio.create_task(self._move_loop())
        while True:
            event, data = await self._bus.listen()
            print(event, data)

            if event == 'joystick':
                self._on_joystick(data)
            elif event == 'home':
                self._on_home()
            elif event == 'debug_toggle':
                self._on_debug_toggle()
            elif event == 'motor_select' and self.debug:
                self._on_motor_select(data)
            elif event == 'motor_pull' and self.debug:
                self._on_motor_pull(data)
            elif event == 'motor_release' and self.debug:
                self._on_motor_release(data)

    async def _move_loop(self):
        """Continuously move the arm as long as the joystick is deflected."""
        while True:
            if self._nx != 0:
                self._execute_deltas(self._coord.tilt(int(self._nx * ELEVATION_STEP_UNITS)))
            if self._ny != 0:
                self._execute_deltas(self._coord.rotate(int(-self._ny * ROTATION_STEP_DEGREES)))
            await asyncio.sleep(JOYSTICK_SAMPLE_DELAY)

    # ------------------------------------------------------------------

    def _on_joystick(self, data):
        self._nx = data['nx']
        self._ny = data['ny']

    def _on_debug_toggle(self):
        self.debug = not self.debug
        if self.debug:
            self._led.set_mode('yellow')
            print("[Arm] Debug mode ON")
        else:
            self._led.set_mode('off')
            print("[Arm] Debug mode OFF")

    def _on_home(self):
        if self.debug:
            self._coord.set_center()
            print("[Arm] Center set to current position")
        else:
            self._execute_deltas(self._coord.home())
            print("[Arm] Homing")

    def _on_motor_select(self, data):
        motor = data['motor']
        self._led.set_mode(MOTOR_LED_MODES.get(motor, 'white'))
        print(f"[Arm] Motor {motor} selected")

    def _on_motor_pull(self, data):
        move_stepper(data['motor'], CLOCKWISE, DEFAULT_SPEED_US, GAMEPAD_MANUAL_STEPS)

    def _on_motor_release(self, data):
        move_stepper(data['motor'], COUNTERCLOCKWISE, DEFAULT_SPEED_US, GAMEPAD_MANUAL_STEPS)

    def _execute_deltas(self, deltas):
        motor_args = [
            {'id': m, 'direction': 1 if d > 0 else 0, 'steps': abs(d)}
            for m, d in deltas.items() if d != 0
        ]
        if motor_args:
            move_multiple_steppers(motor_args, speed_us=DEFAULT_SPEED_US)
