# worldedit_tab/__main__.py
# Updated on 04:01 PM CDT, Saturday, August 30, 2025
import tkinter as tk
from .worldedit_gui import create_worldedit_schematic_gui
from .schematic_generator import generate_schematic

class TestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WorldEdit Schematic Tab Test")
        self.root.geometry("600x400")
        self.terminal_text = None  # Placeholder for terminal output
        self.schematic_block = tk.StringVar(value="minecraft:stone")
        self.schematic_width = tk.StringVar(value="1")
        self.schematic_height = tk.StringVar(value="1")
        self.schematic_length = tk.StringVar(value="1")
        self.schematic_x = tk.StringVar(value="0")
        self.schematic_y = tk.StringVar(value="0")
        self.schematic_z = tk.StringVar(value="0")
        self.notebook = tk.Frame(self.root)  # Dummy notebook for compatibility
        create_worldedit_schematic_gui(tk.Frame(self.root), self)
        self.root.mainloop()

    def print_to_text(self, message, tags="normal"):
        print(message)  # Print to console for testing

    def copy_to_clipboard(self, command):
        print(f"Copied to clipboard: {command}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TestGUI(root)