# Motor control module for Tentacle Arm Controller
# Raspberry Pi Pico W with A4988/DRV8825 drivers

from machine import Pin
import time
from config import MOTORS, MOTOR_ALIASES, DEFAULT_SPEED_US, INTERLACE_STEP_SIZE


class StepperMotor:
    """Wrapper for stepper motor control via step/dir pins."""

    def __init__(self, name, step_pin, dir_pin):
        self.name = name
        self.step = Pin(step_pin, Pin.OUT)
        self.dir = Pin(dir_pin, Pin.OUT)
        self.step.value(0)
        self.dir.value(0)

    def set_direction(self, direction):
        """Set motor direction (1 = clockwise, 0 = counterclockwise)."""
        self.dir.value(direction)

    def pulse(self, delay_us):
        """Generate one step pulse with given delay."""
        self.step.value(1)
        time.sleep_us(delay_us)
        self.step.value(0)
        time.sleep_us(delay_us)


# Global motor instances
_motors = {}


def init_motors():
    """Initialize all motor instances from config."""
    global _motors
    for name, pins in MOTORS.items():
        _motors[name] = StepperMotor(name, pins['step'], pins['dir'])
    return _motors


def get_motor(motor_id):
    """Get motor by name or alias (x, y, z -> motor1, motor2, motor3)."""
    motor_id = str(motor_id).lower()
    if motor_id in MOTOR_ALIASES:
        motor_id = MOTOR_ALIASES[motor_id]
    return _motors.get(motor_id)


def move_stepper(motor_id, direction, speed_us, steps):
    """Move a single stepper motor.

    Args:
        motor_id: Motor name or alias ('x', 'y', 'z' or 'motor1', 'motor2', 'motor3')
        direction: 1 for clockwise, 0 for counterclockwise
        speed_us: Pulse delay in microseconds
        steps: Number of steps to move
    """
    motor = get_motor(motor_id)
    if motor is None:
        return False

    motor.set_direction(direction)

    for _ in range(steps):
        motor.pulse(speed_us)

    return True


def move_multiple_steppers(motor_args, speed_us=None, interlace_size=None):
    """Move multiple steppers in coordinated interlaced fashion.

    This ensures smooth coordinated tentacle motion by stepping each motor
    a small amount in turn, rather than completing one motor before the next.

    Args:
        motor_args: List of dicts with keys:
            - 'id': Motor name or alias
            - 'direction': 1 for clockwise, 0 for counterclockwise
            - 'steps': Number of steps to move
        speed_us: Pulse delay in microseconds (default from config)
        interlace_size: Steps per interlace cycle (default from config)

    Returns:
        True if successful, False otherwise
    """
    if speed_us is None:
        speed_us = DEFAULT_SPEED_US
    if interlace_size is None:
        interlace_size = INTERLACE_STEP_SIZE

    if not motor_args:
        return False

    # Resolve motors and set directions
    motors_to_move = []
    for arg in motor_args:
        motor = get_motor(arg['id'])
        if motor is None:
            continue
        motor.set_direction(arg['direction'])
        motors_to_move.append({
            'motor': motor,
            'remaining': arg['steps']
        })

    if not motors_to_move:
        return False

    # Get max steps for loop control
    max_steps = max(m['remaining'] for m in motors_to_move)

    # Interlaced movement loop
    while max_steps > 0:
        for m in motors_to_move:
            if m['remaining'] > 0:
                # Step this motor by interlace_size (or remaining if less)
                steps_this_cycle = min(interlace_size, m['remaining'])
                for _ in range(steps_this_cycle):
                    m['motor'].pulse(speed_us)
                m['remaining'] -= steps_this_cycle

        max_steps -= interlace_size

    return True


# For testing directly on device
if __name__ == '__main__':
    print("Initializing motors...")
    init_motors()

    print("Testing multi-motor movement...")
    move_multiple_steppers([
        {'id': 'x', 'direction': 0, 'steps': 10},
        {'id': 'y', 'direction': 0, 'steps': 10},
    ], speed_us=2000, interlace_size=10)

    print("Motor test complete.")
