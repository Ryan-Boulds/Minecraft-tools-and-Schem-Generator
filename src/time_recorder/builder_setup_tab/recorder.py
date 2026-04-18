# ==================== time_recorder/builder_setup_tab/recorder.py ====================
import tkinter as tk
from tkinter import messagebox, simpledialog
import time
import threading
import keyboard
import pygame

def finalize_recording(app, record_button, original_text):
    """Handles saving the data once recording is finished"""
    record_button.config(text=original_text, state="normal")
    
    if app.recording_sequence:
        if messagebox.askyesno("Save Layer?", f"Captured {len(app.recording_sequence)} commands. Add to timeline?"):
            name = simpledialog.askstring("Name Layer", "Enter a name for this sequence:", 
                                         initialvalue=f"Take {len(app.sequences)+1}")
            if name:
                app.add_sequence(name=name, sequence=app.recording_sequence, offset=0.0)
                if hasattr(app, "_refresh_builder"):
                    app._refresh_builder()
    else:
        messagebox.showinfo("No Data", "No commands were captured during recording.")

def recording_loop(app, record_button, original_text):
    """Background thread that monitors time and keys during recording"""
    try:
        while app.is_recording:
            elapsed = time.time() - app.recording_start_time
            
            # Update UI playhead in real-time
                        # Update UI playhead in real-time
            if hasattr(app, "_update_playhead"):
                app.main_app.root.after(0, lambda t=elapsed: safe_update_playhead(app, t))

            # Stop if audio finishes
            if hasattr(app, 'audio_duration') and app.audio_duration > 0:
                if elapsed >= app.audio_duration:
                    break
            
            # Physical safety stop
            if keyboard.is_pressed('esc'):
                break
                
            time.sleep(0.01)

    except Exception as e:
        if hasattr(app, "_log_message"):
            app._log_message(f"Recording Loop Error: {e}")
    finally:
        app.is_recording = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        
        # UI Cleanup and Save Prompt
        app.main_app.root.after(0, lambda: finalize_recording(app, record_button, original_text))

def start_record_layer(app, record_button):
    """Toggles the 'Record-along' sequence on and off"""
    
    # --- TOGGLE: STOP RECORDING ---
    if app.is_recording:
        app.is_recording = False # This breaks the while loop in recording_loop
        return

    if not app.mapped_commands:
        messagebox.showwarning("No Mappings", "Please add mappings in 'Map Buttons' first.")
        return

    original_text = "🔴 Record New Layer"
    
    # 1. Start Confirmation
    if not messagebox.askokcancel("Record New Layer", 
            "1. Switch to Minecraft\n"
            "2. Press ENTER to start recording & audio"):
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

        # --- START RECORDING STATE ---
        # Change UI to Stop Mode
        record_button.config(text="⏹ Stop Recording", state="normal")
        
        app.is_recording = True
        app.recording_sequence = []
        app.recording_start_time = time.time()

        if app.audio_path:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(app.audio_path)
                pygame.mixer.music.play()
            except Exception as e:
                if hasattr(app, "_log_message"):
                    app._log_message(f"Audio Error: {e}")

        # Start background monitor
        threading.Thread(target=recording_loop, args=(app, record_button, original_text), daemon=True).start()



    threading.Thread(target=wait_for_enter, daemon=True).start()\
    
def safe_update_playhead(app, elapsed):
    """Safe wrapper to prevent crashes if canvas isn't ready"""
    try:
        if hasattr(app, "_update_playhead") and app._update_playhead:
            app._update_playhead(elapsed)
    except Exception as e:
        print(f"Playhead update skipped: {e}")