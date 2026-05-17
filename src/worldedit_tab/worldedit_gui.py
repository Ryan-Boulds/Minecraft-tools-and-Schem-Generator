# worldedit_tab/worldedit_gui.py
import tkinter as tk
from tkinter import ttk

from .command_block_generator.gui import create_converter_subframe


def create_worldedit_schematic_gui(frame, gui):
    """WorldEdit Schematic Tab - Now ONLY the Schem → Command Blocks Converter"""
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    # Directly load the converter (no old generator UI)
    converter_frame = create_converter_subframe(scrollable_frame, gui, lambda: None)
    converter_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)