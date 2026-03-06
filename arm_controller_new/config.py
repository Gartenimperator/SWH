# Configuration for Tentacle Arm Controller
# Raspberry Pi Pico W with A4988/DRV8825 drivers

# =============================================================================
# PIN ASSIGNMENTS
# =============================================================================

# Stepper motors (STEP, DIR)
MOTORS = {
    'motor1': {'step': 2, 'dir': 3},
    'motor2': {'step': 4, 'dir': 5},
    'motor3': {'step': 6, 'dir': 7},
}

# Joystick (analog axes + switch)
JOYSTICK_X_PIN  = 28
JOYSTICK_Y_PIN  = 27
JOYSTICK_SW_PIN = 22

# Gamepad / touchpad (I2C)
GAMEPAD_SDA_PIN = 0
GAMEPAD_SCL_PIN = 1

# LED RGB (PWM channels, GND on hardware pin)
LED_RED_PIN   = 19
LED_GREEN_PIN = 20
LED_BLUE_PIN  = 21
# Tension/slack detection buttons (one per motor, pressed = string under tension)
# NOTE: pins 16/17/18 currently overlap with LED pins above — reassign as needed
TENSION_BUTTON_PINS = {'x': 10, 'y': 11, 'z': 12}
#11->left 12-middle 13-right

# Steps pulled per calibration iteration when taking up slack
CALIBRATION_PULL_STEPS = 5

# =============================================================================
# MOTOR SETTINGS
# =============================================================================

MOTOR_ALIASES   = {'x': 'motor1', 'y': 'motor2', 'z': 'motor3'}
CLOCKWISE       = 1
COUNTERCLOCKWISE = 0

STEPS_PER_REV      = 200    # Steps per full revolution (NEMA17)
DEFAULT_SPEED_US   = 1000   # Pulse half-period in microseconds
MIN_SPEED_US       = 100    # Fastest (shortest delay)
MAX_SPEED_US       = 5000   # Slowest (longest delay)
DEFAULT_STEPS      = 100    # Default steps per jog
INTERLACE_STEP_SIZE = 10    # Steps per interlace cycle

# =============================================================================
# COORDINATE CONTROLLER
# =============================================================================

# Motor angular positions (equilateral triangle, 120° apart)
MOTOR_ANGLES = {'x': 0, 'y': 120, 'z': 240}

STEPS_PER_DEGREE     = 5    # Motor steps per degree of tilt (tunable)
ELEVATION_LIMIT      = 50   # Maximum elevation magnitude (±60)
ROTATION_STEP_DEGREES = 5   # Degrees per joystick step
ELEVATION_STEP_UNITS  = 3   # Elevation units per joystick step

# Slack compensation — core resists deflection, so releases give less cable
SLACK_AT_CENTER = 0.15       # Slack factor near 0 elevation
SLACK_AT_LIMIT  = 0       # Slack factor at max elevation

# =============================================================================
# JOYSTICK CONTROL
# =============================================================================

JOYSTICK_SAMPLE_DELAY = 0.1  # Seconds between ADC reads
JOYSTICK_MIN          = 300  # Physical minimum ADC reading (hardware limit)
JOYSTICK_MAX          = 1024  # Physical maximum ADC reading (hardware limit)
JOYSTICK_CENTER       = 512  # Mid-point of physical range
JOYSTICK_DEADZONE     = 106  # Raw units around centre → output 0 (midpoint between CENTER and MIN)

# =============================================================================
# GAMEPAD CONTROL
# =============================================================================

GAMEPAD_ADDRESS      = 0x57
GAMEPAD_POLL_DELAY   = 0.05  # Seconds between button polls
GAMEPAD_MANUAL_STEPS = 20    # Steps per UP/DOWN button event
