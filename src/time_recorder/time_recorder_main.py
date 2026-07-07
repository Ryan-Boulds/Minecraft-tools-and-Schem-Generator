import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import keyboard
import json
import time
import pyperclip
import copy

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
        self.height_limit_var = tk.StringVar(value="50")  # Added vertical ceiling constraint variable
        
        # Internal State
        self.is_recording = False
        self.recording_start_time = None
        self.current_mapping_index = None
        self._mapping_popup = None
        self.recording_sequence = []    
        self.audio_path = None
        self.audio_waveform = None
        self.audio_duration = 0.0

        # Prevent overlapping command sends during recording
        self._command_lock = False

        # Recording send delay (used by builder_setup_gui.py)
        if not hasattr(self, 'record_send_delay'):
            self.record_send_delay = tk.StringVar(value="80")

        # Prevent keyboard repeat spam
        self._currently_pressed = set()

        # === UNDO SYSTEM ===
        self.undo_stack = []          
        self.max_undo = 20

        # Make the app more reliable when Minecraft is focused
        self._make_background_friendly()

        self._build_sub_tabs()
        self.setup_key_listener()

    def _make_background_friendly(self):
        root = self.main_app.root
        try:
            root.attributes("-topmost", True)
            root.update_idletasks()
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
            pass

    def _build_sub_tabs(self):
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self.map_buttons_frame = ttk.Frame(self.notebook)
        self.builder_setup_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.map_buttons_frame, text="Map Buttons")
        self.notebook.add(self.builder_setup_frame, text="Builder Setup")

        from .map_buttons_tab.map_buttons_gui import create_map_buttons_gui
        from .builder_setup_tab.builder_setup_gui import create_builder_setup_gui

        create_map_buttons_gui(self.map_buttons_frame, self)
        create_builder_setup_gui(self.builder_setup_frame, self)

    # ====================== UNDO SYSTEM ======================
    def _push_undo(self, description: str):
        """Save current sequences state before a change"""
        snapshot = copy.deepcopy(self.sequences)
        self.undo_stack.append((description, snapshot))
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)

    def undo(self):
        """Perform undo (Ctrl+Z)"""
        if not self.undo_stack:
            if hasattr(self, "_log_message"):
                self._log_message("Nothing to undo")
            return

        description, previous_state = self.undo_stack.pop()
        self.sequences = previous_state

        if hasattr(self, "_log_message"):
            self._log_message(f"↩ Undid: {description}")

        self._refresh_all_ui()

    # ====================== SAVE / LOAD ======================
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
                "height_limit": self.height_limit_var.get(),
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
            self.height_limit_var.set(data.get("height_limit", "50"))
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

            self.undo_stack.clear()  # Clear undo on load
            self._refresh_all_ui()
            messagebox.showinfo("Project Loaded", "Mappings + timelines restored.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _refresh_all_ui(self):
        if hasattr(self, "_refresh_map_buttons"):
            self.main_app.root.after(0, self._refresh_map_buttons)
        if hasattr(self, "_refresh_builder") and self._refresh_builder:
            self.main_app.root.after(0, self._refresh_builder)

    def add_sequence(self, name, sequence, offset=0.0):
        self._push_undo(f"Add sequence '{name}'")
        new_seq = {
            "id": self.next_sequence_id,
            "name": name,
            "sequence": sequence,
            "offset": offset,
            "visible": True
        }
        self.sequences.append(new_seq)
        self.next_sequence_id += 1
        self._refresh_all_ui()

    def delete_sequence(self, seq_id):
        seq = next((s for s in self.sequences if s["id"] == seq_id), None)
        if seq:
            self._push_undo(f"Delete sequence '{seq['name']}'")
            self.sequences = [s for s in self.sequences if s["id"] != seq_id]
            self._refresh_all_ui()

    # ====================== SPLIT (with undo) ======================
    def split_sequence(self, seq_id: int, split_time: float):
        for i, seq in enumerate(self.sequences):
            if seq["id"] == seq_id:
                self._push_undo(f"Split '{seq['name']}' at {split_time:.2f}s")

                offset = seq["offset"]
                if not seq["sequence"]:
                    messagebox.showwarning("Cannot Split", "This sequence has no commands.")
                    return

                seq_duration = seq["sequence"][-1][1] if seq["sequence"] else 0
                rel_split = split_time - offset

                if rel_split <= 0 or rel_split >= seq_duration + 0.001:
                    messagebox.showwarning("Split Position", 
                        "Playhead must be inside the clip (not at the very start or end).")
                    return

                part1 = [(cmd, ts) for cmd, ts in seq["sequence"] if ts < rel_split]
                part2 = [(cmd, ts - rel_split) for cmd, ts in seq["sequence"] if ts >= rel_split]

                base_name = seq["name"]
                del self.sequences[i]

                self.add_sequence(name=f"{base_name} - Part 1", sequence=part1, offset=offset)
                self.add_sequence(name=f"{base_name} - Part 2", sequence=part2, offset=split_time)

                if hasattr(self, "_log_message"):
                    self._log_message(f"✂ Split '{base_name}' at {split_time:.2f}s")
                return

        messagebox.showwarning("Split Error", "Sequence not found.")

    def get_merged_timeline(self):
        events = []
        for s in self.sequences:
            off = s["offset"]
            for cmd, ts in s["sequence"]:
                events.append((off + ts, cmd))
        events.sort(key=lambda x: x[0])
        return events

    # ====================== KEYBOARD ======================
    def setup_key_listener(self):
        keyboard.unhook_all()
        keyboard.hook(self._on_global_key_press)

    def _on_global_key_press(self, event):
        key_name = event.name

        # === UNDO: Ctrl + Z ===
        if event.event_type == "down":
            if (key_name == "z" and 
                (keyboard.is_pressed("ctrl") or keyboard.is_pressed("control"))):
                self.undo()
                return

        # Mapping mode
        if self.current_mapping_index is not None:
            if event.event_type == "down" and key_name != "esc":
                self.mapped_commands[self.current_mapping_index]["key"] = key_name
                self.current_mapping_index = None
                self.main_app.root.after(0, self._close_mapping_popup)
                self.main_app.root.after(0, self._refresh_map_buttons)
            return

        # Recording mode
        if not (self.is_recording and self.recording_start_time is not None):
            return

        if getattr(self, '_command_lock', False):
            return   # Don't process new keys while sending
        
        for mapping in self.mapped_commands:
            if mapping.get("key") != key_name:
                continue

            mtype = mapping.get("type", "single")
            cmd = None
            timestamp = time.time() - self.recording_start_time

            if mtype == "hold":
                if event.event_type == "down":
                    if key_name in self._currently_pressed: return
                    self._currently_pressed.add(key_name)
                    cmd = mapping.get("down_command")
                elif event.event_type == "up":
                    if key_name in self._currently_pressed:
                        self._currently_pressed.remove(key_name)
                    cmd = mapping.get("up_command")
            else:
                if event.event_type == "down":
                    if key_name in self._currently_pressed: return
                    self._currently_pressed.add(key_name)
                    cmd = mapping.get("command")
                elif event.event_type == "up":
                    if key_name in self._currently_pressed:
                        self._currently_pressed.remove(key_name)

            if cmd:
                self.recording_sequence.append((cmd, timestamp))
                if hasattr(self, "_log_message"):
                    tps = float(self.tick_rate.get() or 20)
                    current_tick = round(timestamp * tps)
                    display_cmd = cmd.strip().lstrip('/')[:37] + ("..." if len(cmd.strip().lstrip('/')) > 40 else "")
                    log_entry = f"Tick {current_tick:05d} | {key_name.upper()} -> {display_cmd}"
                    self.main_app.root.after(0, lambda: self._log_message(log_entry))

                self._trigger_minecraft_command(cmd)
            break

    # ====================== COMMAND EXECUTION ======================
    def _trigger_minecraft_command(self, command: str):
        if not command:
            return

        if getattr(self, '_command_lock', False):
            return

        self._command_lock = True

        try:
            pyperclip.copy(command.strip())
            
            # Safe delay reading
            try:
                delay_ms = float(getattr(self, 'record_send_delay', tk.StringVar(value="80")).get() or 80)
            except:
                delay_ms = 80
                
            delay = max(0.04, delay_ms / 1000.0)

            keyboard.press_and_release("/")
            time.sleep(0.035)
            keyboard.press_and_release("ctrl+v")
            time.sleep(delay)
            keyboard.press_and_release("enter")
            time.sleep(0.045)

            if hasattr(self, "_log_message"):
                self._log_message(f"→ Sent: {command.strip()[:50]}...")

        except Exception as e:
            print(f"Command trigger error: {e}")
            if hasattr(self, "_log_message"):
                self._log_message(f"❌ Send failed: {e}")

        finally:
            self.main_app.root.after(60, self._release_command_lock)

    def _release_command_lock(self):
        """Safely release the command lock"""
        self._command_lock = False

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
        if not (0 <= old_index < len(self.sequences) and 0 <= new_index < len(self.sequences)):
            return
        if old_index == new_index:
            return
        self._push_undo("Reorder sequences")
        seq = self.sequences.pop(old_index)
        self.sequences.insert(new_index, seq)
        self._refresh_all_ui()