# worldedit_tab/worldedit_gui.py
import tkinter as tk
from tkinter import ttk
from .schematic_generator import generate_schematic
from .schem_viewer.viewer import SchematicViewer
from tkinter import filedialog
import threading

def create_worldedit_schematic_gui(frame, gui):
    """Create a GUI tab for generating and viewing WorldEdit schematic files."""
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    # Title
    tk.Label(scrollable_frame, text="WorldEdit Schematic Generator", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=5, pady=5, sticky="w")

    # Block Type
    tk.Label(scrollable_frame, text="Block Type:", font=("Arial", 10), bg='#f0f0f0').grid(row=1, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.schematic_block, width=20, bg='#ffffff', font=("Arial", 10)).grid(row=1, column=1, pady=2, sticky="w")

    # Dimensions
    tk.Label(scrollable_frame, text="Dimensions (Width, Height, Length):", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=2, column=0, columnspan=5, pady=2, sticky="w")
    for i, (label, var) in enumerate([("Width:", gui.schematic_width), ("Height:", gui.schematic_height), ("Length:", gui.schematic_length)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+3, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+3, column=1, pady=2, sticky="w")

    # Origin Coordinates
    tk.Label(scrollable_frame, text="Origin (X, Y, Z):", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=6, column=0, columnspan=5, pady=2, sticky="w")
    for i, (label, var) in enumerate([("X:", gui.schematic_x), ("Y:", gui.schematic_y), ("Z:", gui.schematic_z)]):
        tk.Label(scrollable_frame, text=label, font=("Arial", 10), bg='#f0f0f0').grid(row=i+7, column=0, pady=2, sticky="w")
        tk.Entry(scrollable_frame, textvariable=var, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=i+7, column=1, pady=2, sticky="w")

    # Command
    tk.Label(scrollable_frame, text="Command:", font=("Arial", 12, "bold"), bg='#f0f0f0', fg='#333333').grid(row=10, column=0, columnspan=5, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.schematic_command, width=30, bg='#ffffff', font=("Arial", 10)).grid(row=11, column=0, columnspan=2, pady=2, sticky="w")

    # Generate and Save Button
    tk.Button(scrollable_frame, text="Generate and Save Schematic", command=lambda: generate_schematic(gui), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=12, column=0, columnspan=5, pady=5, sticky="w")

    # View Schematic Button
    def open_viewer_window():
        file_path = filedialog.askopenfilename(
            defaultextension=".schem",
            filetypes=[("Schematic files", "*.schem"), ("All files", "*.*")]
        )
        if file_path:
            threading.Thread(target=lambda: SchematicViewer(file_path).run(), daemon=True).start()
            gui.print_to_text(f"Viewing schematic: {file_path}", "normal")

    tk.Button(scrollable_frame, text="View Schematic in 3D", command=open_viewer_window, font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=13, column=0, columnspan=5, pady=5, sticky="w")