# Created on 12:25 PM CDT, Monday, September 01, 2025
import tkinter as tk
from tkinter import ttk
from utils import start_record_keybind

def create_settings_gui(frame, gui):
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

    tk.Label(scrollable_frame, text="Settings", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=3, pady=5, sticky="w")

    tk.Checkbutton(scrollable_frame, text="Always on Top", variable=gui.always_on_top, command=gui.toggle_always_on_top, font=("Arial", 10), bg='#f0f0f0').grid(row=1, column=0, columnspan=2, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Keybind:", font=("Arial", 10), bg='#f0f0f0').grid(row=2, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.key_bind, width=20, bg='#ffffff', font=("Arial", 10)).grid(row=2, column=1, pady=2, sticky="w")
    tk.Button(scrollable_frame, text="Record Keybind", command=lambda: start_record_keybind(gui), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=2, column=2, pady=2, sticky="w")

    tk.Label(scrollable_frame, text="Coordinate Format:", font=("Arial", 10), bg='#f0f0f0').grid(row=3, column=0, pady=2, sticky="w")
    tk.OptionMenu(scrollable_frame, gui.coord_format, "Decimal", "Integer", "Fractional").grid(row=3, column=1, columnspan=2, pady=2, sticky="w")