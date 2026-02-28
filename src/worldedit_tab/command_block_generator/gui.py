# src/worldedit_tab/command_block_generator/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import gzip
import nbtlib

from .loader import load_schematic
from .converter import (
    generate_block_list,
    convert_to_command_blocks,
    convert_to_command_block_wall
)


def open_converter_window(parent):
    window = tk.Toplevel(parent)
    window.title("Schematic → Command Blocks Converter")
    window.geometry("950x720")
    window.configure(bg='#f0f0f0')

    file_path_var = tk.StringVar()

    # File selection
    top_frame = tk.Frame(window, bg='#f0f0f0')
    top_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(top_frame, text="Schematic File:", bg='#f0f0f0').pack(side="left")
    tk.Entry(top_frame, textvariable=file_path_var, width=65).pack(side="left", padx=8)
    tk.Button(top_frame, text="Browse",
              command=lambda: _browse_file(file_path_var),
              bg='#2196F3', fg='white').pack(side="left")

    # Player position
    pos_frame = tk.Frame(window, bg='#f0f0f0')
    pos_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(pos_frame, text="Player Position (X Y Z):",
             bg='#f0f0f0').pack(side="left")

    player_x = tk.StringVar(value="0")
    player_y = tk.StringVar(value="64")
    player_z = tk.StringVar(value="0")

    tk.Entry(pos_frame, textvariable=player_x, width=10).pack(side="left", padx=3)
    tk.Entry(pos_frame, textvariable=player_y, width=10).pack(side="left", padx=3)
    tk.Entry(pos_frame, textvariable=player_z, width=10).pack(side="left", padx=3)

    # Wall controls
    wall_frame = tk.Frame(window, bg='#f0f0f0')
    wall_frame.pack(fill="x", padx=10, pady=6)

    tk.Label(wall_frame, text="Wall Width:", bg='#f0f0f0').pack(side="left")
    wall_width_var = tk.StringVar(value="5")
    tk.Entry(wall_frame, textvariable=wall_width_var, width=6).pack(side="left", padx=6)

    tk.Label(wall_frame, text="Facing:", bg='#f0f0f0').pack(side="left", padx=10)
    facing_var = tk.StringVar(value="north")

    ttk.Combobox(
        wall_frame,
        textvariable=facing_var,
        values=["north", "south", "east", "west"],
        width=8,
        state="readonly"
    ).pack(side="left")

    # Output text
    text_list = tk.Text(window, height=25, font=("Consolas", 10))
    text_list.pack(fill="both", expand=True, padx=10, pady=5)

    # Buttons
    btn_frame = tk.Frame(window, bg='#f0f0f0')
    btn_frame.pack(fill="x", padx=10, pady=8)

    def generate_list():
        fp = file_path_var.get()
        if not fp:
            text_list.insert("end", "No file selected.\n")
            return

        data, debug = load_schematic(fp)
        if not debug["success"]:
            text_list.insert("end", f"Load failed: {debug['error']}\n")
            return

        px = float(player_x.get())
        py = float(player_y.get())
        pz = float(player_z.get())

        lines = generate_block_list(data, (px, py, pz))

        text_list.delete("1.0", "end")
        text_list.insert("end", f"Found {len(lines)} non-air blocks.\n\n")
        text_list.insert("end", "\n".join(lines[:100]))

    def save_schematic(new_root):
        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem",
            filetypes=[("Schematic", "*.schem")]
        )
        if not out_path:
            return

        new_schem = nbtlib.File(new_root)
        with open(out_path, 'wb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9) as gz:
                new_schem.write(gz)

        text_list.insert("end", f"\nSaved: {out_path}\n")

    def generate_original():
        fp = file_path_var.get()
        if not fp:
            return

        data, debug = load_schematic(fp)
        if not debug["success"]:
            return

        px = float(player_x.get())
        py = float(player_y.get())
        pz = float(player_z.get())

        new_root = convert_to_command_blocks(data, (px, py, pz))
        save_schematic(new_root)

    def generate_wall():
        fp = file_path_var.get()
        if not fp:
            return

        data, debug = load_schematic(fp)
        if not debug["success"]:
            return

        px = float(player_x.get())
        py = float(player_y.get())
        pz = float(player_z.get())

        wall_width = int(wall_width_var.get())
        facing = facing_var.get()

        new_root = convert_to_command_block_wall(
            data,
            (px, py, pz),
            wall_width,
            facing
        )

        save_schematic(new_root)

    tk.Button(btn_frame, text="Show Block List",
              command=generate_list,
              bg='#4CAF50', fg='white', width=20).pack(side="left", padx=6)

    tk.Button(btn_frame, text="Generate Original Shape",
              command=generate_original,
              bg='#FF5722', fg='white', width=24).pack(side="left", padx=6)

    tk.Button(btn_frame, text="Generate Command Block WALL",
              command=generate_wall,
              bg='#673AB7', fg='white', width=28).pack(side="left", padx=6)


def _browse_file(var: tk.StringVar):
    path = filedialog.askopenfilename(
        filetypes=[("Schematic files", "*.schem")]
    )
    if path:
        var.set(path)