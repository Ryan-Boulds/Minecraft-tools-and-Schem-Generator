# laser_animations/animator_tab/rotation_math.py
"""
Vector <-> Minecraft yaw/pitch conversion for the Animate tab.

Minecraft's look-vector convention:
    dx = -sin(yaw) * cos(pitch)
    dy = -sin(pitch)
    dz =  cos(yaw) * cos(pitch)
(yaw/pitch in degrees; yaw 0 = south/+Z, 90 = west/-X, 180 = north/-Z,
-90 = east/+X; pitch 0 = level, -90 = straight up, 90 = straight down.)
"""
import math

# Yaw the laser is assumed to already be facing after the static summon
# command in generate_laser_gui.py / modifier.py, before any animation
# rotation is applied.
COMPASS_YAW = {
    "South": 0.0,
    "West": 90.0,
    "North": 180.0,
    "East": -90.0,
}


def initial_yaw_for_direction(direction):
    return COMPASS_YAW.get(direction, 0.0)


def vector_to_yaw_pitch(dx, dy, dz):
    """
    Converts a direction vector into (yaw, pitch) in degrees that would
    point a Minecraft entity along that vector.

    Returns None if the vector is (effectively) the zero vector, since
    yaw/pitch are undefined at the origin.
    """
    horizontal = math.hypot(dx, dz)
    if horizontal < 1e-9 and abs(dy) < 1e-9:
        return None
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = math.degrees(math.atan2(-dy, horizontal))
    return yaw, pitch


def wrap_angle_180(angle):
    """Wraps an angle in degrees to (-180, 180], i.e. the shortest turn."""
    return (angle + 180.0) % 360.0 - 180.0


def clean_number(num, precision=3):
    """Formats a float the same way modifier.py's clean() does - trims
    trailing zeros, drops the decimal point for whole numbers."""
    if abs(num) < 10 ** (-precision):
        return "0"
    rounded = round(num, precision)
    if abs(rounded - int(rounded)) < 1e-9:
        return str(int(rounded))
    s = f"{rounded:.{precision}f}".rstrip('0').rstrip('.')
    return s
