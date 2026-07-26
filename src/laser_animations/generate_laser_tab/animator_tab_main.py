# laser_animations/animator_tab/animator_tab_main.py
"""
Builds the 'Animate' sub-tab under Laser Animations.

Lets the user describe a parametric path (x(t), y(t), z(t)) - with the
laser's origin fixed at (0, 0, 0) - then generates a sequence of relative
rotation commands (`execute as @e[tag=...] at @s run tp @s ~ ~ ~ <yaw>
<pitch>`) that sweep the laser along that path, timed against a chosen
total duration and tick rate, and exports the whole sequence as a
WorldEdit .schem using the existing TimelineSchematicBuilder.

Public interface (unchanged from the placeholder, since laser_tab_main.py
imports these by name):
    create_animator_gui(parent_frame, app)
    process_command(app, command)
"""
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from .equation_parser import EquationParseError
from .path_generator import build_rotation_events, PathGenerationError
from .schem_export import export_animation_schematic
from .animator_preview import PathPreview


def create_animator_gui(parent_frame, app):
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.columnconfigure(1, weight=1)

    app.animator_last_events = []
    app.animator_last_layout = None

    # ---- Header ----
    tk.Label(
        parent_frame, text="Animate", font=("Segoe UI", 16, "bold"), fg="#2e7d32"
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

    tk.Label(
        parent_frame,
        text=(
            "Describe the path as (x(t), y(t), z(t)) - e.g. (10, 10cos(t), 10sin(t)).\n"
            "The laser's origin is treated as (0, 0, 0) for this path; it is NOT\n"
            "translated to the base laser position below (that position is only\n"
            "used to summon the laser)."
        ),
        font=("Segoe UI", 9), justify="left", fg="#555555",
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

    # ---- Equation ----
    tk.Label(parent_frame, text="Path (x(t), y(t), z(t)):", font=("Segoe UI", 10, "bold")).grid(
        row=2, column=0, sticky="w", padx=10, pady=2
    )
    app.animator_equation_var = tk.StringVar(value="(10, 10cos(t), 10sin(t))")
    tk.Entry(parent_frame, textvariable=app.animator_equation_var, width=40).grid(
        row=2, column=1, sticky="we", padx=10, pady=2
    )

    # ---- t range ----
    t_frame = ttk.Frame(parent_frame)
    t_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=2)
    tk.Label(t_frame, text="t start:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    app.animator_t_start_var = tk.StringVar(value="0")
    tk.Entry(t_frame, textvariable=app.animator_t_start_var, width=10).grid(row=0, column=1, padx=(2, 15))
    tk.Label(t_frame, text="t end:", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
    app.animator_t_end_var = tk.StringVar(value="pi/2")
    tk.Entry(t_frame, textvariable=app.animator_t_end_var, width=10).grid(row=0, column=3, padx=(2, 0))

    # ---- Timing ----
    timing_frame = ttk.Frame(parent_frame)
    timing_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=2)
    tk.Label(timing_frame, text="Total time (ms):", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    app.animator_time_ms_var = tk.StringVar(value="2000")
    tk.Entry(timing_frame, textvariable=app.animator_time_ms_var, width=10).grid(row=0, column=1, padx=(2, 15))
    tk.Label(timing_frame, text="Tick rate (1-500):", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
    app.animator_tick_rate_var = tk.StringVar(value="20")
    tk.Entry(timing_frame, textvariable=app.animator_tick_rate_var, width=10).grid(row=0, column=3, padx=(2, 0))

    # ---- Layout options (schem sizing, same meaning as the general exporter) ----
    layout_frame = ttk.Frame(parent_frame)
    layout_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=2)
    tk.Label(layout_frame, text="Layer length:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    app.animator_layer_length_var = tk.StringVar(value="50")
    tk.Entry(layout_frame, textvariable=app.animator_layer_length_var, width=10).grid(row=0, column=1, padx=(2, 15))
    tk.Label(layout_frame, text="Height limit:", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
    app.animator_height_limit_var = tk.StringVar(value="50")
    tk.Entry(layout_frame, textvariable=app.animator_height_limit_var, width=10).grid(row=0, column=3, padx=(2, 0))

    # ---- Base laser note (reuses the Generate Laser tab's shared vars) ----
    tk.Label(
        parent_frame,
        text="Uses the base position / block / tag / direction from the Generate Laser tab.",
        font=("Segoe UI", 9), fg="#555555",
    ).grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 8))

    # ---- Buttons ----
    button_frame = ttk.Frame(parent_frame)
    button_frame.grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=4)

    tk.Button(
        button_frame, text="Preview Path", command=lambda: _preview_path(app),
        font=("Segoe UI", 10), bg="#2196F3", fg="#ffffff",
    ).grid(row=0, column=0, padx=(0, 5))

    tk.Button(
        button_frame, text="Generate Commands", command=lambda: _generate_events(app),
        font=("Segoe UI", 10), bg="#4CAF50", fg="#ffffff",
    ).grid(row=0, column=1, padx=5)

    tk.Button(
        button_frame, text="Export Schematic", command=lambda: _export(app),
        font=("Segoe UI", 10), bg="#FF9800", fg="#ffffff",
    ).grid(row=0, column=2, padx=5)

    # ---- Output ----
    app.animator_output_text = tk.Text(parent_frame, height=14, width=70)
    app.animator_output_text.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=10, pady=(4, 10))
    parent_frame.rowconfigure(8, weight=1)

    app.animator_status_var = tk.StringVar(value="")
    tk.Label(parent_frame, textvariable=app.animator_status_var, font=("Segoe UI", 9), fg="#555555").grid(
        row=9, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10)
    )


