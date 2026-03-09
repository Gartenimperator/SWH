try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import Pin
from motors import move_multiple_steppers, move_stepper
from coordinate_controller import get_controller
from config import (DEFAULT_SPEED_US, ELEVATION_STEP_UNITS, ROTATION_STEP_DEGREES,
                    CLOCKWISE, COUNTERCLOCKWISE, GAMEPAD_MANUAL_STEPS,
                    JOYSTICK_SAMPLE_DELAY, TENSION_BUTTON_PINS, CALIBRATION_PULL_STEPS,
                    RETENSION_INTERVAL)

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
        self._retension_counter = 0
        # Tension buttons: pressed (LOW with pull-up) = string is under tension
        self._tension_buttons = {
            motor: Pin(pin, Pin.IN, Pin.PULL_UP)
            for motor, pin in TENSION_BUTTON_PINS.items()
        }

    async def run(self):
        asyncio.create_task(self._move_loop())
        while True:
            event, data = await self._bus.listen()
            print(event, data)

            if event == 'joystick':
                self._on_joystick(data)
            elif event == 'home':
                await self._on_home()
            elif event == 'debug_toggle':
                self._on_debug_toggle()
            elif event == 'motor_select' and self.debug:
                self._on_motor_select(data)
            elif event == 'motor_pull' and self.debug:
                await self._on_motor_pull(data)
            elif event == 'motor_release' and self.debug:
                await self._on_motor_release(data)
            elif event == 'light_mode_next':
                self._led.next_mode()

    async def _move_loop(self):
        """Continuously move the arm as long as the joystick is deflected."""
        while True:
            if self._nx != 0:
                await self._execute_deltas(self._coord.tilt(int(self._nx * ELEVATION_STEP_UNITS)))
            if self._ny != 0:
                await self._execute_deltas(self._coord.rotate(int(-self._ny * ROTATION_STEP_DEGREES)))
            self._retension_counter += 1
            if self._retension_counter >= RETENSION_INTERVAL:
                await self._retension()
                self._retension_counter = 0
            await asyncio.sleep(JOYSTICK_SAMPLE_DELAY)

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

    async def _on_home(self):
        if self.debug:
            self._coord.set_center()
            print("[Arm] Center set to current position")
        else:
            await self._execute_deltas(self._coord.home())
            print("[Arm] Homing")
            await self._retension()
            self._coord.set_center()
            print("[Arm] Recalibrated after home")

    def _on_motor_select(self, data):
        motor = data['motor']
        self._led.set_mode(MOTOR_LED_MODES.get(motor, 'white'))
        print(f"[Arm] Motor {motor} selected")

    async def _on_motor_pull(self, data):
        await move_stepper(data['motor'], CLOCKWISE, DEFAULT_SPEED_US, GAMEPAD_MANUAL_STEPS)

    async def _on_motor_release(self, data):
        await move_stepper(data['motor'], COUNTERCLOCKWISE, DEFAULT_SPEED_US, GAMEPAD_MANUAL_STEPS)

    async def _retension(self):
        slack = True
        while slack:
            slack = [m for m in ['x', 'y', 'z'] if not self._is_under_tension(m)]
            if not slack:
                break
            await move_multiple_steppers(
                [{'id': m, 'direction': CLOCKWISE, 'steps': CALIBRATION_PULL_STEPS} for m in slack],
                speed_us=DEFAULT_SPEED_US,
            )
            for m in slack:
                self._coord._motor_positions[m] -= CALIBRATION_PULL_STEPS
            await asyncio.sleep(0.010)  # let button state settle

    async def calibrate(self):
        """Pull each string until all tension buttons are pressed, then reset origin.

        Called at startup. Does nothing if all strings are already tensioned.
        """
        if all(self._is_under_tension(m) for m in ['x', 'y', 'z']):
            print("[Arm] All strings tensioned — skipping calibration.")
            return

        print("[Arm] Calibrating — pulling slack strings...")
        await self._retension()
        # This tensioned position is the physical center — reset origin
        self._coord.set_center()
        print("[Arm] Calibration complete.")

    def _is_under_tension(self, motor):
        """Return True if the tension button for this motor is pressed (string is taut)."""
        btn = self._tension_buttons.get(motor)
        if btn is None:
            return True  # no button configured — assume tension
        return btn.value() == 0  # pull-up: pressed = LOW

    async def _execute_deltas(self, deltas):
        motor_args = []
        skipped = {}
        for m, d in deltas.items():
            if d == 0:
                continue
            direction = 1 if d > 0 else 0
            # Only release (COUNTERCLOCKWISE) if the string is currently under tension.
            # If the button is not pressed the string already has slack — skip the release.
            if direction == COUNTERCLOCKWISE and not self._is_under_tension(m):
                skipped[m] = d
                continue
            motor_args.append({'id': m, 'direction': direction, 'steps': abs(d)})

        # Undo the coord controller's position update for skipped releases so
        # internal state stays consistent with what actually moved.
        for m, d in skipped.items():
            self._coord._motor_positions[m] -= d

        if motor_args:
            await move_multiple_steppers(motor_args, speed_us=DEFAULT_SPEED_US)
