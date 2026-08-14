# worldedit_tab/stage/generate_gui.py
"""Placeholder -- loads a saved stage map plus a video/GIF and produces
the schem file(s), reusing the same wall/relay/layer-splitting/
fill-trigger machinery already built and proven for the GIF and Video
tabs -- the only real difference is that each pixel's setblock target
comes from a per-pixel lookup (the stage map) instead of one shared,
flat-wall formula."""

import tkinter as tk


def create_stage_generate_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Generate", font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame, text="Coming next: load a saved stage map, add a video or GIF, and generate the "
                          "schem file(s) -- same wall/relay/layer-splitting design as the GIF and Video "
                          "tabs, just aiming each pixel at the stage map's recorded world position "
                          "instead of a flat wall.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    return frame
