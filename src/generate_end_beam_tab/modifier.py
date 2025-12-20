import logging
import pyperclip
import tkinter as tk
import re

def parse_clipboard_coordinates(gui, position="origin"):
    try:
        clipboard_content = pyperclip.paste().strip()
        # Match coordinates in the format "X Y Z" (e.g., "0 0 0" or "-2 111 4")
        match = re.match(r'^(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)$', clipboard_content)
        if match:
            x, y, z = map(float, match.groups())
            if position == "origin":
                gui.end_beam_x.set(str(x))
                gui.end_beam_y.set(str(y))
                gui.end_beam_z.set(str(z))
            elif position == "target":
                gui.end_beam_target_x.set(str(x))
                gui.end_beam_target_y.set(str(y))
                gui.end_beam_target_z.set(str(z))
            logging.debug(f"Autofilled {position} coordinates from clipboard: {x}, {y}, {z}")
            if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
                gui.end_beam_cmd_text.delete("1.0", tk.END)
                gui.end_beam_cmd_text.insert("1.0", f"{position.capitalize()} coordinates loaded: {x}, {y}, {z}")
        else:
            logging.warning("Invalid clipboard format for coordinates")
            if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
                gui.end_beam_cmd_text.delete("1.0", tk.END)
                gui.end_beam_cmd_text.insert("1.0", "Error: Invalid clipboard format. Use 'X Y Z' (e.g., '0 0 0').")
    except Exception as e:
        logging.error(f"Error parsing clipboard coordinates: {e}")
        if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
            gui.end_beam_cmd_text.delete("1.0", tk.END)
            gui.end_beam_cmd_text.insert("1.0", "Error: Failed to parse clipboard coordinates.")

def generate_end_beam_commands(gui):
    try:
        ox = float(gui.end_beam_x.get() or "0")
        oy = float(gui.end_beam_y.get() or "0")
        oz = float(gui.end_beam_z.get() or "0")
        tx = float(gui.end_beam_target_x.get() or "0")
        ty = float(gui.end_beam_target_y.get() or "0")
        tz = float(gui.end_beam_target_z.get() or "0")
        tag = gui.end_beam_tag.get() or "laser"

        command = (
            f"summon end_crystal {ox:.6f} {oy:.6f} {oz:.6f} "
            f"{{ShowBottom:0b,Invulnerable:1b,Tags:[\"{tag}\"],BeamTarget:{{X:{int(tx):d},Y:{int(ty):d},Z:{int(tz):d}}}}}"
        )

        if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
            gui.end_beam_cmd_text.delete("1.0", tk.END)
            gui.end_beam_cmd_text.insert("1.0", command)
        else:
            logging.warning("end_beam_cmd_text not found or not initialized")

        pyperclip.copy(command.encode('utf-8').decode('utf-8'))
        logging.debug("Command copied to clipboard.")
        logging.debug(f"Generated End Beam Command: {command}")
        return command
    except ValueError as e:
        logging.error(f"Error generating end beam command: {e}")
        if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
            gui.end_beam_cmd_text.delete("1.0", tk.END)
            gui.end_beam_cmd_text.insert("1.0", "Error: Please enter valid numbers for origin and target coordinates.")
        return ""

def generate_kill_end_beam_command(gui):
    try:
        tag = gui.end_beam_tag.get() or "laser"
        command = f"/kill @e[tag={tag}]"

        if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
            gui.end_beam_cmd_text.delete("1.0", tk.END)
            gui.end_beam_cmd_text.insert("1.0", command)
        else:
            logging.warning("end_beam_cmd_text not found or not initialized")

        pyperclip.copy(command.encode('utf-8').decode('utf-8'))
        logging.debug("Kill command copied to clipboard.")
        logging.debug(f"Generated Kill End Beam Command: {command}")
        return command
    except Exception as e:
        logging.error(f"Error generating kill end beam command: {e}")
        if hasattr(gui, 'end_beam_cmd_text') and gui.end_beam_cmd_text.winfo_exists():
            gui.end_beam_cmd_text.delete("1.0", tk.END)
            gui.end_beam_cmd_text.insert("1.0", "Error: Failed to generate kill command.")
        return ""

def process_command(gui, command):
    return generate_end_beam_commands(gui)