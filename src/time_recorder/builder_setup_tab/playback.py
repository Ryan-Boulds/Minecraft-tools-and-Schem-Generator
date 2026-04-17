# ==================== time_recorder/builder_setup_tab/playback.py ====================
import tkinter as tk
from tkinter import messagebox
import time
import threading
import keyboard
import pyperclip   # ← This was missing!

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
    try:
        start_time = time.time()

        for abs_ts, cmd in events:
            target_time = start_time + abs_ts
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
    """Reliable command sender used by Playback"""
    if not command:
        return
    pyperclip.copy(command.strip())
    try:
        keyboard.press_and_release('/')
        time.sleep(0.10)
        keyboard.press_and_release('ctrl+v')
        time.sleep(0.18)
        keyboard.press_and_release('enter')
        time.sleep(0.08)
    except Exception as e:
        print(f"Failed to send: {command[:60]}... | Error: {e}")