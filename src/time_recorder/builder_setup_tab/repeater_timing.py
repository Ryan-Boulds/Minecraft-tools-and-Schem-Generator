# ==================== time_recorder/builder_setup_tab/repeater_timing.py ====================
import tkinter as tk
from tkinter import ttk, messagebox

def show_repeater_timing(app):
    events = app.get_merged_timeline()
    if not events:
        messagebox.showinfo("Repeater Timing", "No commands yet.")
        return

    win = tk.Toplevel()
    win.title("Minecraft Repeater Timing")
    win.geometry("950x650")

    ttk.Label(win, text="Merged Timeline with Repeater Delays (in ticks)", 
              font=("Helvetica", 12, "bold")).pack(pady=8)

    text = tk.Text(win, wrap="none", font=("Consolas", 10))
    text.pack(fill="both", expand=True, padx=10, pady=5)

    tick_rate = float(app.tick_rate.get() or 20)
    prev = 0.0

    text.insert(tk.END, f"Tick Rate: {tick_rate} tps\n")
    text.insert(tk.END, "="*95 + "\n\n")

    for i, (ts, cmd) in enumerate(events):
        delta = ts - prev
        ticks = round(delta * tick_rate)
        repeater_ticks = max(1, ticks)
        text.insert(tk.END, f"{i+1:03d}.  {ts:7.2f}s   Δ {delta:6.2f}s   → {repeater_ticks:4} ticks   |  {cmd}\n")
        prev = ts

    text.config(state="disabled")
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)