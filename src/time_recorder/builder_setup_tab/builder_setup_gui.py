# ==================== time_recorder/builder_setup_tab/builder_setup_gui.py ====================
import tkinter as tk
from tkinter import ttk

from .timeline_canvas import create_timeline_canvas
from .playback import start_playback
from .repeater_timing import show_repeater_timing

def create_builder_setup_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Top toolbar
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=(0, 10))

    ttk.Button(toolbar, text="💾 Save Project", command=app.save_project).pack(side="left", padx=5)
    ttk.Button(toolbar, text="📂 Load Project", command=app.load_project).pack(side="left", padx=5)

    ttk.Label(toolbar, text="Timeline Builder", font=("Helvetica", 14, "bold")).pack(side="left", padx=20)

    # Controls
    control_frame = ttk.Frame(frame)
    control_frame.pack(fill="x", pady=8)

    ttk.Label(control_frame, text="Tick Rate (ticks/sec): ").pack(side="left")
    ttk.Entry(control_frame, textvariable=app.tick_rate, width=10).pack(side="left", padx=5)

    play_button = ttk.Button(control_frame, text="▶ Play", 
                             command=lambda: start_playback(app, play_button))
    play_button.pack(side="right", padx=5)

    ttk.Button(control_frame, text="Show Repeater Timing", 
               command=lambda: show_repeater_timing(app)).pack(side="right", padx=5)

    # === VISUAL TIMELINE (now in separate file) ===
    canvas_frame = ttk.LabelFrame(frame, text="Visual Timeline - Drag clips left/right • Drag up/down to reorder • Ctrl+Wheel to zoom")
    canvas_frame.pack(fill="both", expand=True, pady=10)

    create_timeline_canvas(canvas_frame, app)

    # Store refresh function for main app
    app._refresh_builder = None  # Will be set by timeline_canvas.py