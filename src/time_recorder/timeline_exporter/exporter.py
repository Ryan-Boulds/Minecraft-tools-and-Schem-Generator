# ==================== time_recorder/timeline_exporter/exporter.py ====================
import math
import logging
from nbtlib.tag import (
    Compound, List, Byte, Int, Short, ByteArray, 
    String, IntArray, Long
)
import nbtlib
import gzip
from tkinter import filedialog, messagebox


def generate_timeline_schematic(app) -> str | None:
    """Generate correct compact timeline schematic with proper repeater delays."""
    events = app.get_merged_timeline()
    if not events:
        messagebox.showwarning("Empty Timeline", "No commands to export.")
        return None

    tick_rate = float(app.tick_rate.get() or 20)

    # Palette
    palette = Compound({
        "minecraft:command_block[conditional=false,facing=south]": Int(0),
        "minecraft:repeater[delay=1,facing=south,locked=false,powered=false]": Int(1),
        "minecraft:repeater[delay=4,facing=south,locked=false,powered=false]": Int(2),
        "minecraft:command_block[conditional=false,facing=east]": Int(3),
        "minecraft:command_block[conditional=false,facing=up]": Int(4),
        "minecraft:repeater[delay=3,facing=south,locked=false,powered=false]": Int(5),
        "minecraft:repeater[delay=2,facing=south,locked=false,powered=false]": Int(6),
    })

    block_list = []
    block_entities: List[Compound] = List[Compound]()

    current_z = 0

    # First command block at position 0
    block_list.append(0)
    add_command_block_entity(block_entities, current_z, events[0][1])

    prev_ticks = 0

    for timestamp, command in events[1:]:
        current_ticks = round(timestamp * tick_rate)
        delta_ticks = current_ticks - prev_ticks

        if delta_ticks < 1:
            delta_ticks = 1

        # Place repeaters for this delay
        remaining = delta_ticks
        while remaining > 0:
            if remaining >= 4:
                block_list.append(2)      # 4 tick repeater
                remaining -= 4
            elif remaining >= 3:
                block_list.append(5)      # 3 tick
                remaining -= 3
            elif remaining >= 2:
                block_list.append(6)      # 2 tick
                remaining -= 2
            else:
                block_list.append(1)      # 1 tick
                remaining -= 1

            current_z += 1

        # Place next command block
        current_z += 1
        block_list.append(0)
        add_command_block_entity(block_entities, current_z, command)

        prev_ticks = current_ticks

    length = len(block_list)
    block_data = ByteArray(block_list)

    # Final schematic
    schematic_data = Compound({
        "Version": Int(2),
        "DataVersion": Int(3578),
        "Width": Short(1),
        "Height": Short(1),
        "Length": Short(length),
        "PaletteMax": Int(len(palette)),
        "Palette": palette,
        "BlockData": block_data,
        "BlockEntities": block_entities,
        "Offset": IntArray([0, 0, 0]),
        "Metadata": Compound({
            "WEOffsetX": Int(0),
            "WEOffsetY": Int(0),
            "WEOffsetZ": Int(-length + 8)
        })
    })

    # Save dialog
    filepath = filedialog.asksaveasfilename(
        defaultextension=".schem",
        filetypes=[("WorldEdit Schematic", "*.schem")],
        title="Save Timeline Schematic"
    )

    if not filepath:
        return None

    try:
        schem = nbtlib.File(schematic_data)
        with open(filepath, 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                schem.write(gz)

        messagebox.showinfo("Success", 
            f"Timeline exported successfully!\n"
            f"Length: {length} blocks\n"
            f"Commands: {len(events)}")
        
        logging.info(f"Timeline schematic exported: {filepath} ({length} blocks)")
        return filepath

    except Exception as e:
        messagebox.showerror("Export Failed", str(e))
        logging.error(f"Export failed: {e}")
        return None


def add_command_block_entity(block_entities, z: int, command: str):
    be = Compound({
        "id": String("minecraft:command_block"),
        "Pos": IntArray([0, 0, z]),
        "Command": String(command.strip()),
        "auto": Byte(0),
        "conditionMet": Byte(0),
        "powered": Byte(0),
        "TrackOutput": Byte(1),
        "SuccessCount": Int(0),
        "UpdateLastExecution": Byte(1),
        "LastExecution": Long(0),
        "LastOutput": String(""),
        "CustomName": String("{\"text\":\"@\"}")
    })
    block_entities.append(be)