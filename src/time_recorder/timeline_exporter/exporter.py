# time_recorder/timeline_exporter/exporter.py
import gzip
import nbtlib
from nbtlib.tag import Compound
from tkinter import filedialog, messagebox

from .timeline_builder import TimelineSchematicBuilder


def generate_timeline_schematic(app) -> str | None:
    events = app.get_merged_timeline()
    if not events:
        messagebox.showwarning("Empty Timeline", "No commands to export.")
        return None

    tick_rate = float(app.tick_rate.get() or 20.0)

    builder = TimelineSchematicBuilder(tick_rate=tick_rate)
    builder.add_events(events)
    builder.build_reference_layout(max_z_per_floor=15, floor_height=2)

    schematic_nbt = builder.to_schematic_data()

    filepath = filedialog.asksaveasfilename(
        defaultextension=".schem",
        filetypes=[("WorldEdit Schematic", "*.schem")],
        title="Save Timeline Schematic"
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
            f"Timeline exported successfully!\n"
            f"• {num_events} commands\n"
            f"• {num_blocks} redstone components\n"
            f"• {len(schematic_nbt['BlockData'])} blocks total\n"
            f"Saved to: {filepath}"
        )
        return filepath
    except Exception as e:
        messagebox.showerror("Export Error", str(e))
        return None