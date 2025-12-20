# Updated on 12:25 PM CDT, Monday, September 01, 2025
import logging
import logging.handlers
import pyperclip
import tkinter as tk
from tkinter import ttk
from modify_laser_tab.modifier import set_laser_preset, set_lightbeam_preset
from clipboard_parser import ClipboardCoordinateParser

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.handlers.RotatingFileHandler(
                'command_modifier.log',
                maxBytes=1000000,
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )
    logging.debug("Logging initialized")

def cleanup():
    for handler in logging.getLogger().handlers:
        handler.close()
        logging.getLogger().removeHandler(handler)
    logging.debug("Logging handlers cleaned up")

def adjust_offset(offset_var, change):
    try:
        current = float(offset_var.get())
        offset_var.set(str(current + change))
    except ValueError:
        offset_var.set(str(change))
    logging.debug(f"Adjusted offset: {offset_var.get()}")

def toggle_always_on_top(gui):
    gui.root.attributes('-topmost', gui.always_on_top.get())
    logging.debug(f"Always on top set to: {gui.always_on_top.get()}")

def start_record_keybind(gui):
    gui.is_recording_key = True
    gui.key_bind.set("Press a key...")
    gui.root.bind("<Key>", lambda event: gui.record_keybind(event))
    logging.debug("Started recording keybind")

def record_keybind(gui, event):
    if gui.is_recording_key:
        key = event.keysym
        if key:
            gui.key_bind.set(key)
            gui.root.unbind("<Key>")
            gui.is_recording_key = False
            gui.root.bind(key, lambda e: gui.process_clipboard())
            from settings import save_settings
            gui.settings["key_bind"] = key
            save_settings(gui.settings)
            logging.debug(f"Recorded keybind: {key}")

def process_clipboard(gui):
    try:
        active_tab = gui.notebook.tab(gui.notebook.select(), "text").lower()
        logging.debug(f"Processing clipboard for tab: {active_tab}")
        clipboard_content = pyperclip.paste().strip()

        if active_tab == "generate laser":
            try:
                coords = gui.clipboard_parser.parse_coordinates(clipboard_content)
                if coords:
                    gui.laser_x.set(str(float(coords[0])))
                    gui.laser_y.set(str(float(coords[1])))
                    gui.laser_z.set(str(float(coords[2])))
                    logging.debug(f"Autofilled laser coordinates: {coords}")
                else:
                    logging.warning("No valid coordinates found in clipboard")
            except Exception as e:
                logging.error(f"Error autofilling laser coordinates: {e}")
        elif active_tab == "generate end beam":
            try:
                coords = gui.clipboard_parser.parse_coordinates(clipboard_content)
                if coords:
                    gui.end_beam_x.set(str(float(coords[0])))
                    gui.end_beam_y.set(str(float(coords[1])))
                    gui.end_beam_z.set(str(float(coords[2])))
                    logging.debug(f"Autofilled end beam coordinates: {coords}")
                else:
                    logging.warning("No valid coordinates found in clipboard")
            except Exception as e:
                logging.error(f"Error autofilling end beam coordinates: {e}")
        else:
            gui.process_command(clipboard_content)

    except Exception as e:
        logging.error(f"Error processing clipboard: {e}")

def on_closing(gui):
    if not gui.is_destroyed:
        gui.is_destroyed = True
        from settings import save_settings
        save_settings(gui.settings)
        cleanup()
        gui.root.destroy()
        logging.debug("Application closed")

def show_window(gui):
    gui.root.deiconify()
    logging.debug("Window shown")

def copy_to_clipboard(gui, command):
    pyperclip.copy(command.encode('utf-8').decode('utf-8'))
    logging.debug("Command copied to clipboard.")