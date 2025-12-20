import tkinter as tk
from tkinter import ttk

def create_rename_tag_group_gui(frame, gui):
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

    tk.Label(scrollable_frame, text="Rename Tag/Group", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")
    tk.Label(scrollable_frame, text="New Tag:", font=("Arial", 10), bg='#f0f0f0').grid(row=1, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.tag_text, width=15, bg='#ffffff', font=("Arial", 10)).grid(row=1, column=1, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Generate", command=gui.process_clipboard, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=2, column=0, columnspan=2, pady=5, sticky="w")

    gui.rename_tag_cmd_text = tk.Text(scrollable_frame, height=10, width=40)
    gui.rename_tag_cmd_text.grid(row=3, column=0, columnspan=3, pady=2, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.rename_tag_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=3, column=3, pady=2, sticky="w")
    tk.Label(scrollable_frame, text="Press set keybind to take coordinates from command and automatically update clipboard with result. Works with: summon, execute, tp, kill.", font=("Arial", 8), bg='#f0f0f0').grid(row=4, column=0, columnspan=3, pady=2, sticky="w")

    # Configure row and column weights for scrollable_frame
    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.rowconfigure(3, weight=1)