# worldedit_tab/video_placeholder/gui.py
"""
Placeholder tab for video -> command block animation. Not implemented yet.

Planned flow (per Ryan's spec, not built yet):
  1. "Extract Frames": open a video file, split it into frames, save each
     frame as an image (1.png, 2.png, 3.png, ...) into a chosen folder.
  2. "Generate From Folder": open that folder of numbered frames and build
     a schematic where each frame's pixel art is placed, followed by a row
     of repeaters, then the next frame's pixel art, and so on -- so
     powering the rig plays the frames back in sequence.
"""

import tkinter as tk


def create_video_placeholder_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Video \u2192 Command Block Animation (Coming Soon)",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Not built yet. Planned flow:\n"
                  "  1. Extract Frames \u2013 split a video into numbered frame images (1.png, 2.png, ...)\n"
                  "  2. Generate From Folder \u2013 turn each frame into pixel art blocks, separated by\n"
                  "     repeaters, so powering the schematic plays the frames back in order.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=6)

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=2, column=0, sticky="w", padx=20, pady=12)
    tk.Button(btn_frame, text="Extract Frames (disabled)", state="disabled",
              bg='#9E9E9E', fg='white', width=24).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Generate From Folder (disabled)", state="disabled",
              bg='#9E9E9E', fg='white', width=26).pack(side="left", padx=6)

    return frame
