# Coordinate Controller for Tentacle Arm
# Handles spherical coordinate transformations for the tripod cable-driven mechanism

import math
from config import MOTOR_ANGLES, STEPS_PER_DEGREE


class CoordinateController:
    """Manages spherical coordinate state and motor position calculations.

    The tentacle arm uses 3 motors positioned at 120 degrees apart (equilateral triangle).
    Each motor controls a tendon. This controller tracks:
    - Azimuth (theta): Direction the tentacle points (0-360 degrees)
    - Elevation: Tilt magnitude from center (0 = centered, positive = tilted)
    """

    def __init__(self):
        self.azimuth = 0.0          # Current azimuth in degrees (0-360)
        self.elevation = 0.0        # Current elevation (arbitrary units)
        self._motor_positions = {'x': 0, 'y': 0, 'z': 0}  # Accumulated motor positions
        self._center_offsets = {'x': 0, 'y': 0, 'z': 0}   # Offsets from calibration

    def rotate(self, delta_degrees):
        """Rotate azimuth by delta_degrees, return motor step deltas.

        Args:
            delta_degrees: Degrees to rotate (positive = counterclockwise from above)

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        new_azimuth = (self.azimuth + delta_degrees) % 360
        return self._move_to(new_azimuth, self.elevation)

    def tilt(self, delta_elevation):
        """Change elevation by delta_elevation, return motor step deltas.

        Args:
            delta_elevation: Amount to change elevation (positive = tilt more)

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        new_elevation = max(0, self.elevation + delta_elevation)
        return self._move_to(self.azimuth, new_elevation)

    def home(self):
        """Return to center position (0, 0).

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        return self._move_to(0, 0)

    def set_center(self):
        """Mark current physical position as the new center (origin).

        Resets coordinate state to (0, 0) without moving motors.
        Called after user manually calibrates the tentacle position.
        """
        self.azimuth = 0.0
        self.elevation = 0.0
        self._motor_positions = {'x': 0, 'y': 0, 'z': 0}
        print(self)

    def get_position(self):
        """Get current coordinate state.

        Returns:
            Dict with 'azimuth', 'elevation', and 'motor_positions'
        """
        return {
            'azimuth': self.azimuth,
            'elevation': self.elevation,
            'motor_positions': self._motor_positions.copy()
        }

    def _move_to(self, new_azimuth, new_elevation):
        """Calculate and apply movement to new position.

        Args:
            new_azimuth: Target azimuth in degrees
            new_elevation: Target elevation

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        new_positions = self._calculate_positions(new_azimuth, new_elevation)

        # Calculate deltas (difference from current position)
        deltas = {}
        for motor in ['x', 'y', 'z']:
            deltas[motor] = new_positions[motor] - self._motor_positions[motor]

        # Update state
        self.azimuth = new_azimuth
        self.elevation = new_elevation
        self._motor_positions = new_positions

        return deltas

    def _calculate_positions(self, azimuth, elevation):
        """Calculate motor positions for given spherical coordinates.

        Uses the formula: position = elevation * cos(azimuth - motor_angle)

        For a tripod mechanism:
        - Motor X at 0 degrees: pulls toward 0 degree direction
        - Motor Y at 120 degrees: pulls toward 120 degree direction
        - Motor Z at 240 degrees: pulls toward 240 degree direction

        When elevation > 0 and azimuth points toward a motor, that motor
        has positive position (releases), opposite motor has negative (pulls).

        Args:
            azimuth: Direction in degrees (0-360)
            elevation: Tilt magnitude

        Returns:
            Dict of motor positions {'x': int, 'y': int, 'z': int}
        """
        positions = {}
        azimuth_rad = math.radians(azimuth)

        for motor, angle in MOTOR_ANGLES.items():
            angle_rad = math.radians(angle)
            # Calculate position based on projection of tilt direction onto motor axis
            position = elevation * math.cos(azimuth_rad - angle_rad) * STEPS_PER_DEGREE
            positions[motor] = int(position)

        return positions


# Global instance for the application
_controller = None


def get_controller():
    """Get or create the global CoordinateController instance."""
    global _controller
    if _controller is None:
        _controller = CoordinateController()
    return _controller
