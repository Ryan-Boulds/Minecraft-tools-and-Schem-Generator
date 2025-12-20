import logging
import pyperclip
import tkinter as tk
import re

def generate_laser_commands(gui):
    try:
        base_x = float(gui.laser_x.get() or "0")
        base_y = float(gui.laser_y.get() or "0")
        base_z = float(gui.laser_z.get() or "0")
        block = gui.laser_block.get() or "minecraft:lime_concrete"
        tag = gui.laser_tag.get() or "beam1"
        direction = gui.laser_direction.get() if hasattr(gui, 'laser_direction') else "North"

        # Direction-specific offsets and transformations (with f suffixes)
        if direction == "North":
            x, y, z = base_x - 0.08, base_y + 0.42, base_z - 0.01
            translation = "[0.5f,0.0f,0f]"
            scale = "[0.1f,0.1f,-150f]"
        elif direction == "South":
            x, y, z = base_x - 0.02, base_y + 0.42, base_z + 1.01
            translation = "[0.5f,0.0f,0f]"
            scale = "[0.1f,0.1f,150f]"
        elif direction == "East":
            x, y, z = base_x, base_y + 0.42, base_z + 0.42
            translation = "[0.5f,0.0f,0f]"
            scale = "[150f,0.1f,0.1f]"
        elif direction == "West":
            x, y, z = base_x - 1.0, base_y + 0.42, base_z + 0.48
            translation = "[0.5f,0.0f,0f]"
            scale = "[-150f,0.1f,0.1f]"
        else:
            x, y, z = base_x - 0.08, base_y + 0.42, base_z - 0.01
            translation = "[0.5f,0.0f,0f]"
            scale = "[0.1f,0.1f,-150f]"

        # Helper to remove .00 if not needed
        def clean(num):
            if abs(num - int(num)) < 1e-6:
                return str(int(num))
            return f"{num:.2f}".rstrip("0").rstrip(".")

        command = (
            f"/summon minecraft:block_display {clean(x)} {clean(y)} {clean(z)} "
            f"{{block_state:{{Name:\"{block}\"}},"
            f"transformation:{{translation:{translation},"
            f"scale:{scale},"
            f"left_rotation:[0f,0f,0f,1f],"
            f"right_rotation:[0f,0f,0f,1f]}},"
            f"brightness:15728880,shadow:false,billboard:\"fixed\",Tags:[\"{tag}\"]}}"
        )

        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", command)

        pyperclip.copy(command)
        logging.debug(f"Generated Laser Command ({direction}): {command}")
        return command

    except ValueError as e:
        logging.error(f"Error generating laser command: {e}")
        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", "Error: Please enter valid numbers for coordinates.")
        return ""




def generate_kill_laser_command(gui):
    try:
        tag = gui.laser_tag.get() or "beam1"
        command = f"/kill @e[tag={tag}]"

        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", command)
        else:
            logging.warning("laser_cmd_text not found or not initialized")

        pyperclip.copy(command.encode('utf-8').decode('utf-8'))
        logging.debug("Kill command copied to clipboard.")
        logging.debug(f"Generated Kill Command: {command}")
        return command
    except Exception as e:
        logging.error(f"Error generating kill command: {e}")
        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", "Error: Failed to generate kill command.")
        return ""

def parse_clipboard_coordinates(gui):
    try:
        clipboard_content = pyperclip.paste().strip()
        # Match coordinates in the format "X Y Z" (e.g., "0 0 0" or "-2 101 4")
        match = re.match(r'^(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)$', clipboard_content)
        if match:
            x, y, z = map(float, match.groups())
            gui.laser_x.set(str(x))
            gui.laser_y.set(str(y))
            gui.laser_z.set(str(z))
            logging.debug(f"Autofilled coordinates from clipboard: {x}, {y}, {z}")
            if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
                gui.laser_cmd_text.delete("1.0", tk.END)
                gui.laser_cmd_text.insert("1.0", f"Coordinates loaded: {x}, {y}, {z}")
        else:
            logging.warning("Invalid clipboard format for coordinates")
            if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
                gui.laser_cmd_text.delete("1.0", tk.END)
                gui.laser_cmd_text.insert("1.0", "Error: Invalid clipboard format. Use 'X Y Z' (e.g., '0 0 0').")
    except Exception as e:
        logging.error(f"Error parsing clipboard coordinates: {e}")
        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", "Error: Failed to parse clipboard coordinates.")

def process_command(gui, command):
    return generate_laser_commands(gui)