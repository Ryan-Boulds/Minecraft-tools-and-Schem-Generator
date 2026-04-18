# ==================== time_recorder/builder_setup_tab/playback.py ====================
import tkinter as tk
from tkinter import messagebox
import time
import threading
import keyboard
import pyperclip
import pygame

def start_playback(app, play_button):
    events = app.get_merged_timeline()
    if not events:
        messagebox.showwarning("Nothing to Play", "No commands to execute.")
        return

    original_text = play_button.cget("text")
    play_button.config(text="Ready", state="disabled")

    if not messagebox.askokcancel("Ready to Play", 
            "1. Switch to Minecraft\n"
            "2. Ensure chat is CLOSED\n"
            "3. Press ENTER to start"):
        play_button.config(text=original_text, state="normal")
        return

    state = {"entered": False}

    def on_global_enter(event):
        if event.name == "enter" and event.event_type == "down":
            state["entered"] = True
            try: keyboard.unhook(on_global_enter)
            except: pass

    keyboard.hook(on_global_enter)

    def wait_for_enter():
        while not state["entered"]:
            try:
                app.main_app.root.update()
                time.sleep(0.01)
            except: return

        play_button.config(text="Playing...", state="disabled")
        threading.Thread(
            target=run_playback, 
            args=(app, events, play_button, original_text), 
            daemon=True
        ).start()

    threading.Thread(target=wait_for_enter, daemon=True).start()

def run_playback(app, events, play_button, original_text):
    # Initialize mixer for audio
    pygame.mixer.init()
    
    try:
        # Load and Start Audio if it exists
        if hasattr(app, 'audio_path') and app.audio_path:
            pygame.mixer.music.load(app.audio_path)
            pygame.mixer.music.play()

        start_time = time.time()
        event_idx = 0
        total_events = len(events)
        
        while event_idx < total_events:
            current_elapsed = time.time() - start_time
            
            # Update the UI playhead position
            if hasattr(app, "_update_playhead"):
                app.main_app.root.after(0, lambda t=current_elapsed: app._update_playhead(t))

            # Process events that have reached their timestamp
            abs_ts, cmd = events[event_idx]
            if current_elapsed >= abs_ts:
                threading.Thread(target=send_command_reliably, args=(cmd,), daemon=True).start()
                event_idx += 1
            
            # Small sleep to prevent high CPU usage
            time.sleep(0.005)

        # Brief pause at end to let final commands execute
        time.sleep(0.5)
        
        # Snap back to beginning
        if hasattr(app, "_update_playhead"):
            app.main_app.root.after(0, lambda: app._update_playhead(0.0))

    except Exception as e:
        print(f"Playback error: {e}")
    finally:
        # Cleanup
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        app.main_app.root.after(0, lambda: play_button.config(text=original_text, state="normal"))

def send_command_reliably(command: str):
    if not command: return
    pyperclip.copy(command.strip())
    try:
        keyboard.press_and_release('/')
        time.sleep(0.08)
        keyboard.press_and_release('ctrl+v')
        time.sleep(0.12)
        keyboard.press_and_release('enter')
    except Exception as e:
        print(f"Failed to send: {e}")