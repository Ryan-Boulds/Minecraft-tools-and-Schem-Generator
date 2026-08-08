# worldedit_tab/convert_to_command_blocks/gui.py

import tkinter as tk
from tkinter import ttk, filedialog

from ..common.schem_io import load_schematic, save_schematic
from .converter import (
    generate_block_list,
    convert_to_command_blocks,
    convert_to_command_block_wall,
    convert_to_command_block_wall_projected,
)


def create_converter_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(4, weight=1)

    # Header
    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(8, 12))

    tk.Label(header, text="Schematic \u2192 Command Blocks Converter",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    # File selection
    top_frame = tk.Frame(frame, bg='#f0f0f0')
    top_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=6)

    tk.Label(top_frame, text="Schematic File:", bg='#f0f0f0').pack(side="left")
    file_path_var = tk.StringVar()
    tk.Entry(top_frame, textvariable=file_path_var, width=60).pack(side="left", padx=8)
    tk.Button(top_frame, text="Browse", command=lambda: _browse_file(file_path_var),
              bg='#2196F3', fg='white').pack(side="left")

    # Player position
    pos_frame = tk.Frame(frame, bg='#f0f0f0')
    pos_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=6)

    tk.Label(pos_frame, text="Player Position (X Y Z):", bg='#f0f0f0').pack(side="left")
    player_x = tk.StringVar(value="0")
    player_y = tk.StringVar(value="64")
    player_z = tk.StringVar(value="0")
    tk.Entry(pos_frame, textvariable=player_x, width=8).pack(side="left", padx=4)
    tk.Entry(pos_frame, textvariable=player_y, width=8).pack(side="left", padx=4)
    tk.Entry(pos_frame, textvariable=player_z, width=8).pack(side="left", padx=4)

    # Controls
    wall_frame = tk.Frame(frame, bg='#f0f0f0')
    wall_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=6)

    tk.Label(wall_frame, text="Wall Width:", bg='#f0f0f0').pack(side="left")
    wall_width_var = tk.StringVar(value="5")
    tk.Entry(wall_frame, textvariable=wall_width_var, width=6).pack(side="left", padx=8)

    tk.Label(wall_frame, text="Facing:", bg='#f0f0f0').pack(side="left", padx=12)
    facing_var = tk.StringVar(value="north")
    ttk.Combobox(wall_frame, textvariable=facing_var,
                 values=["north", "south", "east", "west"],
                 width=10, state="readonly").pack(side="left")

    # Output
    text_list = tk.Text(frame, height=18, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_list.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=8)

    # Buttons
    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

    def generate_list():
        _run_generator(text_list, file_path_var, player_x, player_y, player_z, wall_width_var, facing_var, mode="list")

    def generate_original():
        _run_generator(text_list, file_path_var, player_x, player_y, player_z, wall_width_var, facing_var, mode="original")

    def generate_wall():
        _run_generator(text_list, file_path_var, player_x, player_y, player_z, wall_width_var, facing_var, mode="wall")

    def generate_projected():
        _run_generator(text_list, file_path_var, player_x, player_y, player_z, wall_width_var, facing_var, mode="projected")

    tk.Button(btn_frame, text="Show Block List", command=generate_list,
              bg='#4CAF50', fg='white', width=18).pack(side="left", padx=6)

    tk.Button(btn_frame, text="Generate Original Shape", command=generate_original,
              bg='#FF5722', fg='white', width=22).pack(side="left", padx=6)

    tk.Button(btn_frame, text="Generate Command Block WALL", command=generate_wall,
              bg='#673AB7', fg='white', width=26).pack(side="left", padx=6)

    tk.Button(btn_frame, text="Generate PROJECTED Wall", command=generate_projected,
              bg='#9C27B0', fg='white', width=26).pack(side="left", padx=6)

    return frame


def _run_generator(text_widget, file_var, px_var, py_var, pz_var, ww_var, facing_var, mode):
    text_widget.delete("1.0", "end")
    fp = file_var.get()
    if not fp:
        text_widget.insert("end", "No schematic file selected.\n")
        return

    data, debug = load_schematic(fp)
    if not debug["success"]:
        text_widget.insert("end", f"Failed to load schematic: {debug['error']}\n")
        return
    if debug["wrapped"] is False:
        text_widget.insert("end", "Note: this file is missing the standard 'Schematic' NBT wrapper "
                                   "(likely made by an old version of this app). Loaded it anyway.\n\n")

    try:
        px = float(px_var.get())
        py = float(py_var.get())
        pz = float(pz_var.get())
    except:
        text_widget.insert("end", "Invalid player position values.\n")
        return

    if mode == "list":
        lines = generate_block_list(data, (px, py, pz))
        text_widget.insert("end", f"Found {len(lines)} non-air blocks.\n\n")
        text_widget.insert("end", "\n".join(lines[:150]) + ("\n..." if len(lines) > 150 else "") + "\n")
        return

    try:
        wall_width = int(ww_var.get())
    except:
        wall_width = 5

    facing = facing_var.get()

    if mode == "original":
        new_root = convert_to_command_blocks(data, (px, py, pz))
    elif mode == "wall":
        new_root = convert_to_command_block_wall(data, (px, py, pz), wall_width, facing)
    elif mode == "projected":
        new_root = convert_to_command_block_wall_projected(data, (px, py, pz), facing)
    else:
        text_widget.insert("end", f"Unknown mode: {mode}\n")
        return

    out_path = filedialog.asksaveasfilename(
        defaultextension=".schem",
        filetypes=[("Schematic", "*.schem")],
        title="Save converted schematic"
    )
    if not out_path:
        text_widget.insert("end", "Save cancelled.\n")
        return

    try:
        save_schematic(new_root, out_path)
        text_widget.insert("end", f"Successfully saved:\n{out_path}\n")
    except Exception as e:
        text_widget.insert("end", f"Error saving file: {e}\n")


def _browse_file(var: tk.StringVar):
    path = filedialog.askopenfilename(filetypes=[("Schematic files", "*.schem")])
    if path:
        var.set(path)
