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

        # Direction-specific offsets and transformations
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

        def clean(num):
            if abs(num - int(num)) < 1e-6:
                return str(int(num))
            return f"{num:.2f}".rstrip("0").rstrip(".")

        command = (
            f"/summon minecraft:block_display {clean(x)} {clean(y)} {clean(z)} "
            f"{{block_state:{{Name:\"{block}\"}},"
            f"transformation:{{translation:{translation},"
            f"scale:{scale},"
            f"left_rotation:{left_rotation},"
            f"right_rotation:[0f,0f,0f,1f]}},"
            f"brightness:15728880,shadow:false,billboard:\"fixed\",Tags:[\"{tag}\"]}}"
        )

        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", command)

        pyperclip.copy(command)
        return command
    except ValueError as e:
        logging.error(f"Error generating laser command: {e}")
        return ""

def generate_kill_laser_command(gui):
    try:
        tag = gui.laser_tag.get() or "beam1"
        command = f"/kill @e[tag={tag}]"
        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", command)
        pyperclip.copy(command)
        return command
    except Exception as e:
        logging.error(f"Error: {e}")
        return ""

def generate_rotate_command(gui, direction):
    try:
        tag = gui.laser_tag.get() or "beam1"
        # Map directions to relative rotation values
        # tp @s ~ ~ ~ [yaw] [pitch]
        rot_map = {
            "left": "~1 ~",
            "right": "~-1 ~",
            "up": "~ ~-1",
            "down": "~ ~1"
        }
        rot_val = rot_map.get(direction, "~ ~")
        command = f"execute as @e[tag={tag}] at @s run tp @s ~ ~ ~ {rot_val}"

        if hasattr(gui, 'laser_cmd_text') and gui.laser_cmd_text.winfo_exists():
            gui.laser_cmd_text.delete("1.0", tk.END)
            gui.laser_cmd_text.insert("1.0", command)

        pyperclip.copy(command)
        return command
    except Exception as e:
        logging.error(f"Error generating rotation: {e}")
        return ""

def parse_clipboard_coordinates(gui):
    try:
        clipboard_content = pyperclip.paste().strip()
        match = re.match(r'^(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)$', clipboard_content)
        if match:
            x, y, z = map(float, match.groups())
            gui.laser_x.set(str(x))
            gui.laser_y.set(str(y))
            gui.laser_z.set(str(z))
    except Exception as e:
        logging.error(f"Error: {e}")

def process_command(gui, command):
    return generate_laser_commands(gui)