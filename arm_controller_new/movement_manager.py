# Movement Manager for Continuous Motion
# Owns all continuous movement state as a singleton

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import time
import json
from motors import get_motor, move_multiple_steppers
from coordinate_controller import get_controller
from config import (
    CONTINUOUS_ROTATE_INCREMENT, CONTINUOUS_TILT_INCREMENT,
    POSITION_UPDATE_INTERVAL_MS, DEFAULT_SPEED_US, INTERLACE_STEP_SIZE
)


class MovementManager:
    """Manages continuous movement state machine.

    States: idle -> moving -> stopping -> idle
    """

    def __init__(self):
        self._state = "idle"
        self._stop_flag = False
        self._task = None
        self._action = None
        self._direction = None
        self._speed_us = DEFAULT_SPEED_US
        self._send_fn = None

    @property
    def state(self):
        return self._state

    def start(self, action, direction, speed_us, send_fn):
        """Start continuous movement.

        Args:
            action: "rotate" or "tilt"
            direction: 1 or -1
            speed_us: Motor pulse delay in microseconds
            send_fn: Async callable to send messages to client

        Returns:
            True if started, False if already moving
        """
        if self._state != "idle":
            return False

        self._action = action
        self._direction = direction
        self._speed_us = speed_us
        self._send_fn = send_fn
        self._stop_flag = False
        self._state = "moving"
        self._task = asyncio.create_task(self._movement_loop())
        return True

    async def stop(self):
        """Signal the movement loop to stop and wait for it to finish."""
        if self._state == "idle":
            return

        self._stop_flag = True
        self._state = "stopping"

        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass
            self._task = None

        self._state = "idle"

    async def home(self, speed_us, send_fn):
        """Move arm to center position (0, 0).

        Args:
            speed_us: Motor pulse delay in microseconds
            send_fn: Async callable to send messages to client

        Returns:
            True if homing started and completed, False if busy
        """
        if self._state != "idle":
            return False

        self._state = "moving"
        self._speed_us = speed_us
        self._send_fn = send_fn
        self._stop_flag = False

        try:
            controller = get_controller()
            deltas = controller.home()

            # Build motor args from deltas
            motor_args = []
            for motor_id, steps in deltas.items():
                if steps != 0:
                    motor_args.append({
                        "id": motor_id,
                        "direction": 1 if steps > 0 else 0,
                        "steps": abs(steps)
                    })

            if motor_args:
                await self._step_with_yield(motor_args)

            pos = controller.get_position()
            await send_fn(json.dumps({
                "type": "homed",
                "azimuth": pos["azimuth"],
                "elevation": pos["elevation"]
            }))
        except Exception as e:
            print(f"Home error: {e}")
        finally:
            self._state = "idle"
            self._send_fn = None

        return True

    def get_state(self):
        """Return current state and position."""
        controller = get_controller()
        pos = controller.get_position()
        return {
            "type": "state",
            "state": self._state,
            "azimuth": pos["azimuth"],
            "elevation": pos["elevation"]
        }

    async def _movement_loop(self):
        """Core async loop: step motors in small batches, yield between."""
        controller = get_controller()
        send = self._send_fn
        last_update = time.ticks_ms()

        # Notify client that movement started
        await send(json.dumps({
            "type": "started",
            "action": self._action,
            "direction": self._direction
        }))

        try:
            while not self._stop_flag:
                # Compute increment
                if self._action == "rotate":
                    delta = CONTINUOUS_ROTATE_INCREMENT * self._direction
                    deltas = controller.rotate(delta)
                else:  # tilt
                    delta = CONTINUOUS_TILT_INCREMENT * self._direction
                    deltas = controller.tilt(delta)

                # Build motor args from deltas
                motor_args = []
                for motor_id, steps in deltas.items():
                    if steps != 0:
                        motor_args.append({
                            "id": motor_id,
                            "direction": 1 if steps > 0 else 0,
                            "steps": abs(steps)
                        })

                # Execute movement in interlaced batches, yielding between
                if motor_args:
                    await self._step_with_yield(motor_args)

                # Send position update at configured interval
                now = time.ticks_ms()
                if time.ticks_diff(now, last_update) >= POSITION_UPDATE_INTERVAL_MS:
                    pos = controller.get_position()
                    await send(json.dumps({
                        "type": "position",
                        "azimuth": pos["azimuth"],
                        "elevation": pos["elevation"]
                    }))
                    last_update = now

                # Yield to event loop
                await asyncio.sleep_ms(0)

        finally:
            # Send final position
            pos = controller.get_position()
            if send is not None:
                try:
                    await send(json.dumps({
                        "type": "stopped",
                        "azimuth": pos["azimuth"],
                        "elevation": pos["elevation"]
                    }))
                except Exception:
                    pass

            self._send_fn = None

    async def _step_with_yield(self, motor_args):
        """Step motors in batches of INTERLACE_STEP_SIZE, yielding between.

        This keeps the blocking window to ~20ms max per batch instead of
        blocking for the entire movement.
        """
        # Resolve motors and set directions
        motors_to_move = []
        for arg in motor_args:
            motor = get_motor(arg["id"])
            if motor is None:
                continue
            motor.set_direction(arg["direction"])
            motors_to_move.append({
                "motor": motor,
                "remaining": arg["steps"]
            })

        if not motors_to_move:
            return

        # Step in batches
        while any(m["remaining"] > 0 for m in motors_to_move):
            if self._stop_flag:
                return

            for m in motors_to_move:
                if m["remaining"] > 0:
                    batch = min(INTERLACE_STEP_SIZE, m["remaining"])
                    for _ in range(batch):
                        m["motor"].pulse(self._speed_us)
                    m["remaining"] -= batch

            # Yield between batches
            await asyncio.sleep_ms(0)


# Global singleton
_manager = None


def get_manager():
    """Get or create the global MovementManager instance."""
    global _manager
    if _manager is None:
        _manager = MovementManager()
    return _manager
