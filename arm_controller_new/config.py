# Configuration for Tentacle Arm Controller
# Raspberry Pi Pico W with A4988/DRV8825 drivers

# WiFi credentials - UPDATE THESE
WIFI_SSID = "iPhone von Tzvetan"
WIFI_PASSWORD = "hallohallo"

# Pin mappings for stepper motors (STEP, DIR)
# Matching the original motorTest.py layout
MOTORS = {
    'motor1': {'step': 2, 'dir': 3},
    'motor2': {'step': 4, 'dir': 5},
    'motor3': {'step': 6, 'dir': 7},
}

# Motor settings
STEPS_PER_REV = 200          # Steps per full revolution (typical for NEMA17)
DEFAULT_SPEED_US = 1000      # Default pulse delay in microseconds
MIN_SPEED_US = 100           # Fastest speed (shortest delay)
MAX_SPEED_US = 5000          # Slowest speed (longest delay)
DEFAULT_STEPS = 100          # Default steps per jog
INTERLACE_STEP_SIZE = 10     # Steps per interlace cycle

# Direction constants
CLOCKWISE = 1
COUNTERCLOCKWISE = 0

# Web server settings
WEB_PORT = 80

# Motor aliases for API compatibility (x, y, z mapping to motor1, motor2, motor3)
MOTOR_ALIASES = {'x': 'motor1', 'y': 'motor2', 'z': 'motor3'}

# Coordinate mode settings
# Motor angular positions (equilateral triangle layout, 120° apart)
MOTOR_ANGLES = {'x': 0, 'y': 120, 'z': 240}

# Step sizes for coordinate mode controls
ROTATION_STEP_DEGREES = 15    # Degrees per rotation button press
ELEVATION_STEP_UNITS = 10     # Elevation change per button press
STEPS_PER_DEGREE = 5          # Motor steps per degree of tilt (tunable)
ELEVATION_LIMIT = 60          # Maximum elevation magnitude (±30)

# Slack compensation for semi-rigid core
# The core resists deflection, so releasing motors should give less cable.
# Slack factor decreases (less release) as elevation increases.
SLACK_AT_CENTER = 0.5         # Slack factor near 0 elevation
SLACK_AT_LIMIT = 0.2          # Slack factor at max elevation

# Continuous movement settings (WebSocket hold-to-move)
CONTINUOUS_ROTATE_INCREMENT = 1    # Degrees per loop cycle
CONTINUOUS_TILT_INCREMENT = 1      # Elevation units per loop cycle
POSITION_UPDATE_INTERVAL_MS = 200  # Position update frequency
