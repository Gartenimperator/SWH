from machine import Pin, I2C
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from config import (GAMEPAD_SDA_PIN, GAMEPAD_SCL_PIN, GAMEPAD_ADDRESS, GAMEPAD_POLL_DELAY)


class Gamepad:
    # Map face buttons to motor aliases (x/y/z → motor1/motor2/motor3)
    MOTOR_BUTTONS = {
        'CROSS':  'x',
        'SQUARE': 'y',
        'CIRCLE': 'z',
    }

    def __init__(self, bus, sda_pin=GAMEPAD_SDA_PIN, scl_pin=GAMEPAD_SCL_PIN, address=GAMEPAD_ADDRESS):
        self._bus = bus
        self.i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=10000)
        self.address = address
        self.selected_motor = None

        self.button_map = {
            3:  "LEFT",
            1:  "RIGHT",
            2:  "UP",
            13: "DOWN",
            9:  "SQUARE",
            10: "CIRCLE",
            8:  "TRIANGLE",
            11: "CROSS",
            5:  "POWER",
            6:  "BERRY",
            7:  "BUG",
            16: "HOME",
            14: "LEFTCHAR",
            15: "MINUS",
            4:  "PLUS",
            12: "RIGHTCHAR",
        }

    def get_single_pressed(self):
        """Returns the button name ONLY if exactly ONE button is pressed."""
        try:
            data = self.i2c.readfrom(self.address, 2)
            keys_val = (data[1] << 8) | data[0]
            if keys_val == 0:
                return None
            if (keys_val & (keys_val - 1)) != 0:
                return None
            for i in range(16):
                if keys_val & (1 << i):
                    raw_num = i + 1
                    return self.button_map.get(raw_num, f"Key_{raw_num}")
        except OSError:
            return None

    async def run(self):
        while True:
            button = self.get_single_pressed()

            if button in self.MOTOR_BUTTONS:
                self.selected_motor = self.MOTOR_BUTTONS[button]
                self._bus.emit('motor_select', {'motor': self.selected_motor})

            elif button == 'UP' and self.selected_motor:
                self._bus.emit('motor_release', {'motor': self.selected_motor})

            elif button == 'DOWN' and self.selected_motor:
                self._bus.emit('motor_pull', {'motor': self.selected_motor})

            elif button == 'HOME':
                self._bus.emit('home', {})

            elif button == 'POWER':
                self._bus.emit('debug_toggle', {})

            await asyncio.sleep(GAMEPAD_POLL_DELAY)
