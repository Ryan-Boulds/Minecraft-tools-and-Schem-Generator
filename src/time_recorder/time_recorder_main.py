import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import keyboard
import json
import time
import pyperclip

class TimeRecorderManager:
    """Manages all Time Recorder logic and sub-tabs as a single project"""
    
    def __init__(self, parent_frame, main_app):
        self.main_app = main_app
        self.frame = parent_frame

        # --- CENTRALIZED PROJECT DATA ---
        self.mapped_commands = []       
        self.sequences = []             
        self.next_sequence_id = 0
        self.tick_rate = tk.StringVar(value="20")
        
        # Internal State
        self.is_recording = False
        self.recording_start_time = None
        self.current_mapping_index = None
        self._mapping_popup = None
        self.recording_sequence = []    # temporary during live recording

        # Prevent keyboard repeat spam
        self._currently_pressed = set()

        # Make the app more reliable when Minecraft is focused
        self._make_background_friendly()

        self._build_sub_tabs()
        self.setup_key_listener()

    def _make_background_friendly(self):
        """Improves reliability when switching focus to Minecraft"""
        root = self.main_app.root
        try:
            # Keep window on top but reduce focus stealing
            root.attributes("-topmost", True)
            root.update_idletasks()

            # Windows-specific: make window act more like a tool window
            hwnd = root.winfo_id()
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass  # Not critical if it fails

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

        from .map_buttons_tab.map_buttons_gui import create_map_buttons_gui
        from .timeline_tab.timeline_gui import create_timeline_gui
        from .builder_setup_tab.builder_setup_gui import create_builder_setup_gui

        create_map_buttons_gui(self.map_buttons_frame, self)
        create_timeline_gui(self.timeline_frame, self)
        create_builder_setup_gui(self.builder_setup_frame, self)

    # ====================== UNIFIED SAVE / LOAD ======================

    def save_project(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Save Time Recorder Project"
        )
        if not filepath: return

        try:
            project_data = {
                "tick_rate": self.tick_rate.get(),
                "mapped_commands": self.mapped_commands,
                "sequences": [
                    {
                        "id": s["id"],
                        "name": s["name"],
                        "offset": s["offset"],
                        "sequence": [{"command": cmd, "delay": ts} for cmd, ts in s["sequence"]]
                    }
                    for s in self.sequences
                ]
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=4)

            messagebox.showinfo("Project Saved", f"Everything saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def load_project(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            title="Load Time Recorder Project"
        )
        if not filepath: return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.tick_rate.set(data.get("tick_rate", "20"))
            self.mapped_commands = data.get("mapped_commands", [])

            self.sequences = []
            self.next_sequence_id = 0
            for entry in data.get("sequences", []):
                seq = {
                    "id": entry.get("id", self.next_sequence_id),
                    "name": entry.get("name", f"Sequence {self.next_sequence_id}"),
                    "offset": float(entry.get("offset", 0.0)),
                    "sequence": [(e["command"], float(e["delay"])) for e in entry.get("sequence", [])]
                }
                self.sequences.append(seq)
                self.next_sequence_id = max(self.next_sequence_id, seq["id"] + 1)

            self._refresh_all_ui()
            messagebox.showinfo("Project Loaded", "Mappings + all layered timelines restored.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _refresh_all_ui(self):
        if hasattr(self, "_refresh_map_buttons"):
            self.main_app.root.after(0, self._refresh_map_buttons)
        if hasattr(self, "_refresh_timeline_list"):
            self.main_app.root.after(0, self._refresh_timeline_list)
        if hasattr(self, "_refresh_builder"):
            self.main_app.root.after(0, self._refresh_builder)

    # ====================== SEQUENCE MANAGEMENT ======================

    def add_sequence(self, name=None, sequence=None, offset=0.0):
        if name is None:
            name = f"Sequence {len(self.sequences) + 1}"
        if sequence is None:
            sequence = []
        seq = {
            "id": self.next_sequence_id,
            "name": name,
            "offset": float(offset),
            "sequence": list(sequence)
        }
        self.sequences.append(seq)
        self.next_sequence_id += 1
        self._refresh_all_ui()
        return seq["id"]

    def delete_sequence(self, seq_id):
        self.sequences = [s for s in self.sequences if s["id"] != seq_id]
        self._refresh_all_ui()

    def update_offset(self, seq_id, new_offset):
        for s in self.sequences:
            if s["id"] == seq_id:
                s["offset"] = float(new_offset)
                self._refresh_all_ui()
                break

    def get_merged_timeline(self):
        events = []
        for s in self.sequences:
            off = s["offset"]
            for cmd, ts in s["sequence"]:
                events.append((off + ts, cmd))
        events.sort(key=lambda x: x[0])
        return events

    # ====================== KEYBOARD LOGIC ======================

    def setup_key_listener(self):
        keyboard.unhook_all()  # Prevent duplicate hooks
        keyboard.hook(self._on_global_key_press)

    def _on_global_key_press(self, event):
        key_name = event.name

        # 1. KEY MAPPING MODE
        if self.current_mapping_index is not None:
            if event.event_type == "down" and key_name != "esc":
                self.mapped_commands[self.current_mapping_index]["key"] = key_name
                self.current_mapping_index = None
                self.main_app.root.after(0, self._close_mapping_popup)
                self.main_app.root.after(0, self._refresh_map_buttons)
            return

        # 2. RECORDING MODE - Works even when Minecraft is focused
        if not (self.is_recording and self.recording_start_time is not None):
            return

        for mapping in self.mapped_commands:
            if mapping.get("key") != key_name:
                continue

            mtype = mapping.get("type", "single")
            cmd = None
            timestamp = time.time() - self.recording_start_time

            if mtype == "hold":
                if event.event_type == "down":
                    if key_name in self._currently_pressed:
                        return
                    self._currently_pressed.add(key_name)
                    cmd = mapping.get("down_command")
                elif event.event_type == "up":
                    if key_name in self._currently_pressed:
                        self._currently_pressed.remove(key_name)
                    cmd = mapping.get("up_command")
            else:  # SINGLE
                if event.event_type == "down":
                    if key_name in self._currently_pressed:
                        return
                    self._currently_pressed.add(key_name)
                    cmd = mapping.get("command")
                elif event.event_type == "up":
                    if key_name in self._currently_pressed:
                        self._currently_pressed.remove(key_name)

            if cmd:
                self.recording_sequence.append((cmd, timestamp))
                self._trigger_minecraft_command(cmd)
            break

    def _trigger_minecraft_command(self, command: str):
        """Improved reliability for sending commands to Minecraft"""
        if not command:
            return
        pyperclip.copy(command.strip())
        try:
            keyboard.press_and_release("/")
            time.sleep(0.04)      # Time for chat to open
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.05)      # Critical delay for paste
            keyboard.press_and_release("enter")
            time.sleep(0.06)      # Cooldown before next command
        except Exception as e:
            print(f"Command trigger error: {e}")

    def _show_listening_popup(self, index):
        self.current_mapping_index = index
        self._mapping_popup = tk.Toplevel(self.main_app.root)
        self._mapping_popup.title("Mapping...")
        self._mapping_popup.geometry("250x100")
        self._mapping_popup.attributes("-topmost", True)
        ttk.Label(self._mapping_popup, text="Press any key to map...", font=("Arial", 10)).pack(expand=True)

    def _close_mapping_popup(self):
        if self._mapping_popup:
            self._mapping_popup.destroy()
            self._mapping_popup = None


    def move_sequence(self, old_index: int, new_index: int):
        """Reorder sequences by dragging tracks up/down in the builder"""
        if not (0 <= old_index < len(self.sequences) and 0 <= new_index < len(self.sequences)):
            return
        if old_index == new_index:
            return
        seq = self.sequences.pop(old_index)
        self.sequences.insert(new_index, seq)
        self._refresh_all_ui()

    def move_sequence(self, old_index: int, new_index: int):
        if not (0 <= old_index < len(self.sequences) and 0 <= new_index < len(self.sequences)):
            return
        if old_index == new_index:
            return
        seq = self.sequences.pop(old_index)
        self.sequences.insert(new_index, seq)
        self._refresh_all_ui()