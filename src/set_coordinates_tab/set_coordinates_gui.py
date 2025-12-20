# set_coordinates_gui.py
# Updated on September 20, 2025
import tkinter as tk
from tkinter import ttk
import pyperclip
from gui_utils import adjust_offset
from .modifier import process_command  # Import process_command for direct use

def create_set_coordinates_gui(frame, gui):
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    tk.Label(scrollable_frame, text="Set Coordinates", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=6, pady=5, sticky="w")

    # Position section
    tk.Label(scrollable_frame, text="Position:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=1, column=0, columnspan=6, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.pos_vars[0]), ("Y:", gui.pos_vars[1]), ("Z:", gui.pos_vars[2])]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+2, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+2, column=1, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▲", command=lambda v=var, c=1: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+2, column=2, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▼", command=lambda v=var, c=-1: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+2, column=3, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▲10", command=lambda v=var, c=10: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+2, column=4, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▼10", command=lambda v=var, c=-10: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+2, column=5, pady=2, sticky="w")

    # Target section
    tk.Label(scrollable_frame, text="Target (for applicable commands like end_crystal):", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=5, column=0, columnspan=6, pady=10, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.target_vars[0]), ("Y:", gui.target_vars[1]), ("Z:", gui.target_vars[2])]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+6, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+6, column=1, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▲", command=lambda v=var, c=1: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+6, column=2, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▼", command=lambda v=var, c=-1: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+6, column=3, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▲10", command=lambda v=var, c=10: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+6, column=4, pady=2, sticky="w")
        tk.Button(scrollable_frame, text="▼10", command=lambda v=var, c=-10: adjust_offset(v, c), font=("Arial", 8)).grid(row=i+6, column=5, pady=2, sticky="w")

    # Autofill buttons
    tk.Button(scrollable_frame, text="Autofill from Clipboard", command=lambda: gui.clipboard_parser.autofill_coordinates(gui.pos_vars + gui.target_vars), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=9, column=0, columnspan=6, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Autofill Integers from Clipboard", command=lambda: gui.clipboard_parser.autofill_integer_coordinates(gui.pos_vars + gui.target_vars), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=10, column=0, columnspan=6, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Autofill Fractionals from Clipboard", command=lambda: gui.clipboard_parser.autofill_fractional_coordinates(gui.pos_vars + gui.target_vars), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=11, column=0, columnspan=6, pady=2, sticky="w")

    # Original Command input section
    tk.Label(scrollable_frame, text="Original Command:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=12, column=0, columnspan=6, pady=10, sticky="w")
    gui.original_cmd_text = tk.Text(scrollable_frame, height=4, width=60)
    gui.original_cmd_text.grid(row=13, column=0, columnspan=3, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Paste from Clipboard", command=lambda: gui.original_cmd_text.insert("1.0", pyperclip.paste()), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=13, column=3, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Generate Updated Command", command=lambda: process_command(gui, gui.original_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=13, column=4, columnspan=2, pady=2, sticky="w")

    # Updated Command output section
    tk.Label(scrollable_frame, text="Updated Command:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=14, column=0, columnspan=6, pady=10, sticky="w")
    gui.cmd_text_set = tk.Text(scrollable_frame, height=4, width=60)
    gui.cmd_text_set.grid(row=15, column=0, columnspan=3, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.cmd_text_set.get("1.0", tk.END).strip()), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=15, column=3, pady=2, sticky="w")