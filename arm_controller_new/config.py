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
