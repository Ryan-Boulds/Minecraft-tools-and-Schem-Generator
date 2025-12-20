# modify_laser_gui.py
# Fully fixed & working — November 30, 2025
# All variable names now match modifier.py perfectly

import tkinter as tk
from tkinter import ttk
import pyperclip
import re


def create_modify_laser_gui(frame, gui):
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    # Title
    tk.Label(scrollable_frame, text="Modify Laser", font=("Arial", 18, "bold"), fg="#2e7d32").grid(
        row=0, column=0, columnspan=4, pady=(10, 15), sticky="w", padx=10)

    # Input Command Box
    tk.Label(scrollable_frame, text="Input Command:", font=("Arial", 10, "bold")).grid(
        row=1, column=0, sticky="w", padx=10, pady=(10, 2))
    gui.modify_input_text = tk.Text(scrollable_frame, height=4, width=70, font=("Consolas", 10))
    gui.modify_input_text.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    tk.Button(scrollable_frame,
              text="Paste from Clipboard",
              command=lambda: gui.modify_input_text.insert("1.0", pyperclip.paste()),
              bg="#1976d2", fg="white").grid(row=2, column=3, padx=10, pady=5, sticky="e")

    # === VARIABLES — NOW MATCH modifier.py EXACTLY ===
    gui.modify_direction = tk.BooleanVar(value=True)        # Checkbox: apply direction offset
    gui.modify_move_to = tk.BooleanVar(value=False)         # Checkbox: use Move To coordinates
    gui.modify_laser_direction = tk.StringVar(value="North")  # Dropdown selection
    gui.modify_x = tk.StringVar()
    gui.modify_y = tk.StringVar()
    gui.modify_z = tk.StringVar()
    gui.modify_block = tk.BooleanVar(value=True)
    gui.modify_tag = tk.BooleanVar(value=True)
    gui.modify_block_text = tk.StringVar(value="minecraft:lime_concrete")
    gui.modify_tag_text = tk.StringVar(value="beam1")

    # Checkboxes
    tk.Checkbutton(scrollable_frame, text="Modify Direction",
                   variable=gui.modify_direction, font=("Arial", 10)).grid(
        row=3, column=0, columnspan=2, sticky="w", pady=8, padx=10)
    tk.Checkbutton(scrollable_frame, text="Move To X Y Z",
                   variable=gui.modify_move_to, font=("Arial", 10)).grid(
        row=3, column=2, columnspan=2, sticky="w", pady=8)

    # Direction Dropdown
    tk.Label(scrollable_frame, text="Direction:").grid(row=4, column=0, sticky="w", padx=10)
    ttk.Combobox(scrollable_frame, textvariable=gui.modify_laser_direction,
                 values=["North", "South", "East", "West"],
                 state="readonly", width=10).grid(row=4, column=1, sticky="w", padx=10)

    # Move To Coordinates
    tk.Label(scrollable_frame, text="Move To:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
    tk.Entry(scrollable_frame, textvariable=gui.modify_x, width=12).grid(row=5, column=1, padx=3, pady=5)
    tk.Entry(scrollable_frame, textvariable=gui.modify_y, width=12).grid(row=5, column=2, padx=3, pady=5)
    tk.Entry(scrollable_frame, textvariable=gui.modify_z, width=12).grid(row=5, column=3, padx=3, pady=5)

    # Copy Coords from Clipboard button
    tk.Button(scrollable_frame, text="Copy Coords from Clipboard", font=("Arial", 9),
              command=lambda: parse_coords_to_entries(gui)).grid(row=5, column=4, padx=10, sticky="w")

    # Block override
    tk.Label(scrollable_frame, text="Block:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
    tk.Checkbutton(scrollable_frame, text="", variable=gui.modify_block).grid(row=6, column=1, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.modify_block_text, width=30).grid(
        row=6, column=2, columnspan=2, sticky="w", padx=5)

    # Tag override
    tk.Label(scrollable_frame, text="Tag:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
    tk.Checkbutton(scrollable_frame, text="", variable=gui.modify_tag).grid(row=7, column=1, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.modify_tag_text, width=20).grid(row=7, column=2, sticky="w", padx=5)

    # MODIFY LASER BUTTON — NOW CALLS THE CORRECT METHOD
    tk.Button(scrollable_frame, text="MODIFY LASER",
              command=lambda: gui.process_command(gui.modify_input_text.get("1.0", tk.END).strip()),
              font=("Arial", 14, "bold"), bg="#2e7d32", fg="white", height=2).grid(
        row=8, column=0, columnspan=5, pady=25, sticky="ew", padx=50)

    # Output box
    tk.Label(scrollable_frame, text="Modified Command:", font=("Arial", 10, "bold")).grid(
        row=9, column=0, sticky="w", padx=10, pady=(10, 2))
    gui.modify_output_text = tk.Text(scrollable_frame, height=6, width=70,
                                    font=("Consolas", 10), bg="#f9f9f9")
    gui.modify_output_text.grid(row=10, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    tk.Button(scrollable_frame, text="Copy Output",
              command=lambda: gui.copy_to_clipboard(gui.modify_output_text.get("1.0", tk.END).strip()),
              bg="#4caf50", fg="white").grid(row=11, column=0, columnspan=5, pady=8)

    # Grid configuration
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(10, weight=1)


# Helper: Parse coordinates from clipboard and fill Move To fields
def parse_coords_to_entries(gui):
    try:
        text = pyperclip.paste().strip()
        match = re.search(r'(-?[\d\.]+)\s+(-?[\d\.]+)\s+(-?[\d\.]+)', text)
        if match:
            x, y, z = match.groups()
            gui.modify_x.set(x)
            gui.modify_y.set(y)
            gui.modify_z.set(z)
            if hasattr(gui, 'print_to_text'):
                gui.print_to_text(f"Coords loaded: {x} {y} {z}", "normal")
        else:
            if hasattr(gui, 'print_to_text'):
                gui.print_to_text("No valid coordinates found in clipboard", "normal")
    except Exception as e:
        if hasattr(gui, 'print_to_text'):
            gui.print_to_text(f"Failed to parse coordinates: {e}", "normal")