# modifier.py
# Updated on September 20, 2025
import logging
import re
import tkinter as tk
import pyperclip
from typing import Tuple, List, Optional

def get_set_values(x_var: tk.StringVar, y_var: tk.StringVar, z_var: tk.StringVar) -> Tuple[float, float, float]:
    try:
        return (
            float(x_var.get()),
            float(y_var.get()),
            float(z_var.get())
        )
    except ValueError:
        logging.warning("Invalid set values entered, using 0.0")
        return (0.0, 0.0, 0.0)

def modify_coordinates(command: str, pos_x_var: tk.StringVar, pos_y_var: tk.StringVar, pos_z_var: tk.StringVar,
                       target_x_var: tk.StringVar, target_y_var: tk.StringVar, target_z_var: tk.StringVar) -> Tuple[str, Optional[List[str]], Optional[List[str]]]:
    logging.debug(f"Modifying coordinates for command: {command}")
    pos_values = get_set_values(pos_x_var, pos_y_var, pos_z_var)
    target_values = get_set_values(target_x_var, target_y_var, target_z_var)

    if not command.startswith('/'):
        command = '/' + command

    modified_command = command
    original_pos = None
    original_target = None

    # Handle /summon end_crystal (with BeamTarget)
    summon_end_pattern = re.compile(r'(/summon end_crystal\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*?(?:BeamTarget:\{|\],\{).*?X:)(-?\d+|\~)(.*?Y:)(-?\d+|\~)(.*?Z:)(-?\d+|\~)(.*?\}\})')
    match = summon_end_pattern.search(command)
    if match:
        original_pos = [match.group(2), match.group(4), match.group(6)]
        original_target = [match.group(8), match.group(10), match.group(12)]
        x1, y1, z1 = pos_values
        x2, y2, z2 = target_values
        modified_command = f"{match.group(1)}{x1:.6f}{match.group(3)}{y1:.6f}{match.group(5)}{z1:.6f}{match.group(7)}{int(x2)}{match.group(9)}{int(y2)}{match.group(11)}{int(z2)}{match.group(13)}"
        return modified_command, original_pos, original_target

    # Handle general /summon (e.g., block_display)
    summon_pattern = re.compile(r'(/summon\s+[^\s]+\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*)')
    match = summon_pattern.search(command)
    if match:
        original_pos = [match.group(2), match.group(4), match.group(6)]
        x, y, z = pos_values
        modified_command = f"{match.group(1)}{x:.6f}{match.group(3)}{y:.6f}{match.group(5)}{z:.6f}{match.group(7)}"
        return modified_command, original_pos, None

    # Handle /setblock
    setblock_pattern = re.compile(r'(/setblock\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*)')
    match = setblock_pattern.search(command)
    if match:
        original_pos = [match.group(2), match.group(4), match.group(6)]
        x, y, z = pos_values
        modified_command = f"{match.group(1)}{x:.6f}{match.group(3)}{y:.6f}{match.group(5)}{z:.6f}{match.group(7)}"
        return modified_command, original_pos, None

    # Optional: Handle /kill @e[x=...,y=...,z=...]
    kill_pattern = re.compile(r'(/kill @e\[[^]]*x=)(-?\d+\.?\d*|\~)([^,]*,\s*y=)(-?\d+\.?\d*|\~)([^,]*,\s*z=)(-?\d+\.?\d*|\~)([^]]*\])')
    match = kill_pattern.search(command)
    if match:
        original_pos = [match.group(2), match.group(4), match.group(6)]
        x, y, z = pos_values
        modified_command = f"{match.group(1)}{x:.6f}{match.group(3)}{y:.6f}{match.group(5)}{z:.6f}{match.group(7)}"
        return modified_command, original_pos, None

    logging.debug("No supported command found for modification")
    return command, None, None

def process_command(gui, command):
    logging.debug(f"Processing command in Set Coordinates tab: {command}")
    modified_command, original_pos, original_target = modify_coordinates(
        command, gui.pos_vars[0], gui.pos_vars[1], gui.pos_vars[2],
        gui.target_vars[0], gui.target_vars[1], gui.target_vars[2]
    )
    if original_pos is None:
        gui.print_to_text("Warning: No supported command found with coordinates to set.", "normal")
        return command

    gui.print_to_text(f"Original Position: {original_pos}", "coord")
    if original_target:
        gui.print_to_text(f"Original Target: {original_target}", "coord")

    # Extract new coords for printing (optional, since we know the values)
    new_pos_match = re.search(r'\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', modified_command)
    if new_pos_match:
        new_pos = [new_pos_match.group(1), new_pos_match.group(2), new_pos_match.group(3)]
        gui.print_to_text(f"New Position: {new_pos}", "modified_coord")

    if original_target:
        new_target_match = re.search(r'X:(-?\d+).*?Y:(-?\d+).*?Z:(-?\d+)', modified_command)
        if new_target_match:
            new_target = [new_target_match.group(1), new_target_match.group(2), new_target_match.group(3)]
            gui.print_to_text(f"New Target: {new_target}", "modified_coord")

    if hasattr(gui, 'cmd_text_set') and gui.cmd_text_set.winfo_exists():
        gui.cmd_text_set.delete("1.0", tk.END)
        gui.cmd_text_set.insert("1.0", modified_command)
    else:
        logging.warning("cmd_text_set not found or not initialized")
        gui.print_to_text("Warning: cmd_text_set not found or not initialized", "normal")

    pyperclip.copy(modified_command)
    gui.print_to_text("Modified command copied to clipboard.", "normal")
    return modified_command