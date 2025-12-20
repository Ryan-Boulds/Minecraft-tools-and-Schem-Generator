import tkinter as tk
from tkinter import ttk
from .modifier import modify_clipboard_command, generate_kill_block_display_command

def create_change_block_gui(frame, gui):
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

    tk.Label(scrollable_frame, text="Change Block", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")

    tk.Label(scrollable_frame, text="Block:", font=("Arial", 10), bg='#f0f0f0').grid(row=1, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.block_text, width=20, bg='#ffffff', font=("Arial", 10)).grid(row=1, column=1, columnspan=2, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Tag (for Block Display):", font=("Arial", 10), bg='#f0f0f0').grid(row=2, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.change_block_tag, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=2, column=1, pady=2, sticky="w")

    tk.Button(scrollable_frame, text="Copy from Clipboard", command=gui.modify_clipboard_command, font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=3, column=0, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Modify Command", command=gui.modify_clipboard_command, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=3, column=1, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Despawn Block Display", command=gui.generate_kill_block_display, font=("Arial", 10), bg='#FF4444', fg='#ffffff').grid(row=3, column=2, pady=5, sticky="w")

    gui.change_block_cmd_text = tk.Text(scrollable_frame, height=5, width=40)
    gui.change_block_cmd_text.grid(row=4, column=0, columnspan=3, pady=2, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.change_block_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10)).grid(row=4, column=3, pady=2, sticky="w")

    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(4, weight=1)