def _get_float(var, label):
    try:
        return float(var.get())
    except ValueError:
        raise PathGenerationError(f"{label} must be a number.")


def _get_int(var, label):
    try:
        return int(float(var.get()))
    except ValueError:
        raise PathGenerationError(f"{label} must be a whole number.")


def _collect_inputs(app):
    tick_rate = _get_float(app.animator_tick_rate_var, "Tick rate")
    total_time_ms = _get_float(app.animator_time_ms_var, "Total time (ms)")
    layer_length = _get_int(app.animator_layer_length_var, "Layer length")
    height_limit = _get_int(app.animator_height_limit_var, "Height limit")

    base_x = _get_float(app.laser_x, "Base X")
    base_y = _get_float(app.laser_y, "Base Y")
    base_z = _get_float(app.laser_z, "Base Z")
    block = app.laser_block.get() or "minecraft:lime_concrete"
    tag = app.laser_tag.get() or "beam1"
    direction = app.laser_direction.get() if hasattr(app, "laser_direction") else "North"

    return dict(
        equation_text=app.animator_equation_var.get(),
        t_start_text=app.animator_t_start_var.get(),
        t_end_text=app.animator_t_end_var.get(),
        total_time_ms=total_time_ms,
        tick_rate=tick_rate,
        direction=direction,
        base_x=base_x, base_y=base_y, base_z=base_z,
        block=block, tag=tag,
        layer_length=layer_length, height_limit=height_limit,
    )


def _generate_events(app):
    try:
        inputs = _collect_inputs(app)
        layer_length = inputs.pop("layer_length")
        height_limit = inputs.pop("height_limit")
        events = build_rotation_events(**inputs)
    except (EquationParseError, PathGenerationError) as e:
        messagebox.showerror("Invalid Input", str(e))
        return None
    except Exception as e:
        logging.error(f"Unexpected error generating animation events: {e}")
        messagebox.showerror("Error", str(e))
        return None

    app.animator_last_events = events
    app.animator_last_layout = (inputs["tick_rate"], layer_length, height_limit)

    app.animator_output_text.delete("1.0", tk.END)
    for ts, cmd in events:
        app.animator_output_text.insert(tk.END, f"[t={ts:.3f}s] {cmd}\n")

    app.animator_status_var.set(f"Generated {len(events)} commands.")
    return events


def _preview_path(app):
    try:
        from .equation_parser import parse_vector_equation, parse_scalar
        (x_fn, y_fn, z_fn), _exprs = parse_vector_equation(app.animator_equation_var.get())
        t_start = parse_scalar(app.animator_t_start_var.get())
        t_end = parse_scalar(app.animator_t_end_var.get())
    except EquationParseError as e:
        messagebox.showerror("Invalid Equation", str(e))
        return

    try:
        steps = 200
        points = []
        for i in range(steps + 1):
            t = t_start + (t_end - t_start) * i / steps
            points.append((x_fn(t), y_fn(t), z_fn(t)))
    except Exception as e:
        messagebox.showerror("Evaluation Error", str(e))
        return

    try:
        PathPreview.show(points)
    except ImportError:
        messagebox.showinfo(
            "Preview Unavailable",
            "Install matplotlib to enable the path preview:\n\npip install matplotlib",
        )
    except Exception as e:
        messagebox.showerror("Preview Error", str(e))


def _export(app):
    events = app.animator_last_events
    if not events:
        events = _generate_events(app)
        if not events:
            return
    tick_rate, layer_length, height_limit = app.animator_last_layout
    result = export_animation_schematic(
        events, tick_rate, layer_length=layer_length, height_limit=height_limit
    )
    if result:
        app.animator_status_var.set(f"Exported to: {result}")


def process_command(app, command):
    """
    Placeholder command processor for the 'Animate' sub-tab, wired into
    CommandModifierGUI.process_command() in main.py so clipboard-triggered
    processing on this tab doesn't error out. The Animate tab is driven by
    its own Generate/Export buttons rather than clipboard paste, so this
    intentionally does nothing beyond logging.
    """
    logging.debug(
        "Animate tab: process_command called (ignored - use Generate Commands / Export Schematic buttons)"
    )
