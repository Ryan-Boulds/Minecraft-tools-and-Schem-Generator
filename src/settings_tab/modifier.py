# Created on 12:25 PM CDT, Monday, September 01, 2025
import logging
import tkinter as tk
from settings import save_settings

def process_command(gui, command):
    logging.debug(f"Processing command in Settings tab: {command}")
    gui.print_to_text("No command processing in Settings tab.", "normal")
    return command

def apply_settings(gui):
    try:
        gui.settings["always_on_top"] = gui.always_on_top.get()
        gui.settings["key_bind"] = gui.key_bind.get()
        gui.settings["coord_format"] = gui.coord_format.get()
        save_settings(gui.settings)
        logging.debug("Settings applied and saved")
        gui.print_to_text("Settings applied and saved.", "normal")
    except Exception as e:
        logging.error(f"Error applying settings: {e}")
        gui.print_to_text("Error: Failed to apply settings.", "normal")