# src/worldedit_tab/command_block_generator/gui.py
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import logging
import gzip
import nbtlib
from .loader import load_schematic
from .converter import generate_block_list, convert_to_command_blocks


def open_converter_window(parent):
    window = tk.Toplevel(parent)
    window.title("Schematic → Command Blocks Converter")
    window.geometry("900x700")
    window.configure(bg='#f0f0f0')

    file_path_var = tk.StringVar()

    # ── File selection ───────────────────────────────────────────────────────
    top_frame = tk.Frame(window, bg='#f0f0f0')
    top_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(top_frame, text="Schematic File:", font=("Arial", 11), bg='#f0f0f0').pack(side="left")
    tk.Entry(top_frame, textvariable=file_path_var, width=60).pack(side="left", padx=8)
    tk.Button(top_frame, text="Browse", command=lambda: _browse_file(file_path_var), bg='#2196F3', fg='white').pack(side="left")

    # ── Player position ──────────────────────────────────────────────────────
    pos_frame = tk.Frame(window, bg='#f0f0f0')
    pos_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(pos_frame, text="Player position when copied (X Y Z):", font=("Arial", 11), bg='#f0f0f0').pack(side="left")
    player_x = tk.StringVar(value="0")
    player_y = tk.StringVar(value="64")
    player_z = tk.StringVar(value="0")
    tk.Entry(pos_frame, textvariable=player_x, width=12).pack(side="left", padx=4)
    tk.Entry(pos_frame, textvariable=player_y, width=12).pack(side="left", padx=4)
    tk.Entry(pos_frame, textvariable=player_z, width=12).pack(side="left", padx=4)

    # ── Output area ──────────────────────────────────────────────────────────
    text_list = tk.Text(window, height=25, font=("Consolas", 10))
    text_list.pack(fill="both", expand=True, padx=10, pady=5)

    # ── Buttons ──────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(window, bg='#f0f0f0')
    btn_frame.pack(fill="x", padx=10, pady=8)

    def generate_list():
        fp = file_path_var.get()
        if not fp:
            text_list.insert("end", "→ No file selected.\n")
            return

        data, debug = load_schematic(fp)

        text_list.delete("1.0", "end")
        text_list.insert("end", "═ Debug & Loading Report ════════════════════════════════\n\n")

        show_debug_window(debug)

        if debug["error"]:
            text_list.insert("end", f"Loading failed:\n{debug['error']}\n\n")
            return

        if debug["success"]:
            text_list.insert("end", "File loaded successfully.\n")
            text_list.insert("end", f"Object type: {debug['loaded_type']}\n")
            text_list.insert("end", f"Width present: {debug['has_width']}\n")

            if debug['width_value'] is not None:
                text_list.insert("end", f"Width = {debug['width_value']}\n")

            try:
                px = float(player_x.get())
                py = float(player_y.get())
                pz = float(player_z.get())
                lines = generate_block_list(data, (px, py, pz))
                text_list.insert("end", f"\nFound {len(lines)} non-air blocks.\n\n")
                text_list.insert("end", "\n".join(lines[:50]) + "\n")
                if len(lines) > 50:
                    text_list.insert("end", f"... and {len(lines)-50} more\n")
            except Exception as e:
                text_list.insert("end", f"Error generating block list:\n{type(e).__name__}: {str(e)}\n")
        else:
            text_list.insert("end", "No data returned.\n")

    def generate_schematic():
        fp = file_path_var.get()
        if not fp:
            text_list.insert("end", "→ No file selected.\n")
            return

        data, debug = load_schematic(fp)
        if not debug["success"]:
            text_list.insert("end", f"Cannot convert – loading failed:\n{debug['error']}\n")
            return

        try:
            px = float(player_x.get())
            py = float(player_y.get())
            pz = float(player_z.get())
            new_root = convert_to_command_blocks(data, (px, py, pz))

            out_path = filedialog.asksaveasfilename(
                defaultextension=".schem",
                filetypes=[("Schematic", "*.schem"), ("All Files", "*.*")],
                title="Save Command Block Schematic (gzipped .schem)"
            )
            if not out_path:
                text_list.insert("end", "→ Save cancelled.\n")
                return

            # Explicit gzip write – fixes "Not in GZIP format" in WorldEdit
            new_schem = nbtlib.File(new_root)
            with open(out_path, 'wb') as raw_file:
                with gzip.GzipFile(fileobj=raw_file, mode='wb', compresslevel=9) as gz:
                    new_schem.write(gz)

            text_list.insert("end", f"\nSuccessfully saved gzipped .schem:\n{out_path}\n")
            text_list.insert("end", "Try in-game: /schem load <filename> (without .schem)\n")

        except Exception as e:
            text_list.insert("end", f"Error during conversion or save:\n{type(e).__name__}: {str(e)}\n")

    tk.Button(btn_frame, text="Show Block List + Debug", command=generate_list, bg='#4CAF50', fg='white', width=22).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Generate Command Block Schematic", command=generate_schematic, bg='#FF5722', fg='white', width=30).pack(side="left", padx=6)


def show_debug_window(debug_info):
    """Open a separate window with detailed loading debug info"""
    dbg_win = tk.Toplevel()
    dbg_win.title("Schematic Load Debug")
    dbg_win.geometry("800x600")
    dbg_win.configure(bg='#f8f8f8')

    text = scrolledtext.ScrolledText(dbg_win, font=("Consolas", 10), wrap=tk.WORD)
    text.pack(fill="both", expand=True, padx=10, pady=10)

    text.insert(tk.END, "Schematic Debug Report\n")
    text.insert(tk.END, "═══════════════════════\n\n")

    for key, value in debug_info.items():
        if key == "str_preview":
            text.insert(tk.END, f"{key}:\n{'─'*60}\n{value}\n\n")
        else:
            text.insert(tk.END, f"{key: <18}: {value}\n")

    text.config(state='disabled')


def _browse_file(var: tk.StringVar):
    path = filedialog.askopenfilename(
        filetypes=[("Schematic files", "*.schem"), ("All files", "*.*")]
    )
    if path:
        var.set(path)