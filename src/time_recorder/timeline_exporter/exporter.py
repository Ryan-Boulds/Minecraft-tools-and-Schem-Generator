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

    # Fetch custom layout length dynamically from your new UI entry box
    try:
        max_z = int(app.layer_length_var.get())
    except (ValueError, AttributeError):
        max_z = 50  # Default fallback if the entry is empty or missing

    builder = TimelineSchematicBuilder(tick_rate=tick_rate)
    builder.add_events(events)
    
    # Pass the dynamic length value to the layout calculation engine
    builder.build_reference_layout(max_z_per_floor=max_z, floor_height=2)

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