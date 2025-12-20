import tkinter as tk
from tkinter import ttk
from .modifier import generate_end_beam_commands, generate_kill_end_beam_command, parse_clipboard_coordinates

def create_generate_end_beam_gui(frame, gui):
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

    tk.Label(scrollable_frame, text="Generate End Beam", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")

    tk.Label(scrollable_frame, text="Origin Position:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=1, column=0, columnspan=2, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Copy from Clipboard", command=lambda: parse_clipboard_coordinates(gui, "origin"), font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=1, column=2, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.end_beam_x), ("Y:", gui.end_beam_y), ("Z:", gui.end_beam_z)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+2, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+2, column=1, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Target Position:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=5, column=0, columnspan=2, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Copy from Clipboard", command=lambda: parse_clipboard_coordinates(gui, "target"), font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=5, column=2, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.end_beam_target_x), ("Y:", gui.end_beam_target_y), ("Z:", gui.end_beam_target_z)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+6, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+6, column=1, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Tag:", font=("Arial", 10), bg='#f0f0f0').grid(row=9, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.end_beam_tag, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=9, column=1, pady=2, sticky="w")

    tk.Button(scrollable_frame, text="Generate", command=gui.generate_end_beam, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=10, column=0, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Despawn End Beam", command=gui.generate_kill_end_beam, font=("Arial", 10), bg='#FF4444', fg='#ffffff').grid(row=10, column=1, pady=5, sticky="w")

    gui.end_beam_cmd_text = tk.Text(scrollable_frame, height=5, width=40)
    gui.end_beam_cmd_text.grid(row=11, column=0, columnspan=3, pady=2, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.end_beam_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10)).grid(row=11, column=3, pady=2, sticky="w")

    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(11, weight=1)