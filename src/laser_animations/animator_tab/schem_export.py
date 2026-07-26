# laser_animations/animator_tab/schem_export.py
"""
Builds and saves a WorldEdit .schem for a laser-rotation animation's
timed command events.

This intentionally re-implements the small amount of save/gzip glue from
time_recorder.timeline_exporter.exporter.generate_timeline_schematic()
rather than calling that function directly, since it's wired to the
shared app.get_merged_timeline() / app.tick_rate flow used by the general
command-timeline tab, which the Animate tab doesn't participate in. The
actual schematic-building class (TimelineSchematicBuilder) is imported
and reused unmodified - exporter.py, gui_integration.py, and
timeline_builder.py itself are not touched.

NOTE: adjust the import below if your project's package root differs
from `time_recorder.timeline_exporter.timeline_builder` (inferred from
the header comment in the timeline_builder.py you provided).
"""
import gzip
import logging
from tkinter import filedialog, messagebox

import nbtlib

from time_recorder.timeline_exporter.timeline_builder import TimelineSchematicBuilder


def export_animation_schematic(events, tick_rate, layer_length=50, height_limit=50, floor_height=2):
    """
    events: list of (timestamp_seconds, command) tuples, time-ordered.
    tick_rate: same tick_rate used to generate the events (see path_generator).
    layer_length / height_limit: schematic layout limits, same meaning as
        exporter.py's max_z_per_floor / max_height.
    """
    if not events:
        messagebox.showwarning("Empty Animation", "No commands to export.")
        return None

    builder = TimelineSchematicBuilder(tick_rate=tick_rate)
    builder.add_events(events)
    builder.build_reference_layout(
        max_z_per_floor=layer_length,
        floor_height=floor_height,
        max_height=height_limit,
    )
    schematic_nbt = builder.to_schematic_data()

    filepath = filedialog.asksaveasfilename(
        defaultextension=".schem",
        filetypes=[("WorldEdit Schematic", "*.schem")],
        title="Save Laser Animation Schematic",
    )
    if not filepath:
        return None

    try:
        with open(filepath, 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                nbtlib.File(schematic_nbt).write(gz)

        num_events = len(events)
        num_blocks = len(builder.physical_items)
        messagebox.showinfo(
            "Export Successful",
            f"Laser animation exported successfully!\n"
            f"- {num_events} commands\n"
            f"- {num_blocks} redstone components\n"
            f"- {len(schematic_nbt['BlockData'])} blocks total\n"
            f"Saved to: {filepath}"
        )
        return filepath
    except Exception as e:
        logging.error(f"Animation schematic export error: {e}")
        messagebox.showerror("Export Error", str(e))
        return None
