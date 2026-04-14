# ==================== time_recorder/timeline_tab/timeline_gui.py ====================
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time

def create_timeline_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # === TOP TOOLBAR (Save / Load on EVERY tab) ===
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=(0, 10))

    ttk.Button(toolbar, text="💾 Save Project", command=app.save_project).pack(side="left", padx=5)
    ttk.Button(toolbar, text="📂 Load Project", command=app.load_project).pack(side="left", padx=5)

    ttk.Label(toolbar, text="Timeline Recorder", font=("Helvetica", 14, "bold")).pack(side="left", padx=20)

    status_label = ttk.Label(frame, text="Not recording", font=("Helvetica", 12), foreground="red")
    status_label.pack(pady=5)

    def toggle_recording():
        if not app.is_recording:
            if not app.mapped_commands:
                messagebox.showwarning("No Mappings", "Please add at least one mapping in the Map Buttons tab first!")
                return

            app.is_recording = True
            app.recording_start_time = time.time()
            app.recording_sequence = []
            app._currently_pressed.clear()
            status_label.config(text="RECORDING...", foreground="green")
            record_btn.config(text="Stop & Add as New Timeline")

        else:
            app.is_recording = False
            app.recording_start_time = None
            app._currently_pressed.clear()
            status_label.config(text="Not recording", foreground="red")
            record_btn.config(text="Start Recording")

            if app.recording_sequence:
                if messagebox.askyesno("Add to Timeline?", 
                        f"Recorded {len(app.recording_sequence)} commands.\n\nAdd this as a new layered timeline?"):
                    name = tk.simpledialog.askstring("Timeline Name", "Name for this timeline:", 
                                                     initialvalue=f"Recorded {len(app.sequences)+1}")
                    if name:
                        app.add_sequence(name=name, sequence=app.recording_sequence, offset=0.0)
                        app.recording_sequence = []

    record_btn = ttk.Button(frame, text="Start Recording", command=toggle_recording)
    record_btn.pack(pady=20)

    # Add new empty timeline
    def add_empty_timeline():
        name = tk.simpledialog.askstring("New Timeline", "Name for the new empty timeline:", 
                                         initialvalue=f"Sequence {len(app.sequences)+1}")
        if name:
            app.add_sequence(name=name, sequence=[], offset=0.0)

    ttk.Button(frame, text="➕ Add new timeline (empty)", command=add_empty_timeline).pack(pady=5)

    # List of timelines
    ttk.Label(frame, text="Current Layered Timelines", font=("Helvetica", 11, "bold")).pack(pady=(15,5))

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill="both", expand=True)

    timeline_list = tk.Listbox(list_frame, height=8)
    timeline_list.pack(side="left", fill="both", expand=True)

    def refresh_list():
        timeline_list.delete(0, tk.END)
        for s in app.sequences:
            duration = s["sequence"][-1][1] if s["sequence"] else 0.0
            timeline_list.insert(tk.END, f"• {s['name']}  |  offset: {s['offset']:.2f}s  |  {len(s['sequence'])} cmds  |  duration: {duration:.2f}s")

    app._refresh_timeline_list = refresh_list
    refresh_list()

    def delete_selected():
        sel = timeline_list.curselection()
        if not sel: return
        idx = sel[0]
        seq_id = app.sequences[idx]["id"]
        if messagebox.askyesno("Delete?", f"Delete '{app.sequences[idx]['name']}'?"):
            app.delete_sequence(seq_id)

    ttk.Button(list_frame, text="🗑 Delete Selected", command=delete_selected).pack(side="left", padx=5)

    # Live log
    log_text = tk.Text(frame, height=10, state="disabled")
    log_text.pack(fill="both", expand=True, pady=10)

    def update_log():
        log_text.config(state="normal")
        log_text.delete(1.0, tk.END)
        for i, (cmd, ts) in enumerate(app.recording_sequence):
            log_text.insert(tk.END, f"{i+1:02d}. [{ts:.2f}s] {cmd}\n")
        log_text.config(state="disabled")
        frame.after(50, update_log)

    update_log()