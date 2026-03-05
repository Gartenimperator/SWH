# LED Controller for RGB LED (pins from config)
# Supports multiple visual modes, cycled via next_mode() (button hookup TBD)

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from machine import Pin, PWM
from config import LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN


# (name, display_label)
MODES = [
    "off",
    "red",
    "green",
    "blue",
    "white",
    "cyan",
    "magenta",
    "yellow",
    "blink_red",
    "blink_green",
    "blink_blue",
    "blink_white",
    "police",
    "rainbow",
    "breathing_white",
    "breathing_red",
    "candle",
]


class LEDController:
    """
    Async RGB LED controller with switchable modes.

    Call next_mode() to advance to the next mode (wire to a button later).
    Call run() as an asyncio task to keep the LED animating.
    """

    def __init__(self, pin_red=LED_RED_PIN, pin_green=LED_GREEN_PIN, pin_blue=LED_BLUE_PIN):
        # PWM on each colour channel for smooth brightness control
        self._r = PWM(Pin(pin_red))
        self._g = PWM(Pin(pin_green))
        self._b = PWM(Pin(pin_blue))

        for ch in (self._r, self._g, self._b):
            ch.freq(1000)

        self._mode_idx = 0
        self._running = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def current_mode(self):
        return MODES[self._mode_idx]

    def next_mode(self):
        """Advance to the next mode. Wire this to a button interrupt."""
        self._mode_idx = (self._mode_idx + 1) % len(MODES)
        print(f"[LED] Mode → {self.current_mode}")

    def set_mode(self, name):
        """Switch to a named mode."""
        if name in MODES:
            self._mode_idx = MODES.index(name)
            print(f"[LED] Mode → {name}")

    def stop(self):
        self._running = False
        self._set(0, 0, 0)

    async def run(self):
        """Main loop – call once as an asyncio task."""
        self._running = True
        print(f"[LED] Starting in mode: {self.current_mode}")
        while self._running:
            await self._dispatch(self._mode_idx)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set(self, r, g, b):
        """Set RGB (0–255 each)."""
        self._r.duty_u16(int(r / 255 * 65535))
        self._g.duty_u16(int(g / 255 * 65535))
        self._b.duty_u16(int(b / 255 * 65535))

    def _mode_changed(self, snap):
        """True if mode was switched externally since snap was taken."""
        return self._mode_idx != snap

    async def _dispatch(self, snap):
        """Run one cycle of whatever mode snap points to."""
        mode = MODES[snap]

        # --- Solid colours ---
        if mode == "off":
            self._set(0, 0, 0)
            await asyncio.sleep(0.2)

        elif mode == "red":
            self._set(255, 0, 0)
            await asyncio.sleep(0.2)

        elif mode == "green":
            self._set(0, 255, 0)
            await asyncio.sleep(0.2)

        elif mode == "blue":
            self._set(0, 0, 255)
            await asyncio.sleep(0.2)

        elif mode == "white":
            self._set(255, 255, 255)
            await asyncio.sleep(0.2)

        elif mode == "cyan":
            self._set(0, 255, 255)
            await asyncio.sleep(0.2)

        elif mode == "magenta":
            self._set(255, 0, 255)
            await asyncio.sleep(0.2)

        elif mode == "yellow":
            self._set(255, 180, 0)
            await asyncio.sleep(0.2)

        # --- Blink modes ---
        elif mode == "blink_red":
            self._set(255, 0, 0)
            await asyncio.sleep(0.4)
            self._set(0, 0, 0)
            await asyncio.sleep(0.4)

        elif mode == "blink_green":
            self._set(0, 255, 0)
            await asyncio.sleep(0.4)
            self._set(0, 0, 0)
            await asyncio.sleep(0.4)

        elif mode == "blink_blue":
            self._set(0, 0, 255)
            await asyncio.sleep(0.4)
            self._set(0, 0, 0)
            await asyncio.sleep(0.4)

        elif mode == "blink_white":
            self._set(255, 255, 255)
            await asyncio.sleep(0.4)
            self._set(0, 0, 0)
            await asyncio.sleep(0.4)

        # --- Police strobe ---
        elif mode == "police":
            for _ in range(2):
                self._set(255, 0, 0)
                await asyncio.sleep(0.12)
                self._set(0, 0, 0)
                await asyncio.sleep(0.08)
                if self._mode_changed(snap):
                    return
            for _ in range(2):
                self._set(0, 0, 255)
                await asyncio.sleep(0.12)
                self._set(0, 0, 0)
                await asyncio.sleep(0.08)
                if self._mode_changed(snap):
                    return
            await asyncio.sleep(0.1)

        # --- Rainbow ---
        elif mode == "rainbow":
            steps = 60
            for i in range(steps):
                if self._mode_changed(snap):
                    return
                t = i / steps
                if t < 1 / 3:
                    r = int(255 * (1 - t * 3))
                    g = int(255 * (t * 3))
                    b = 0
                elif t < 2 / 3:
                    t2 = (t - 1 / 3) * 3
                    r = 0
                    g = int(255 * (1 - t2))
                    b = int(255 * t2)
                else:
                    t3 = (t - 2 / 3) * 3
                    r = int(255 * t3)
                    g = 0
                    b = int(255 * (1 - t3))
                self._set(r, g, b)
                await asyncio.sleep(0.05)

        # --- Breathing white ---
        elif mode == "breathing_white":
            await self._breathe(255, 255, 255, snap)

        # --- Breathing red ---
        elif mode == "breathing_red":
            await self._breathe(255, 20, 0, snap)

        # --- Candle flicker ---
        elif mode == "candle":
            await self._candle(snap)

    async def _breathe(self, r, g, b, snap, steps=60):
        """Fade in then out on the given colour."""
        for i in range(steps):
            if self._mode_changed(snap):
                return
            br = i / steps
            self._set(int(r * br), int(g * br), int(b * br))
            await asyncio.sleep(0.02)
        for i in range(steps, 0, -1):
            if self._mode_changed(snap):
                return
            br = i / steps
            self._set(int(r * br), int(g * br), int(b * br))
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.3)

    async def _candle(self, snap):
        """Warm flicker simulated with pseudo-random brightness steps."""
        import urandom  # MicroPython built-in
        base_r, base_g, base_b = 255, 80, 10
        for _ in range(20):
            if self._mode_changed(snap):
                return
            flicker = (urandom.getrandbits(6) + 180) / 255  # 0.70 – 1.0
            self._set(
                int(base_r * flicker),
                int(base_g * flicker),
                int(base_b * flicker),
            )
            delay_ms = 40 + urandom.getrandbits(5)  # 40–71 ms
            await asyncio.sleep(delay_ms / 1000)
