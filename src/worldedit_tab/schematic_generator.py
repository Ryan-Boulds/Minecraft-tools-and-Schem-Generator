# Updated on 08:31 PM CDT, Friday, September 19, 2025
import logging
import nbtlib
from nbtlib.tag import Compound, List, Byte, Int, Long, Short, ByteArray, String, IntArray
from tkinter import filedialog
import gzip

def generate_schematic(gui):
    """Generate a WorldEdit schematic file with a command block."""
    try:
        # Get inputs
        block_type = gui.schematic_block.get().replace("__", ":") or "minecraft:command_block"
        width = int(gui.schematic_width.get()) if gui.schematic_width.get() else 1
        height = int(gui.schematic_height.get()) if gui.schematic_height.get() else 1
        length = int(gui.schematic_length.get()) if gui.schematic_length.get() else 1
        x = int(float(gui.schematic_x.get() or "0"))
        y = int(float(gui.schematic_y.get() or "0"))
        z = int(float(gui.schematic_z.get() or "0"))
        command = gui.schematic_command.get() or "say Hello from command block"

        # Validate inputs
        if width < 1 or height < 1 or length < 1:
            raise ValueError("Dimensions must be positive integers.")

        # Create block palette with proper block state and index 0
        palette_key = block_type if '[' in block_type else f"{block_type}[conditional=false,facing=up]"
        palette = Compound({
            palette_key: Int(0)
        })

        # Block data: all blocks use index 0 (fixed to match dimensions)
        block_data = ByteArray([0] * (width * height * length))

        # Create command block entities if applicable (replicate for all positions with same command)
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

        # Create schematic data
        schematic_data = Compound({
            "Version": Int(2),
            "DataVersion": Int(4550),  # Updated to latest (Minecraft 1.21.9 Pre-Release 2 as of Sep 19, 2025)
            "Width": Short(width),
            "Height": Short(height),
            "Length": Short(length),
            "PaletteMax": Int(1),
            "Palette": palette,
            "BlockData": block_data,
            "BlockEntities": block_entities,
            "Offset": IntArray([x, y, z]),  # Use origin inputs
            "Metadata": Compound({
                "WEOffsetX": Int(x),
                "WEOffsetY": Int(y),
                "WEOffsetZ": Int(z)
            })
        })

        # Use nbtlib.File for schematic
        schematic = nbtlib.File(schematic_data)

        # Prompt user to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".schem",
            filetypes=[("Schematic files", "*.schem"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'wb') as f:
                with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                    schematic.write(gz)  # Write NBT data directly to GZIP file
            gui.print_to_text(f"Schematic saved to {file_path}", "normal")
            logging.debug(f"Schematic saved to {file_path}")
            return file_path
        else:
            gui.print_to_text("Schematic save cancelled.", "normal")
            logging.debug("Schematic save cancelled")
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
    """Generate a schematic from a clipboard command (e.g., set a single command block)."""
    gui.schematic_block.set("minecraft:command_block")
    gui.schematic_width.set("1")
    gui.schematic_height.set("1")
    gui.schematic_length.set("1")
    gui.schematic_x.set("0")
    gui.schematic_y.set("0")
    gui.schematic_z.set("0")
    gui.schematic_command.set(command)
    return generate_schematic(gui)