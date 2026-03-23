# Coordinate Controller for Tentacle Arm
# Handles spherical coordinate transformations for the tripod cable-driven mechanism

import math
from config import MOTOR_ANGLES, STEPS_PER_DEGREE, ELEVATION_LIMIT, SLACK_AT_CENTER, SLACK_AT_LIMIT


class CoordinateController:
    """Manages spherical coordinate state and motor position calculations.

    The tentacle arm uses 3 motors positioned at 120 degrees apart (equilateral triangle).
    Each motor controls a tendon. This controller tracks:
    - Azimuth (theta): Direction the tentacle points (0-360 degrees)
    - Elevation: Tilt magnitude from center (0 = centered, positive/negative = tilted up/down)
    """

    def __init__(self):
        self.azimuth = 0.0          # Current azimuth in degrees (0-360)
        self.elevation = 0.0        # Current elevation (arbitrary units)
        self._motor_positions = {'x': 0, 'y': 0, 'z': 0}  # Actual motor positions (with slack applied)

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
        new_elevation = max(-ELEVATION_LIMIT, min(ELEVATION_LIMIT, self.elevation + delta_elevation))
        return self._move_to(self.azimuth, new_elevation)

    def home(self):
        """Return to center position (0, 0).

        Directly reverses actual motor positions — no slack model needed
        since we're returning to the known physical center.

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        deltas = {}
        for motor in ['x', 'y', 'z']:
            deltas[motor] = -self._motor_positions[motor]
        self.azimuth = 0.0
        self.elevation = 0.0
        self._motor_positions = {'x': 0, 'y': 0, 'z': 0}
        return deltas

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
            Dict with 'azimuth', 'elevation', 'motor_positions', and 'slack_factor'
        """
        return {
            'azimuth': self.azimuth,
            'elevation': self.elevation,
            'motor_positions': self._motor_positions.copy(),
            'slack_factor': self._compute_slack_factor(self.elevation)
        }

    def _compute_slack_factor(self, elevation):
        """Compute non-linear slack factor based on elevation magnitude.

        Interpolates linearly from SLACK_AT_CENTER (near 0) to
        SLACK_AT_LIMIT (at max elevation).

        Args:
            elevation: Current elevation value

        Returns:
            Slack factor between SLACK_AT_LIMIT and SLACK_AT_CENTER
        """
        t = min(abs(elevation) / ELEVATION_LIMIT, 1.0)
        return SLACK_AT_CENTER - (SLACK_AT_CENTER - SLACK_AT_LIMIT) * t

    def _move_to(self, new_azimuth, new_elevation):
        """Calculate and apply movement to new position.

        Computes deltas from actual motor positions to ideal target.
        Slack is applied per-motor: only when a release would take
        that motor further from its rest position (0). When a motor
        releases toward 0, the core helps spring back — no slack needed.

        Args:
            new_azimuth: Target azimuth in degrees
            new_elevation: Target elevation

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        ideal_new = self._calculate_ideal_positions(new_azimuth, new_elevation)
        slack = self._compute_slack_factor(new_elevation)

        deltas = {}
        for motor in ['x', 'y', 'z']:
            # Delta from actual position to ideal target
            delta = ideal_new[motor] - self._motor_positions[motor]
            # Apply slack only when releasing AND moving further from rest (0)
            if delta > 0:
                new_pos = self._motor_positions[motor] + delta
                if abs(new_pos) > abs(self._motor_positions[motor]):
                    delta = int(delta * slack)
            deltas[motor] = delta

        # Update state — track actual motor positions
        self.azimuth = new_azimuth
        self.elevation = new_elevation
        for motor in ['x', 'y', 'z']:
            self._motor_positions[motor] += deltas[motor]

        return deltas

    def seek(self, target_azimuth, target_elevation):
        """Move toward a target (azimuth, elevation) in one step.

        Used by the 8-position joystick steering model to jump directly to the
        target rather than nudging incrementally.

        Args:
            target_azimuth: Target azimuth in degrees (0-360)
            target_elevation: Target elevation (clamped to ±ELEVATION_LIMIT)

        Returns:
            Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        """
        target_elevation = max(-ELEVATION_LIMIT, min(ELEVATION_LIMIT, target_elevation))
        return self._move_to(target_azimuth, target_elevation)

    def _calculate_ideal_positions(self, azimuth, elevation):
        """Calculate ideal motor positions (pure geometry, no slack).

        Uses the formula: position = elevation * cos(azimuth - motor_angle)

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
