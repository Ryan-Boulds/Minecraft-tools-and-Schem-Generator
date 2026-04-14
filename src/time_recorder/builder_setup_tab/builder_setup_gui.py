# ==================== time_recorder/builder_setup_tab/builder_setup_gui.py ====================
import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import keyboard
import pyperclip

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

    # Visual Timeline
    canvas_frame = ttk.LabelFrame(frame, text="Drag clips left/right to sync timing")
    canvas_frame.pack(fill="both", expand=True, pady=10)

    canvas = tk.Canvas(canvas_frame, height=420, bg="#f8f8f8", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    PIXELS_PER_SECOND = 80
    TRACK_HEIGHT = 55
    RULER_HEIGHT = 40

    selected_clip = [None]
    drag_start_x = [0]
    drag_start_offset = [0]

    def draw_timeline():
        canvas.delete("all")
        if not app.sequences:
            canvas.create_text(400, 200, text="No timelines yet.\nGo to Timeline tab to add some.", 
                               fill="gray", font=("Arial", 12))
            return

        max_time = max((s["offset"] + (s["sequence"][-1][1] if s["sequence"] else 0) 
                       for s in app.sequences), default=5)

        # Ruler
        canvas.create_line(50, RULER_HEIGHT, 50 + max_time * PIXELS_PER_SECOND, RULER_HEIGHT, fill="black", width=2)
        for sec in range(0, int(max_time) + 2):
            x = 50 + sec * PIXELS_PER_SECOND
            canvas.create_line(x, RULER_HEIGHT-10, x, RULER_HEIGHT+10, fill="black")
            canvas.create_text(x, RULER_HEIGHT-20, text=str(sec), font=("Arial", 9))

        for i, seq in enumerate(app.sequences):
            y = RULER_HEIGHT + 20 + i * TRACK_HEIGHT
            canvas.create_text(20, y + TRACK_HEIGHT//2, text=seq["name"][:12], anchor="e", font=("Arial", 10, "bold"))

            canvas.create_line(50, y + TRACK_HEIGHT//2, 50 + max_time * PIXELS_PER_SECOND, 
                               y + TRACK_HEIGHT//2, fill="#ddd", dash=(4,2))

            start_x = 50 + seq["offset"] * PIXELS_PER_SECOND
            duration = seq["sequence"][-1][1] if seq["sequence"] else 2
            width = max(duration * PIXELS_PER_SECOND, 60)

            clip_tag = f"clip_{seq['id']}"
            canvas.create_rectangle(start_x, y+10, start_x+width, y+TRACK_HEIGHT-10,
                                    fill="#4a90e2", outline="#2171b5", width=2, tags=clip_tag)
            canvas.create_text(start_x + width//2, y + TRACK_HEIGHT//2,
                               text=f"{seq['name'][:14]} ({len(seq['sequence'])})",
                               fill="white", font=("Arial", 9, "bold"), tags=clip_tag)

    # Drag logic (unchanged)
    def on_click(event):
        items = canvas.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
        for item in items:
            for t in canvas.gettags(item):
                if t.startswith("clip_"):
                    seq_id = int(t.split("_")[1])
                    selected_clip[0] = seq_id
                    drag_start_x[0] = event.x
                    for s in app.sequences:
                        if s["id"] == seq_id:
                            drag_start_offset[0] = s["offset"]
                            break
                    return

    def on_drag(event):
        if not selected_clip[0]: return
        delta_x = event.x - drag_start_x[0]
        delta_sec = delta_x / PIXELS_PER_SECOND
        new_offset = max(0.0, round(drag_start_offset[0] + delta_sec, 3))
        app.update_offset(selected_clip[0], new_offset)

    def on_release(event):
        selected_clip[0] = None
        draw_timeline()

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    app._refresh_builder = draw_timeline
    draw_timeline()


# ====================== PLAYBACK ======================
def start_playback(app, play_button):
    events = app.get_merged_timeline()
    if not events:
        messagebox.showwarning("Nothing to Play", "No commands to execute.")
        return

    original_text = play_button.cget("text")
    play_button.config(text="Ready", state="disabled")

    if not messagebox.askokcancel("Ready to Play", 
            "1. Switch to Minecraft now\n"
            "2. Make sure chat is closed\n"
            "3. Press ENTER (in Minecraft) to start"):
        play_button.config(text=original_text, state="normal")
        return

    entered = [False]

    def on_global_enter(event):
        if event.name == "enter" and event.event_type == "down":
            entered[0] = True
            try:
                keyboard.unhook(on_global_enter)
            except:
                pass

    keyboard.hook(on_global_enter)

    def wait_for_enter():
        while not entered[0]:
            try:
                app.main_app.root.update_idletasks()
                app.main_app.root.update()
                time.sleep(0.01)
            except:
                try: keyboard.unhook(on_global_enter)
                except: pass
                play_button.config(text=original_text, state="normal")
                return

        try:
            keyboard.unhook(on_global_enter)
        except:
            pass

        play_button.config(text="Playing...", state="disabled")
        threading.Thread(target=run_playback, args=(app, events, play_button, original_text), 
                         daemon=True).start()

    threading.Thread(target=wait_for_enter, daemon=True).start()


def run_playback(app, events, play_button, original_text):
    """Simple, reliable playback"""
    try:
        start_time = time.time()

        for abs_ts, cmd in events:
            target_time = start_time + abs_ts

            # Wait until it's time
            while time.time() < target_time:
                time.sleep(0.001)

            if cmd:
                send_command_reliably(cmd)

        print("Playback finished successfully.")

    except Exception as e:
        print(f"Playback error: {e}")

    finally:
        play_button.config(text=original_text, state="normal")


def send_command_reliably(command: str):
    """This is the exact same method that works during recording"""
    if not command:
        return

    pyperclip.copy(command.strip())

    try:
        keyboard.press_and_release('/')
        time.sleep(0.08)      # Time for chat to open
        keyboard.press_and_release('ctrl+v')
        time.sleep(0.15)      # Critical: time for paste to finish
        keyboard.press_and_release('enter')
        time.sleep(0.06)      # Cooldown before next command
    except Exception as e:
        print(f"Failed to send: {command[:60]}... | Error: {e}")


# ====================== REPEATER TIMING ======================
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