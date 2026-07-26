# laser_animations/animator_tab/path_generator.py
"""
Turns a parametric path equation + t-range + timing into a list of
(timestamp_seconds, command) events: one /summon for the static laser,
followed by one `execute ... tp @s ~ ~ ~ <yaw> <pitch>` per timestep that
rotates it to sweep along the path.

The path's origin is fixed at (0, 0, 0) and is NOT translated to the
laser's base position - only the direction from the origin to each path
point matters for the rotation math. The base position is only used to
place (summon) the laser itself.

Note: build_summon_command() intentionally duplicates the small amount of
command-formatting logic from modifier.generate_laser_commands() rather
than importing it, since modifier.py is treated as reference-only and is
not to be modified or depended on here.
"""
import logging

from .equation_parser import parse_vector_equation, parse_scalar, EquationParseError
from .rotation_math import (
    initial_yaw_for_direction,
    vector_to_yaw_pitch,
    wrap_angle_180,
    clean_number,
)


class PathGenerationError(ValueError):
    """Raised for any invalid timing/path input that isn't an equation parse error."""
    pass


def build_summon_command(base_x, base_y, base_z, block, tag, direction):
    """Mirrors the direction-specific offsets/transformation used by
    modifier.generate_laser_commands() to build the initial static laser
    that the animation then rotates."""
    if direction == "North":
        x, y, z = base_x, base_y + 0.42, base_z - 0.01
        translation = "[0.075f,0.0f,0f]"
        scale = "[0.1f,0.1f,150f]"
        left_rotation = "[0f,1f,0f,0f]"
    elif direction == "South":
        x, y, z = base_x, base_y + 0.42, base_z + 1.01
        translation = "[-0.025f,0.06f,0f]"
        scale = "[0.1f,0.1f,150f]"
        left_rotation = "[0f,0f,0f,1f]"
    elif direction == "East":
        x, y, z = base_x + 1.01, base_y + 0.42, base_z + 0.42
        translation = "[0f,0.0f,0f]"
        scale = "[150f,0.1f,0.1f]"
        left_rotation = "[0f,0f,0f,1f]"
    elif direction == "West":
        x, y, z = base_x - 0.01, base_y + 0.42, base_z
        translation = "[0f,0.0f,0.08f]"
        scale = "[150f,0.1f,0.1f]"
        left_rotation = "[0f,1f,0f,0f]"
    else:
        x, y, z = base_x, base_y + 0.42, base_z - 0.01
        translation = "[0.075f,0.0f,0f]"
        scale = "[0.1f,0.1f,150f]"
        left_rotation = "[0f,1f,0f,0f]"

    return (
        f"/summon minecraft:block_display {clean_number(x)} {clean_number(y)} {clean_number(z)} "
        f"{{block_state:{{Name:\"{block}\"}},"
        f"transformation:{{translation:{translation},"
        f"scale:{scale},"
        f"left_rotation:{left_rotation},"
        f"right_rotation:[0f,0f,0f,1f]}},"
        f"brightness:15728880,shadow:false,billboard:\"fixed\",Tags:[\"{tag}\"]}}"
    )


def build_rotate_command(tag, delta_yaw, delta_pitch):
    yaw_part = clean_number(delta_yaw)
    pitch_part = clean_number(delta_pitch)
    return f"execute as @e[tag={tag}] at @s run tp @s ~ ~ ~ ~{yaw_part} ~{pitch_part}"


def build_rotation_events(
    equation_text,
    t_start_text,
    t_end_text,
    total_time_ms,
    tick_rate,
    direction,
    base_x, base_y, base_z,
    block, tag,
):
    """
    Returns a time-ordered list of (timestamp_seconds, command) tuples,
    ready to hand to TimelineSchematicBuilder (see schem_export.py).

    step_count timesteps are spread evenly across [t_start, t_end], one
    per tick (1 / tick_rate seconds apart), for a total duration of
    total_time_ms milliseconds.
    """
    if tick_rate <= 0:
        raise PathGenerationError("Tick rate must be greater than 0.")
    if tick_rate > 500:
        raise PathGenerationError("Tick rate must be 500 or less.")
    if total_time_ms <= 0:
        raise PathGenerationError("Total time (ms) must be greater than 0.")

    (x_fn, y_fn, z_fn), _exprs = parse_vector_equation(equation_text)
    t_start = parse_scalar(t_start_text)
    t_end = parse_scalar(t_end_text)

    step_count = max(2, round(tick_rate * (total_time_ms / 1000.0)))

    events = [(0.0, build_summon_command(base_x, base_y, base_z, block, tag, direction))]

    cumulative_yaw = initial_yaw_for_direction(direction)
    cumulative_pitch = 0.0
    last_valid_raw = (cumulative_yaw, cumulative_pitch)

    for i in range(step_count):
        frac = i / (step_count - 1) if step_count > 1 else 0.0
        t = t_start + (t_end - t_start) * frac
        try:
            dx, dy, dz = x_fn(t), y_fn(t), z_fn(t)
        except Exception as e:
            raise PathGenerationError(f"Could not evaluate equation at t={t}: {e}") from e

        result = vector_to_yaw_pitch(dx, dy, dz)
        if result is None:
            raw_yaw, raw_pitch = last_valid_raw
            logging.warning(
                "Path point at t=%s is at the origin; holding previous orientation.", t
            )
        else:
            raw_yaw, raw_pitch = result
            last_valid_raw = (raw_yaw, raw_pitch)

        delta_yaw = wrap_angle_180(raw_yaw - cumulative_yaw)
        delta_pitch = raw_pitch - cumulative_pitch
        cumulative_yaw += delta_yaw
        cumulative_pitch += delta_pitch

        ts = (i + 1) / tick_rate
        events.append((ts, build_rotate_command(tag, delta_yaw, delta_pitch)))

    return events
