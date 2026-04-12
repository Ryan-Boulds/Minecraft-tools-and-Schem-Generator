import tkinter as tk
from tkinter import ttk, messagebox, filedialog   # ← filedialog is now imported
import json
import time

def create_timeline_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="Timeline Recorder", font=("Helvetica", 14, "bold")).pack(pady=10)

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
            status_label.config(text="RECORDING...", foreground="green")
            record_btn.config(text="Stop Recording")

        else:
            app.is_recording = False
            app.recording_start_time = None
            status_label.config(text="Not recording", foreground="red")
            record_btn.config(text="Start Recording")

            if app.recording_sequence and messagebox.askyesno("Save Recording?", 
                    "Recording stopped.\nWould you like to save the sequence?"):
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                    title="Save Recording Sequence"
                )
                if filepath:
                    try:
                        data = {
                            "tick_rate": int(app.tick_rate.get()),
                            "sequence": [{"command": cmd, "delay_seconds": round(ts, 3)} 
                                         for cmd, ts in app.recording_sequence]
                        }
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        messagebox.showinfo("Saved", f"Sequence saved successfully to:\n{filepath}")
                    except Exception as e:
                        messagebox.showerror("Save Error", f"Failed to save file:\n{e}")

    record_btn = ttk.Button(frame, text="Start Recording", command=toggle_recording)
    record_btn.pack(pady=20)

    # Live log
    log_text = tk.Text(frame, height=15, state="disabled")
    log_text.pack(fill="both", expand=True, pady=10)

    def update_log():
        log_text.config(state="normal")
        log_text.delete(1.0, tk.END)
        for i, (cmd, ts) in enumerate(app.recording_sequence):
            log_text.insert(tk.END, f"{i+1:02d}. [{ts:.2f}s] {cmd}\n")
        log_text.config(state="disabled")
        frame.after(50, update_log)

    update_log()