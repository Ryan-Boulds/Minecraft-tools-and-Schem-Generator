# timeline_exporter/gui_integration.py
import logging
from .exporter import generate_timeline_schematic


def export_timeline_to_schematic(app):
    """Called from the GUI button"""
    try:
        logging.info("Starting timeline schematic export...")
        generate_timeline_schematic(app)
    except Exception as e:
        logging.error(f"Export integration error: {e}")
        from tkinter import messagebox
        messagebox.showerror("Export Failed", str(e))