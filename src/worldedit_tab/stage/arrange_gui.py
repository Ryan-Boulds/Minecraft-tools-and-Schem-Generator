# worldedit_tab/stage/arrange_gui.py
"""Placeholder -- the drag-and-drop stage arrangement canvas is next.
Loads saved screen objects (from the Scan Screens tab) and lets you
position each one, purely in logical pixel space, onto a shared canvas
that a video/GIF will later be mapped across -- this does NOT move
anything in the world; each screen's own real-world position stays
exactly what its scan found. Saves a stage map file the Generate tab
reads."""

import tkinter as tk


def create_arrange_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Arrange Stage", font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame, text="Coming next: drag your saved screens onto a shared canvas to lay out the full "
                          "stage, then save it as a map for the Generate tab.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    return frame
