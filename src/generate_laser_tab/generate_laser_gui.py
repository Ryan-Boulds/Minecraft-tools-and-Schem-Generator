import tkinter as tk
from tkinter import ttk
from .modifier import generate_laser_commands, generate_kill_laser_command, parse_clipboard_coordinates

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

    tk.Label(scrollable_frame, text="Generate Laser", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")

    tk.Label(scrollable_frame, text="Base Position:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=1, column=0, columnspan=3, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.laser_x), ("Y:", gui.laser_y), ("Z:", gui.laser_z)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+2, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+2, column=1, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Direction:", font=("Arial", 10), bg='#f0f0f0').grid(row=5, column=0, pady=2, sticky="w")
    direction_var = gui.laser_direction if hasattr(gui, 'laser_direction') else tk.StringVar(value="North")
    ttk.Combobox(scrollable_frame, textvariable=direction_var, values=["North", "South", "East", "West"], state="readonly", width=10).grid(row=5, column=1, pady=2, sticky="w")
    gui.laser_direction = direction_var  # Ensure gui has the variable

    tk.Label(scrollable_frame, text="Block:", font=("Arial", 10), bg='#f0f0f0').grid(row=6, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_block, width=20, bg='#ffffff', font=("Arial", 10)).grid(row=6, column=1, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Tag:", font=("Arial", 10), bg='#f0f0f0').grid(row=7, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_tag, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=7, column=1, pady=2, sticky="w")

    tk.Button(scrollable_frame, text="Generate", command=gui.generate_laser, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=8, column=0, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Remove Laser", command=gui.generate_kill_laser, font=("Arial", 10), bg='#FF4444', fg='#ffffff').grid(row=8, column=1, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Copy from Clipboard", command=gui.copy_from_clipboard, font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=8, column=2, pady=5, sticky="w")

    gui.laser_cmd_text = tk.Text(scrollable_frame, height=10, width=40)
    gui.laser_cmd_text.grid(row=9, column=0, columnspan=3, pady=2, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.laser_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10)).grid(row=9, column=3, pady=2, sticky="w")

    # Configure row and column weights for scrollable_frame
    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(9, weight=1)