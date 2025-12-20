import tkinter as tk
from tkinter import ttk
import logging
from command_processor import CommandProcessor
from clipboard_parser import ClipboardCoordinateParser
from settings import load_settings, save_settings
from utils import adjust_offset, toggle_always_on_top, start_record_keybind, record_keybind, toggle_terminal, on_closing, show_window, copy_to_clipboard, setup_logging, cleanup
from modify_laser_tab.modify_laser_gui import create_modify_laser_gui
from set_coordinates_tab.set_coordinates_gui import create_set_coordinates_gui
from change_block_tab.change_block_gui import create_change_block_gui
from generate_laser_tab.generate_laser_gui import create_generate_laser_gui
from generate_end_beam_tab.generate_end_beam_gui import create_generate_end_beam_gui
from rename_tag_group_tab.rename_tag_group_gui import create_rename_tag_group_gui
from settings_tab.settings_gui import create_settings_gui
from worldedit_tab.worldedit_gui import create_worldedit_schematic_gui

class CommandModifierGUI:
    def __init__(self, root):
        setup_logging()  # Initialize logging from utils.py
        self.root = root
        self.root.title("Minecraft Command Block Modifier")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        self.is_destroyed = False
        self.is_recording_key = False
        self.terminal_visible = False
        self.settings = load_settings()
        self.command_processor = CommandProcessor()
        self.command_processor.set_gui(self)
        self.clipboard_parser = ClipboardCoordinateParser(self)

        # Initialize variables
        self.pos_vars = [tk.StringVar(value="0") for _ in range(3)]
        self.target_vars = [tk.StringVar(value="0") for _ in range(3)]
        self.laser_x = tk.StringVar(value="0")
        self.laser_y = tk.StringVar(value="0")
        self.laser_z = tk.StringVar(value="0")
        self.laser_tag = tk.StringVar(value="beam1")
        self.laser_block = tk.StringVar(value="minecraft:lime_concrete")
        self.laser_length = tk.StringVar(value="-150.0")
        self.end_beam_x = tk.StringVar(value="0")
        self.end_beam_y = tk.StringVar(value="0")
        self.end_beam_z = tk.StringVar(value="0")
        self.end_beam_block = tk.StringVar(value="minecraft:end_crystal")
        self.end_beam_length = tk.StringVar(value="-150.0")
        self.end_beam_tag = tk.StringVar(value="end_beam1")
        self.always_on_top = tk.BooleanVar(value=self.settings.get("always_on_top", False))
        self.key_bind = tk.StringVar(value=self.settings.get("key_bind", ""))
        self.block_text = tk.StringVar(value="minecraft:lime_concrete")
        self.modify_coords = tk.BooleanVar(value=True)
        self.modify_translation = tk.BooleanVar(value=True)
        self.modify_scale = tk.BooleanVar(value=True)
        self.modify_centering = tk.BooleanVar(value=True)
        self.laser_mode = tk.StringVar(value="laser")
        self.pos_x_set = tk.StringVar(value="0.0")
        self.pos_y_set = tk.StringVar(value="0.5")
        self.pos_z_set = tk.StringVar(value="0.999999")
        self.trans_x = tk.StringVar(value="0.5")
        self.trans_y = tk.StringVar(value="0.0")
        self.trans_z = tk.StringVar(value="0.0")
        self.beam_scale = tk.StringVar(value="-150.0")
        self.centering_x = tk.StringVar(value="0.0")
        self.centering_y = tk.StringVar(value="0.0")
        self.centering_z = tk.StringVar(value="0.0")
        self.tag_text = tk.StringVar(value="beam1")
        self.coord_format = tk.StringVar(value="Decimal")
        self.schematic_block = tk.StringVar(value="minecraft:command_block")
        self.schematic_width = tk.StringVar(value="1")
        self.schematic_height = tk.StringVar(value="1")
        self.schematic_length = tk.StringVar(value="1")
        self.schematic_x = tk.StringVar(value="0")
        self.schematic_y = tk.StringVar(value="0")
        self.schematic_z = tk.StringVar(value="0")
        self.schematic_command = tk.StringVar(value="say Hello from command block")
        self.cmd_text_set = None
        self.change_block_cmd_text = None
        self.laser_cmd_text = tk.Text(self.generate_laser_frame, height=2, width=40)
        self.end_beam_cmd_text = tk.Text(self.generate_end_beam_frame, height=2, width=40)
        self.rename_tag_cmd_text = tk.Text(self.rename_tag_group_frame, height=2, width=40)
        self.terminal_text = None

        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Create frames
        self.modify_laser_frame = ttk.Frame(self.notebook)
        self.set_coordinates_frame = ttk.Frame(self.notebook)
        self.change_block_frame = ttk.Frame(self.notebook)
        self.generate_laser_frame = ttk.Frame(self.notebook)
        self.generate_end_beam_frame = ttk.Frame(self.notebook)
        self.rename_tag_group_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.worldedit_frame = ttk.Frame(self.notebook)
        self.terminal_frame = ttk.Frame(self.root)

        # Add tabs
        self.notebook.add(self.modify_laser_frame, text="Modify Laser")
        self.notebook.add(self.set_coordinates_frame, text="Set Coordinates")
        self.notebook.add(self.change_block_frame, text="Change Block")
        self.notebook.add(self.generate_laser_frame, text="Generate Laser")
        self.notebook.add(self.generate_end_beam_frame, text="Generate End Beam")
        self.notebook.add(self.rename_tag_group_frame, text="Rename Tag/Group")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.add(self.worldedit_frame, text="WorldEdit Schematic")

        # Create GUIs
        create_modify_laser_gui(self.modify_laser_frame, self)
        create_set_coordinates_gui(self.set_coordinates_frame, self)
        create_change_block_gui(self.change_block_frame, self)
        create_generate_laser_gui(self.generate_laser_frame, self)
        create_generate_end_beam_gui(self.generate_end_beam_frame, self)
        create_rename_tag_group_gui(self.rename_tag_group_frame, self)
        create_settings_gui(self.settings_frame, self)
        create_worldedit_schematic_gui(self.worldedit_frame, self)

        # Create terminal
        self.terminal_text = tk.Text(self.terminal_frame, height=5, width=80, font=("Arial", 10))
        self.terminal_text.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.terminal_scroll = ttk.Scrollbar(self.terminal_frame, orient="vertical", command=self.terminal_text.yview)
        self.terminal_scroll.grid(row=0, column=1, sticky="ns")
        self.terminal_text.configure(yscrollcommand=self.terminal_scroll.set)
        self.terminal_frame.grid(row=1, column=0, sticky="ew")
        tk.Button(self.terminal_frame, text="Toggle Terminal", command=self.toggle_terminal, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=1, column=0, pady=5)

        # Configure terminal tags
        self.terminal_text.tag_configure("normal", foreground="black")
        self.terminal_text.tag_configure("coord", foreground="blue")
        self.terminal_text.tag_configure("modified_coord", foreground="green")
        self.terminal_text.tag_configure("command", foreground="purple")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # Bind closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Apply settings
        if self.always_on_top.get():
            self.toggle_always_on_top()
        if self.key_bind.get():
            self.root.bind(self.key_bind.get(), lambda e: self.process_clipboard())

    # Delegate methods to utils
    adjust_offset = adjust_offset
    toggle_always_on_top = toggle_always_on_top
    start_record_keybind = start_record_keybind
    record_keybind = record_keybind
    toggle_terminal = toggle_terminal
    on_closing = on_closing
    show_window = show_window
    copy_to_clipboard = copy_to_clipboard

    def print_to_text(self, message: str, tag: str = "normal"):
        """
        Prints a message to the terminal text box (shared across all tabs)
        """
        if hasattr(self, 'terminal_text') and self.terminal_text.winfo_exists():
            self.terminal_text.insert(tk.END, message + "\n", tag)
            self.terminal_text.see(tk.END)
        else:
            logging.info(f"Terminal message: {message}")

    def process_clipboard(self):
        from utils import process_clipboard
        process_clipboard(self)

    def process_command(self, command):
        active_tab = self.notebook.tab(self.notebook.select(), "text").lower()
        if active_tab == "modify laser":
            from modify_laser_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "set coordinates":
            from set_coordinates_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "change block":
            from change_block_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "generate laser":
            from generate_laser_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "generate end beam":
            from generate_end_beam_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "rename tag/group":
            from rename_tag_group_tab.modifier import process_command
            process_command(self, command)
        elif active_tab == "worldedit schematic":
            from worldedit_tab.modifier import process_command
            process_command(self, command)

    def print_to_text(self, message: str, tag: str = "normal"):
        """
        Prints a message to the terminal text box (shared across all tabs)
        """
        if hasattr(self, 'terminal_text') and self.terminal_text.winfo_exists():
            self.terminal_text.insert(tk.END, message + "\n")
            self.terminal_text.see(tk.END)
            
            # Apply tag for color
            start = self.terminal_text.index("end-1c linestart")
            end = self.terminal_text.index("end-1c")
            self.terminal_text.tag_add(tag, start, end)
        else:
            print(message)  # fallback to console