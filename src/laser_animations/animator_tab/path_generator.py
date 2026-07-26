# laser_animations/animator_tab/path_generator.py
"""
Turns a parametric path equation + t-range + timing into a list of
(timestamp_seconds, command) events, where each command is a single
`execute as @e[tag=...] at @s run tp @s ~ ~ ~ <yaw> <pitch>` relative
rotation.

This tab does NOT summon anything - it's meant to steer lasers that are
already spawned in-game (each possibly at a different starting angle).
Because of that, every command here is a *delta* between two consecutive
points on the path; there is no initial "snap to the start of the curve"
command, since that would assume a known starting orientation. In-game,
the laser is expected to already be aimed at (or close to) the path's
starting point before these commands run.

The path's origin is fixed at (0, 0, 0) - the program doesn't need or
use real in-game coordinates for this tab, only the direction from the
origin to each path point.
"""
import logging

from .equation_parser import parse_vector_equation, parse_scalar, EquationParseError
from .rotation_math import vector_to_yaw_pitch, wrap_angle_180, clean_number


class PathGenerationError(ValueError):
    """Raised for any invalid timing/path input that isn't an equation parse error."""
    pass


def build_rotate_command(tag, delta_yaw, delta_pitch):
    yaw_part = clean_number(delta_yaw)
    pitch_part = clean_number(delta_pitch)
    return f"execute as @e[tag={tag}] at @s run tp @s ~ ~ ~ ~{yaw_part} ~{pitch_part}"


def compute_step_count(tick_rate, total_time_ms):
    if tick_rate <= 0:
        raise PathGenerationError("Tick rate must be greater than 0.")
    if tick_rate > 500:
        raise PathGenerationError("Tick rate must be 500 or less.")
    if total_time_ms <= 0:
        raise PathGenerationError("Total time (ms) must be greater than 0.")
    return max(2, round(tick_rate * (total_time_ms / 1000.0)))


def sample_curve(equation_text, t_start_text, t_end_text, step_count):
    """Evaluates (x(t), y(t), z(t)) at `step_count` evenly spaced values
    of t across [t_start, t_end] (inclusive of both ends)."""
    (x_fn, y_fn, z_fn), _exprs = parse_vector_equation(equation_text)
    t_start = parse_scalar(t_start_text)
    t_end = parse_scalar(t_end_text)

    points = []
    for i in range(step_count):
        frac = i / (step_count - 1) if step_count > 1 else 0.0
        t = t_start + (t_end - t_start) * frac
        try:
            points.append((x_fn(t), y_fn(t), z_fn(t)))
        except Exception as e:
            raise PathGenerationError(f"Could not evaluate equation at t={t}: {e}") from e
    return points


def build_rotation_events(equation_text, t_start_text, t_end_text, total_time_ms, tick_rate, tag):
    """
    Returns a time-ordered list of (timestamp_seconds, command) tuples -
    one relative rotation command per timestep after the first - ready to
    hand to TimelineSchematicBuilder (see schem_export.py).
    """
    step_count = compute_step_count(tick_rate, total_time_ms)
    points = sample_curve(equation_text, t_start_text, t_end_text, step_count)

    first = vector_to_yaw_pitch(*points[0])
    if first is None:
        raise PathGenerationError(
            "The path starts at the origin (0, 0, 0), where direction is undefined. "
            "Adjust t start or the equation so the starting point isn't (0, 0, 0)."
        )
    cumulative_yaw, cumulative_pitch = first
    last_valid_raw = first

    events = []
    for i in range(1, step_count):
        result = vector_to_yaw_pitch(*points[i])
        if result is None:
            raw_yaw, raw_pitch = last_valid_raw
            logging.warning("Path point %d is at the origin; holding previous orientation.", i)
        else:
            raw_yaw, raw_pitch = result
            last_valid_raw = result

        delta_yaw = wrap_angle_180(raw_yaw - cumulative_yaw)
        delta_pitch = raw_pitch - cumulative_pitch
        cumulative_yaw += delta_yaw
        cumulative_pitch += delta_pitch

        ts = i / tick_rate
        events.append((ts, build_rotate_command(tag, delta_yaw, delta_pitch)))

    return events
