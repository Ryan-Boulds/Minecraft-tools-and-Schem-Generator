# Updated origin handling — FIXED PASTE OFFSET
# Updated February 28, 2026

import logging
import nbtlib
from nbtlib.tag import Compound, List, Byte, Int, Long, Short, ByteArray, String, IntArray
from tkinter import filedialog
import gzip


def generate_schematic(gui):
    """Generate a WorldEdit schematic file with a command block.
       Always anchors at 0,0,0 so //paste places directly at target."""
    try:
        # Get inputs
        block_type = gui.schematic_block.get().replace("__", ":") or "minecraft:command_block"
        width = int(gui.schematic_width.get()) if gui.schematic_width.get() else 1
        height = int(gui.schematic_height.get()) if gui.schematic_height.get() else 1
        length = int(gui.schematic_length.get()) if gui.schematic_length.get() else 1

        # These are ONLY for command text — not structure placement
        player_x = int(float(gui.schematic_x.get() or "0"))
        player_y = int(float(gui.schematic_y.get() or "0"))
        player_z = int(float(gui.schematic_z.get() or "0"))

        command = gui.schematic_command.get() or "say Hello from command block"

        if width < 1 or height < 1 or length < 1:
            raise ValueError("Dimensions must be positive integers.")

        # Ensure facing default exists
        palette_key = block_type if '[' in block_type else f"{block_type}[conditional=false,facing=up]"

        palette = Compound({
            palette_key: Int(0)
        })

        # Structure is EXACTLY width × height × length
        block_data = ByteArray([0] * (width * height * length))

        block_entities = List[Compound]()

        if "command_block" in block_type:
            for py in range(height):
                for pz in range(length):
                    for px in range(width):
                        block_entities.append(
                            Compound({
                                "id": String("minecraft:command_block"),
                                "Pos": IntArray([px, py, pz]),
                                "Command": String(command),
                                "CustomName": String("{\"text\":\"@\"}"),
                                "auto": Byte(0),
                                "conditionMet": Byte(0),
                                "powered": Byte(0),
                                "TrackOutput": Byte(1),
                                "SuccessCount": Int(0),
                                "UpdateLastExecution": Byte(1),
                                "LastExecution": Long(0),
                                "LastOutput": String("")
                            })
                        )

        schematic_data = Compound({
            "Version": Int(2),
            "DataVersion": Int(4550),
            "Width": Short(width),
            "Height": Short(height),
            "Length": Short(length),
            "PaletteMax": Int(1),
            "Palette": palette,
            "BlockData": block_data,
            "BlockEntities": block_entities,

            # 🔥 CRITICAL FIX — ORIGIN IS ALWAYS ZERO
            "Offset": IntArray([0, 0, 0]),

            "Metadata": Compound({
                "WEOffsetX": Int(0),
                "WEOffsetY": Int(0),
                "WEOffsetZ": Int(0)
            })
        })

        schematic = nbtlib.File(schematic_data)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".schem",
            filetypes=[("Schematic files", "*.schem"), ("All files", "*.*")]
        )

        if file_path:
            with open(file_path, 'wb') as f:
                with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                    schematic.write(gz)

            gui.print_to_text(f"Schematic saved to {file_path}", "normal")
            logging.debug(f"Schematic saved to {file_path}")
            return file_path
        else:
            gui.print_to_text("Schematic save cancelled.", "normal")
            return None

    except ValueError as e:
        gui.print_to_text(f"Error: {str(e)}", "normal")
        logging.error(f"Error generating schematic: {e}")
        return None

    except Exception as e:
        gui.print_to_text(f"Error saving schematic: {str(e)}", "normal")
        logging.error(f"Error saving schematic: {e}")
        return None


def generate_schematic_from_command(gui, command):
    gui.schematic_block.set("minecraft:command_block")
    gui.schematic_width.set("1")
    gui.schematic_height.set("1")
    gui.schematic_length.set("1")
    gui.schematic_x.set("0")
    gui.schematic_y.set("0")
    gui.schematic_z.set("0")
    gui.schematic_command.set(command)
    return generate_schematic(gui)