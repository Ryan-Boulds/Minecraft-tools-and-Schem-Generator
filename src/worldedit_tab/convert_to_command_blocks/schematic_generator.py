# worldedit_tab/convert_to_command_blocks/schematic_generator.py
import logging
from tkinter import filedialog

from nbtlib.tag import Compound, List, Int, Short, ByteArray, IntArray

from ..common.schem_io import save_schematic, make_command_block_entity


def generate_schematic(gui):
    """Generate a WorldEdit schematic file with a command block.
       Always anchors at 0,0,0 so //paste places directly at target."""
    try:
        # Get inputs
        block_type = gui.schematic_block.get().replace("__", ":") or "minecraft:command_block"
        width = int(gui.schematic_width.get()) if gui.schematic_width.get() else 1
        height = int(gui.schematic_height.get()) if gui.schematic_height.get() else 1
        length = int(gui.schematic_length.get()) if gui.schematic_length.get() else 1

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
                            make_command_block_entity((px, py, pz), command, custom_name="{\"text\":\"@\"}")
                        )

        schematic_data = Compound({
            "Version": Int(2),
            "DataVersion": Int(3578),
            "Width": Short(width),
            "Height": Short(height),
            "Length": Short(length),
            "PaletteMax": Int(1),
            "Palette": palette,
            "BlockData": block_data,
            "BlockEntities": block_entities,
            "Offset": IntArray([0, 0, 0]),
            "Metadata": Compound({
                "WEOffsetX": Int(0),
                "WEOffsetY": Int(0),
                "WEOffsetZ": Int(0)
            })
        })

        file_path = filedialog.asksaveasfilename(
            defaultextension=".schem",
            filetypes=[("Schematic files", "*.schem"), ("All files", "*.*")]
        )

        if file_path:
            save_schematic(schematic_data, file_path)
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
