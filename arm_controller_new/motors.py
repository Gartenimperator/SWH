# Motor control module for Tentacle Arm Controller
# Raspberry Pi Pico W with A4988/DRV8825 drivers
# Uses PIO state machines for precise hardware-timed stepping

from machine import Pin
import rp2
from config import MOTORS, MOTOR_ALIASES, DEFAULT_SPEED_US, INTERLACE_STEP_SIZE

# PIO clock frequency (1MHz = 1 cycle per microsecond for easy timing)
PIO_FREQ = 1_000_000


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, autopull=False, fifo_join=rp2.PIO.JOIN_TX)
def stepper_pio():
    """PIO program for precise stepper pulse generation.
    Protocol: Send two values to FIFO:
      1. delay_cycles (half-period in PIO cycles, stored in ISR)
      2. step_count (number of pulses to generate)
    Uses ISR to preserve delay value across the step loop.
    At 1MHz PIO clock, 1 cycle = 1 microsecond.
    """
    wrap_target()
    pull(block)              # Wait for delay value
    mov(isr, osr)            # ISR = delay (preserved)
    pull(block)              # Wait for step count
    mov(x, osr)              # X = step count
    label("step_loop")
    set(pins, 1)             # Step HIGH
    mov(y, isr)              # Y = delay countdown
    label("delay_high")
    jmp(y_dec, "delay_high") # Count down
    set(pins, 0)             # Step LOW
    mov(y, isr)              # Y = delay countdown
    label("delay_low")
    jmp(y_dec, "delay_low")  # Count down
    jmp(x_dec, "step_loop")  # Decrement X and loop if not zero
    wrap()                   # Return to start, wait for next command


class StepperMotor:
    """Wrapper for stepper motor control via PIO state machine."""

    _sm_index = 0  # Track which state machine to use next

    def __init__(self, name, step_pin, dir_pin):
        self.name = name
        self.dir = Pin(dir_pin, Pin.OUT)
        self.dir.value(0)

        # Each motor gets its own PIO state machine
        self.sm = rp2.StateMachine(
            StepperMotor._sm_index,
            stepper_pio,
            freq=PIO_FREQ,
            set_base=Pin(step_pin)
        )
        self.sm.active(1)
        StepperMotor._sm_index += 1

    def set_direction(self, direction):
        """Set motor direction (1 = clockwise, 0 = counterclockwise)."""
        self.dir.value(direction)

    def step_async(self, steps, delay_us):
        """Start stepping without blocking. PIO handles timing in hardware.

        Args:
            steps: Number of steps to execute
            delay_us: Half-period delay in microseconds

        Note: At 1MHz PIO clock, delay_us directly equals PIO cycles.
        The jmp loop adds ~2 cycles overhead per delay, so actual timing
        is very close to requested microseconds.
        """
        if steps == 0:
            return
        # Send delay first, then step count (matches PIO protocol)
        self.sm.put(delay_us)
        self.sm.put(steps)

    def pulse(self, delay_us):
        """Generate one step pulse with given delay (blocking for compatibility)."""
        self.step_async(1, delay_us)
        # Brief wait for single step to complete
        import time
        time.sleep_us(delay_us * 2 + 10)


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
    motor.step_async(steps, speed_us)

    # Wait for movement to complete (total time = steps * 2 * delay)
    import time
    time.sleep_us(steps * speed_us * 2 + 100)

    return True


def move_multiple_steppers(motor_args, speed_us=None, interlace_size=None):
    """Move multiple steppers simultaneously using PIO hardware timing.

    All motors start at the same time and run in parallel via their
    dedicated PIO state machines - no interlacing needed with hardware timing.

    Args:
        motor_args: List of dicts with keys:
            - 'id': Motor name or alias
            - 'direction': 1 for clockwise, 0 for counterclockwise
            - 'steps': Number of steps to move
        speed_us: Pulse delay in microseconds (default from config)
        interlace_size: Ignored (kept for API compatibility)

    Returns:
        True if successful, False otherwise
    """
    import time

    if speed_us is None:
        speed_us = DEFAULT_SPEED_US

    if not motor_args:
        return False

    # Resolve motors and set directions
    motors_to_move = []
    max_steps = 0
    for arg in motor_args:
        motor = get_motor(arg['id'])
        if motor is None:
            continue
        motor.set_direction(arg['direction'])
        motors_to_move.append({
            'motor': motor,
            'steps': arg['steps']
        })
        max_steps = max(max_steps, arg['steps'])

    if not motors_to_move:
        return False

    # Start all motors simultaneously - PIO handles timing in hardware
    for m in motors_to_move:
        m['motor'].step_async(m['steps'], speed_us)

    # Wait for longest movement to complete
    time.sleep_us(max_steps * speed_us * 2 + 100)

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
