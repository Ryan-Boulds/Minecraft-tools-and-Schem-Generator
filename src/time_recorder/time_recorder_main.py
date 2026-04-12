import tkinter as tk
from tkinter import ttk
import keyboard

class TimeRecorderManager:
    """Manages all Time Recorder logic and sub-tabs"""
    
    def __init__(self, parent_frame, main_app):
        self.main_app = main_app          # reference to CommandModifierGUI
        self.frame = parent_frame

        # Shared variables (moved here for better organization)
        self.mapped_commands = []
        self.recording_sequence = []
        self.is_recording = False
        self.recording_start_time = None
        self.current_mapping_index = None
        self._mapping_popup = None
        self.tick_rate = tk.StringVar(value="20")

        self._build_sub_tabs()

    def _build_sub_tabs(self):
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self.map_buttons_frame = ttk.Frame(self.notebook)
        self.timeline_frame = ttk.Frame(self.notebook)
        self.builder_setup_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.map_buttons_frame, text="Map Buttons")
        self.notebook.add(self.timeline_frame, text="Timeline")
        self.notebook.add(self.builder_setup_frame, text="Builder Setup")

        # Import and create GUIs
        from .map_buttons_tab.map_buttons_gui import create_map_buttons_gui
        from .timeline_tab.timeline_gui import create_timeline_gui
        from .builder_setup_tab.builder_setup_gui import create_builder_setup_gui

        create_map_buttons_gui(self.map_buttons_frame, self)
        create_timeline_gui(self.timeline_frame, self)
        create_builder_setup_gui(self.builder_setup_frame, self)

    # ====================== KEYBOARD & RECORDING LOGIC ======================
    def setup_key_listener(self):
        keyboard.hook(self._on_global_key_press)

    def _on_global_key_press(self, event):
        if event.event_type not in ("down", "up"):
            return

        key_name = event.name

        # Mapping mode
        if self.current_mapping_index is not None:
            if key_name not in {"esc", "unknown"}:
                mapping = self.mapped_commands[self.current_mapping_index]
                mapping["key"] = key_name
                mapping["type"] = mapping.get("type", "single")
                self.current_mapping_index = None
                self.root.after(0, getattr(self, '_refresh_map_buttons', lambda: None))

                if self._mapping_popup:
                    try:
                        self._mapping_popup.destroy()
                    except:
                        pass
                    self._mapping_popup = None
            return

        # Recording mode
        if self.is_recording and self.recording_start_time is not None:
            for mapping in self.mapped_commands:
                if mapping.get("key") != key_name:
                    continue
                cmd = None
                if mapping.get("type") == "hold":
                    if event.event_type == "down" and mapping.get("down_command"):
                        cmd = mapping["down_command"]
                    elif event.event_type == "up" and mapping.get("up_command"):
                        cmd = mapping["up_command"]
                else:
                    if event.event_type == "down" and mapping.get("command"):
                        cmd = mapping["command"]

                if cmd:
                    self._trigger_mapped_command(cmd)
                    timestamp = time.time() - self.recording_start_time
                    self.recording_sequence.append((cmd, timestamp))
                    break

    def _trigger_mapped_command(self, command: str):
        if not command:
            return
        import pyperclip
        pyperclip.copy(command.strip())
        try:
            keyboard.press_and_release("/")
            time.sleep(0.05)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.05)
            keyboard.press_and_release("enter")
        except Exception as e:
            print(f"Simulation error: {e}")

    def _show_listening_popup(self, index):
        try:
            if self._mapping_popup:
                self._mapping_popup.destroy()
        except:
            pass

        popup = tk.Toplevel(self.main_app.root)
        popup.title("Mapping Key")
        popup.geometry("300x120")
        popup.resizable(False, False)
        popup.grab_set()

        ttk.Label(popup, text="Listening for key press...", font=("Helvetica", 11)).pack(pady=20)
        ttk.Label(popup, text="Press any key (ESC to cancel)", foreground="gray").pack()

        self._mapping_popup = popup

    # Helper to expose refresh
    def _refresh_map_buttons(self):
        pass  # Will be set by map_buttons_gui