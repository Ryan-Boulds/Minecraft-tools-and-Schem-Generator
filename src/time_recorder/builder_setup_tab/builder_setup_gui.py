# ==================== time_recorder/builder_setup_tab/builder_setup_gui.py ====================
import tkinter as tk
from tkinter import ttk
import time  # Needed for the log timestamp and internal timing fixes

from .recorder import start_record_layer
from .audio_handler import load_audio_data
from .timeline_canvas import create_timeline_canvas
from .playback import start_playback
from .repeater_timing import show_repeater_timing

# Import for the new Export functionality
from ..timeline_exporter import export_timeline_to_schematic


def create_builder_setup_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # --- TOP TOOLBAR ---
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=(0, 10))

    ttk.Button(toolbar, text="💾 Save Project", command=app.save_project).pack(side="left", padx=5)
    ttk.Button(toolbar, text="📂 Load Project", command=app.load_project).pack(side="left", padx=5)
    ttk.Button(toolbar, text="🎵 Import Audio", command=lambda: load_audio_data(app)).pack(side="left", padx=5)

    # NEW EXPORT BUTTON (top right, above record button)
    ttk.Button(
        toolbar, 
        text="📤 Export Timeline Schematic",
        command=lambda: export_timeline_to_schematic(app)
    ).pack(side="right", padx=8)

    ttk.Label(toolbar, text="Timeline Builder", font=("Helvetica", 14, "bold")).pack(side="left", padx=20)

    # --- CONTROLS ---
    control_frame = ttk.Frame(frame)
    control_frame.pack(fill="x", pady=8)

    ttk.Label(control_frame, text="Tick Rate (ticks/sec): ").pack(side="left")
    ttk.Entry(control_frame, textvariable=app.tick_rate, width=10).pack(side="left", padx=5)

    # Record Button
    record_btn = ttk.Button(
        control_frame, 
        text="🔴 Record New Layer", 
        command=lambda: start_record_layer(app, record_btn)
    )
    record_btn.pack(side="right", padx=5)

    play_button = ttk.Button(
        control_frame, 
        text="▶ Play", 
        command=lambda: start_playback(app, play_button)
    )
    play_button.pack(side="right", padx=5)
    
    ttk.Button(
        control_frame, 
        text="⏱ Show Repeater Timing", 
        command=lambda: show_repeater_timing(app)
    ).pack(side="right", padx=5)

    # --- VISUAL TIMELINE ---
    canvas_label = "Visual Timeline - Drag clips left/right • Drag up/down to reorder • Ctrl+Wheel to zoom"
    canvas_frame = ttk.LabelFrame(frame, text=canvas_label)
    canvas_frame.pack(fill="both", expand=True, pady=10)

    # Initialize the canvas
    create_timeline_canvas(canvas_frame, app)

    # --- LIVE LOG ---
    log_frame = ttk.LabelFrame(frame, text="Live Activity Log")
    log_frame.pack(fill="x", side="bottom", pady=(10, 0))
    
    log_text = tk.Text(log_frame, height=4, state="disabled", font=("Consolas", 9), bg="#2b2b2b", fg="#a9b7c6")
    log_text.pack(fill="x", side="left", expand=True)
    
    log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
    log_scroll.pack(side="right", fill="y")
    log_text.config(yscrollcommand=log_scroll.set)

    # Function for the app to update this log
    def update_log(message):
        try:
            log_text.config(state="normal")
            timestamp = time.strftime('%H:%M:%S')
            log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            log_text.see(tk.END)
            log_text.config(state="disabled")
        except Exception as e:
            print(f"Log error: {e}")

    app._log_message = update_log  # Store reference in main manager for global access