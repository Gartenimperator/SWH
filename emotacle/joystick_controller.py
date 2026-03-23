"""MicroPython joystick reader (async)

Reads joystick X/Y values and switch state as an asyncio task.

Defaults target Raspberry Pi Pico (ADC pins 26/27/28). Adjust pins
at the top if using a different board.
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import time
from machine import ADC, Pin
from config import (JOYSTICK_X_PIN, JOYSTICK_Y_PIN, JOYSTICK_SW_PIN,
                    JOYSTICK_SAMPLE_DELAY, JOYSTICK_CENTER, JOYSTICK_DEADZONE)

DOUBLE_CLICK_WINDOW_MS = 400


class Joystick:
    def __init__(self, bus):
        self._bus = bus
        self.adc_x = ADC(JOYSTICK_X_PIN)
        self.adc_y = ADC(JOYSTICK_Y_PIN)
        self.sw = Pin(JOYSTICK_SW_PIN, Pin.IN, Pin.PULL_UP)
        self.x = 0
        self.y = 0
        self.pressed = False
        self._prev_pressed = False
        self._click_count = 0
        self._last_click_ms = 0

    def _read_adc(self, adc):
        """Read an ADC and return a 0..1023 integer."""
        try:
            v = adc.read_u16()
        except AttributeError:
            v = adc.read()
        if v > 4095:
            return int(v * 1023 // 65535)
        return int(v)

    def _normalize(self, raw):
        """Snap axis to 0 / +1 / -1 with a centre dead zone."""
        dev = raw - JOYSTICK_CENTER
        if abs(dev) < JOYSTICK_DEADZONE:
            return 0.0
        return 1.0 if dev > 0 else -1.0

    @property
    def nx(self):
        return self._normalize(self.x)

    @property
    def ny(self):
        return self._normalize(self.y)

    async def run(self):
        prev_nx, prev_ny = 0.0, 0.0
        while True:
            self.x = self._read_adc(self.adc_x)
            self.y = self._read_adc(self.adc_y)
            self.pressed = self.sw.value() == 0
            nx, ny = self.nx, self.ny
            if nx != prev_nx or ny != prev_ny:
                self._bus.emit('joystick', {'nx': nx, 'ny': ny})
                prev_nx, prev_ny = nx, ny

            now = time.ticks_ms()

            # Detect rising edge (button just pressed)
            if self.pressed and not self._prev_pressed:
                if self._click_count == 1 and time.ticks_diff(now, self._last_click_ms) < DOUBLE_CLICK_WINDOW_MS:
                    self._bus.emit('light_mode_next', {})
                    self._click_count = 0
                else:
                    self._click_count = 1
                    self._last_click_ms = now

            # Single click timeout: emit home if window has passed with one click
            if self._click_count == 1 and time.ticks_diff(now, self._last_click_ms) >= DOUBLE_CLICK_WINDOW_MS:
                self._bus.emit('home', {})
                self._click_count = 0

            self._prev_pressed = self.pressed
            await asyncio.sleep(JOYSTICK_SAMPLE_DELAY)
