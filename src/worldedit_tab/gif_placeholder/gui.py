# worldedit_tab/gif_placeholder/gui.py
"""
Placeholder tab for GIF -> animated pixel art. Not implemented yet.
Planned to work like Image -> Pixel Art, but looping through each GIF frame
and building either a sequence of schematics or a single animated
command-block rig (framing TBD once the image pipeline is finalized).
"""

import tkinter as tk
from tkinter import filedialog


def create_gif_placeholder_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="GIF \u2192 Pixel Art (Coming Soon)",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Not built yet. This tab will reuse the Image \u2192 Pixel Art palette matching\n"
                  "logic, but run it once per GIF frame instead of once per image.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=6)

    file_frame = tk.Frame(frame, bg='#f0f0f0')
    file_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=6)
    tk.Label(file_frame, text="GIF File:", bg='#f0f0f0').pack(side="left")
    path_var = tk.StringVar()
    tk.Entry(file_frame, textvariable=path_var, width=50, state="disabled").pack(side="left", padx=8)
    tk.Button(file_frame, text="Browse", state="disabled").pack(side="left")

    tk.Button(frame, text="Generate (disabled)", state="disabled",
              bg='#9E9E9E', fg='white', width=24).grid(row=3, column=0, sticky="w", padx=20, pady=12)

    return frame
