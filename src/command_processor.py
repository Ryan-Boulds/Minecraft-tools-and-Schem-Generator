# command_processor.py
# Updated on September 20, 2025
import logging
import re
import pyperclip
import keyboard
import tkinter as tk
from typing import Tuple, List, Optional

class CommandProcessor:
    def __init__(self):
        self.gui = None
        self.setup_keyboard_hook()

    def setup_keyboard_hook(self):
        keyboard.add_hotkey('F12', self.on_f12_press)
        logging.info("F12 keyboard hook initialized")

    def on_f12_press(self):
        logging.info("F12 pressed - capturing clipboard command")
        command = pyperclip.paste().strip()
        if command:
            if self.gui is not None:
                # Update original command text box if in Set Coordinates tab
                if self.gui.notebook.tab(self.gui.notebook.select(), "text") == "Set Coordinates":
                    if hasattr(self.gui, 'original_cmd_text') and self.gui.original_cmd_text.winfo_exists():
                        self.gui.original_cmd_text.delete("1.0", tk.END)
                        self.gui.original_cmd_text.insert("1.0", command)
                self.gui.process_command(command)
            else:
                logging.error("GUI not set for command processing")
        else:
            if self.gui is not None:
                self.gui.print_to_text("", "normal")
                self.gui.print_to_text("Input Command:", "normal")
                self.gui.print_to_text("Clipboard is empty or invalid. Copy a command before pressing F12.", "normal")
                self.gui.print_to_text("", "normal")
            else:
                logging.error("GUI not set, cannot display clipboard error")

    def set_gui(self, gui):
        self.gui = gui

    def get_offsets(self, pos_x_offset: tk.StringVar, pos_y_offset: tk.StringVar, pos_z_offset: tk.StringVar,
                    target_x_offset: tk.StringVar, target_y_offset: tk.StringVar, target_z_offset: tk.StringVar) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        try:
            pos_offsets = (
                float(pos_x_offset.get()),
                float(pos_y_offset.get()),
                float(pos_z_offset.get())
            )
            target_offsets = (
                float(target_x_offset.get()),
                float(target_y_offset.get()),
                float(target_z_offset.get())
            )
            return pos_offsets, target_offsets
        except ValueError:
            logging.warning("Invalid offset values entered, using 0.0")
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)

    def get_set_values(self, pos_x_set: tk.StringVar, pos_y_set: tk.StringVar, pos_z_set: tk.StringVar,
                       target_x_set: tk.StringVar, target_y_set: tk.StringVar, target_z_set: tk.StringVar) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        try:
            pos_set = (
                float(pos_x_set.get()),
                float(pos_y_set.get()),
                float(pos_z_set.get())
            )
            target_set = (
                float(target_x_set.get()),
                float(target_y_set.get()),
                float(target_z_set.get())
            )
            return pos_set, target_set
        except ValueError:
            logging.warning("Invalid set values entered, using 0.0")
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)

    def modify_coordinates(self, command: str, use_set: bool, pos_x_var: tk.StringVar, pos_y_var: tk.StringVar, pos_z_var: tk.StringVar,
                           target_x_var: tk.StringVar, target_y_var: tk.StringVar, target_z_var: tk.StringVar,
                           block_text: tk.StringVar) -> Tuple[str, List[float], Optional[str]]:
        logging.debug(f"Modifying coordinates for command: {command}")
        if use_set:
            pos_values, target_values = self.get_set_values(pos_x_var, pos_y_var, pos_z_var, target_x_var, target_y_var, target_z_var)
        else:
            pos_offsets, target_offsets = self.get_offsets(pos_x_var, pos_y_var, pos_z_var, target_x_var, target_y_var, target_z_var)

        original_coords = [float(x) for x in re.findall(r'-?\d+\.?\d*', command) if x.replace('-', '').replace('.', '').isdigit()]
        original_block = None
        block_match = re.search(r'(?:setblock\s+-?\d+\.?\d*\s+-?\d+\.?\d*\s+-?\d+\.?\d*\s+)(minecraft:\w+|\w+)', command)
        if block_match:
            original_block = block_match.group(1)

        summon_pattern = re.compile(r'(summon end_crystal\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*?(?:BeamTarget:\{|\],\{).*?X:)(-?\d+|\~)(.*?Y:)(-?\d+|\~)(.*?Z:)(-?\d+|\~)(.*?\}\})')
        summon_match = summon_pattern.search(command)
        if summon_match:
            logging.debug(f"Summon match groups: {summon_match.groups()}")
            x1 = pos_values[0] if use_set else float(summon_match.group(2)) + pos_offsets[0]
            y1 = pos_values[1] if use_set else float(summon_match.group(4)) + pos_offsets[1]
            z1 = pos_values[2] if use_set else float(summon_match.group(6)) + pos_offsets[2]
            x2 = target_values[0] if use_set else float(summon_match.group(8)) + target_offsets[0]
            y2 = target_values[1] if use_set else float(summon_match.group(10)) + target_offsets[1]
            z2 = target_values[2] if use_set else float(summon_match.group(12)) + target_offsets[2]
            result = f"{summon_match.group(1)}{x1:.6f}{summon_match.group(3)}{y1:.6f}{summon_match.group(5)}{z1:.6f}{summon_match.group(7)}{int(x2):d}{summon_match.group(9)}{int(y2):d}{summon_match.group(11)}{int(z2):d}{summon_match.group(13)}"
            logging.debug(f"Summon command modified: {result}")
            return result, original_coords, None

        setblock_pattern = re.compile(r'(setblock\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*)')
        setblock_match = setblock_pattern.search(command)
        if setblock_match:
            logging.debug(f"Setblock match groups: {setblock_match.groups()}")
            x = pos_values[0] if use_set else float(setblock_match.group(2)) + pos_offsets[0]
            y = pos_values[1] if use_set else float(setblock_match.group(4)) + pos_offsets[1]
            z = pos_values[2] if use_set else float(setblock_match.group(6)) + pos_offsets[2]
            original_block_text = setblock_match.group(8).strip()
            new_block_text = block_text.get().strip() if self.gui and self.gui.notebook.tab(self.gui.notebook.select(), "text") == "Change Block" else original_block_text
            result = f"/setblock {x:.6f} {y:.6f} {z:.6f} {new_block_text}"
            logging.debug(f"Setblock command modified: {result}")
            return result, original_coords, original_block_text

        kill_pattern = re.compile(r'(kill @e\[[^]]*x=)(-?\d+\.?\d*|\~)([^,]*,\s*y=)(-?\d+\.?\d*|\~)([^,]*,\s*z=)(-?\d+\.?\d*|\~)([^]]*\])')
        kill_match = kill_pattern.search(command)
        if kill_match:
            logging.debug(f"Kill match groups: {kill_match.groups()}")
            x = pos_values[0] if use_set else float(kill_match.group(2)) + pos_offsets[0]
            y = pos_values[1] if use_set else float(kill_match.group(4)) + pos_offsets[1]
            z = pos_values[2] if use_set else float(kill_match.group(6)) + pos_offsets[2]
            result = f"{kill_match.group(1)}{x:.6f}{kill_match.group(3)}{y:.6f}{kill_match.group(5)}{z:.6f}{kill_match.group(7)}"
            logging.debug(f"Kill command modified: {result}")
            return result, original_coords, None

        summon_block_pattern = re.compile(r'(summon\s+[^\s]+\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(\s+)(-?\d+\.?\d*|\~\.?~?)(.*)')
        summon_block_match = summon_block_pattern.search(command)
        if summon_block_match:
            logging.debug(f"Summon block display match groups: {summon_block_match.groups()}")
            x = pos_values[0] if use_set else float(summon_block_match.group(2)) + pos_offsets[0]
            y = pos_values[1] if use_set else float(summon_block_match.group(4)) + pos_offsets[1]
            z = pos_values[2] if use_set else float(summon_block_match.group(6)) + pos_offsets[2]
            result = f"{summon_block_match.group(1)}{x:.6f}{summon_block_match.group(3)}{y:.6f}{summon_block_match.group(5)}{z:.6f}{summon_block_match.group(7)}"
            logging.debug(f"Summon block command modified: {result}")
            return result, original_coords, None

        logging.debug("No modification applied")
        return command, original_coords, None