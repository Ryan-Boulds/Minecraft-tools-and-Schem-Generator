import tkinter as tk
from tkinter import ttk
from .modifier import generate_laser_commands, generate_kill_laser_command, parse_clipboard_coordinates, generate_rotate_command

def create_generate_laser_gui(frame, gui):
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

    # Header
    tk.Label(scrollable_frame, text="Generate Laser", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")

    # Coordinates
    tk.Label(scrollable_frame, text="Base Position:", font=("Arial", 12, "bold"), bg='#f0f0f0').grid(row=1, column=0, columnspan=3, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.laser_x), ("Y:", gui.laser_y), ("Z:", gui.laser_z)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+2, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10).grid(row=i+2, column=1, pady=2, sticky="w")

    # Direction & Block
    tk.Label(scrollable_frame, text="Direction:", font=("Arial", 10)).grid(row=5, column=0, pady=2, sticky="w")
    direction_var = gui.laser_direction if hasattr(gui, 'laser_direction') else tk.StringVar(value="North")
    ttk.Combobox(scrollable_frame, textvariable=direction_var, values=["North", "South", "East", "West"], state="readonly", width=10).grid(row=5, column=1, pady=2, sticky="w")
    gui.laser_direction = direction_var

    tk.Label(scrollable_frame, text="Block:", font=("Arial", 10)).grid(row=6, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_block, width=20).grid(row=6, column=1, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Tag:", font=("Arial", 10)).grid(row=7, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_tag, width=10).grid(row=7, column=1, pady=2, sticky="w")

    # Row 8: Primary Actions
    tk.Button(scrollable_frame, text="Generate", command=gui.generate_laser, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=8, column=0, pady=5, sticky="we")
    tk.Button(scrollable_frame, text="Remove Laser", command=gui.generate_kill_laser, font=("Arial", 10), bg='#FF4444', fg='#ffffff').grid(row=8, column=1, pady=5, sticky="we")
    tk.Button(scrollable_frame, text="Copy Clipboard Pos", command=gui.copy_from_clipboard, font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=8, column=2, pady=5, sticky="we")

    # Row 9: Horizontal Rotation
    tk.Button(scrollable_frame, text="Rotate Left", command=lambda: generate_rotate_command(gui, "left"), font=("Arial", 10), bg='#9C27B0', fg='#ffffff').grid(row=9, column=0, pady=2, sticky="we")
    tk.Button(scrollable_frame, text="Rotate Right", command=lambda: generate_rotate_command(gui, "right"), font=("Arial", 10), bg='#9C27B0', fg='#ffffff').grid(row=9, column=1, pady=2, sticky="we")

    # Row 10: Vertical Rotation
    tk.Button(scrollable_frame, text="Rotate Up", command=lambda: generate_rotate_command(gui, "up"), font=("Arial", 10), bg='#673AB7', fg='#ffffff').grid(row=10, column=0, pady=2, sticky="we")
    tk.Button(scrollable_frame, text="Rotate Down", command=lambda: generate_rotate_command(gui, "down"), font=("Arial", 10), bg='#673AB7', fg='#ffffff').grid(row=10, column=1, pady=2, sticky="we")

    # Row 11: Text Output
    gui.laser_cmd_text = tk.Text(scrollable_frame, height=8, width=40)
    gui.laser_cmd_text.grid(row=11, column=0, columnspan=3, pady=5, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.laser_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10)).grid(row=11, column=3, pady=5, sticky="s")

    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(11, weight=1)