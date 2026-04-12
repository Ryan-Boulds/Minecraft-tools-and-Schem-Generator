import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json   # ← This line was missing or not working in your file

def create_builder_setup_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="Builder Setup", font=("Helvetica", 14, "bold")).pack(pady=5)

    # Tick rate selector
    tick_frame = ttk.Frame(frame)
    tick_frame.pack(fill="x", pady=8)
    ttk.Label(tick_frame, text="Tick Rate (ticks per second): ").pack(side="left")
    tick_entry = ttk.Entry(tick_frame, textvariable=app.tick_rate, width=10)
    tick_entry.pack(side="left", padx=5)

    def load_and_analyze():
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Select Recording File"
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            sequence = data.get("sequence", [])
            tick_rate = float(app.tick_rate.get() or 20)

            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"✅ Loaded {len(sequence)} commands from:\n{filepath}\n\n")
            result_text.insert(tk.END, "No.  Command                              Delay(s)   Ticks     Repeaters\n")
            result_text.insert(tk.END, "-" * 80 + "\n")

            prev_ts = 0.0
            total_repeaters = 0

            for i, entry in enumerate(sequence):
                cmd = entry.get("command", "[empty]")
                ts = entry.get("delay_seconds", 0.0)
                delta_sec = ts - prev_ts
                ticks_needed = delta_sec * tick_rate
                repeaters = max(0, round(ticks_needed / 2))   # 1 repeater = 2 ticks

                total_repeaters += repeaters

                result_text.insert(tk.END, 
                    f"{i+1:2d}.  {cmd[:38]:38}  {delta_sec:7.3f}s   {ticks_needed:7.1f}   {repeaters:3} repeaters\n"
                )

                prev_ts = ts

            result_text.insert(tk.END, f"\nTotal repeaters needed: {total_repeaters}\n")
            messagebox.showinfo("Success", f"Analysis complete!\nTotal repeaters: {total_repeaters}")

        except json.JSONDecodeError:
            messagebox.showerror("JSON Error", "The selected file is not a valid JSON file.")
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file:\n{str(e)}")

    ttk.Button(frame, text="Load Saved Recording & Analyze", command=load_and_analyze).pack(pady=10)

    # Results area
    result_text = tk.Text(frame, height=22, wrap="word", font=("Consolas", 10))
    result_text.pack(fill="both", expand=True, pady=5)