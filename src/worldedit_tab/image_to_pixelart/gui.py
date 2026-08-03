# worldedit_tab/image_to_pixelart/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember
from ..resource_pack_scanner.scanner import load_palette
from .converter import (
    load_source_image,
    build_pixel_grid,
    match_palette,
    locked_dimension,
    generate_direct_block_schem,
    generate_command_block_wall_schem,
)


def create_image_to_pixelart_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(6, weight=1)

    state = {"palette": None, "image": None, "orig_w": None, "orig_h": None, "updating": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Image \u2192 Pixel Art", font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    # Palette file
    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=4)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=50).pack(side="left", padx=8, fill="x", expand=True)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    # Image file
    img_frame = tk.Frame(frame, bg='#f0f0f0')
    img_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=4)
    tk.Label(img_frame, text="Image File:", bg='#f0f0f0').pack(side="left")
    image_path_var = tk.StringVar()
    tk.Entry(img_frame, textvariable=image_path_var, width=50).pack(side="left", padx=8, fill="x", expand=True)
    tk.Button(img_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_image(image_path_var, state, width_var, height_var, status_var)).pack(side="left")

    # Size controls
    size_frame = tk.Frame(frame, bg='#f0f0f0')
    size_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=4)

    tk.Label(size_frame, text="Width (px/blocks):", bg='#f0f0f0').pack(side="left")
    width_var = tk.StringVar(value="32")
    width_entry = tk.Entry(size_frame, textvariable=width_var, width=6)
    width_entry.pack(side="left", padx=(4, 16))

    tk.Label(size_frame, text="Height (px/blocks):", bg='#f0f0f0').pack(side="left")
    height_var = tk.StringVar(value="32")
    height_entry = tk.Entry(size_frame, textvariable=height_var, width=6)
    height_entry.pack(side="left", padx=(4, 16))

    lock_aspect_var = tk.BooleanVar(value=True)
    tk.Checkbutton(size_frame, text="Lock aspect ratio", variable=lock_aspect_var,
                   bg='#f0f0f0').pack(side="left", padx=8)

    def _on_width_change(*_):
        if state["updating"] or not lock_aspect_var.get() or not state["orig_w"]:
            return
        try:
            w = int(width_var.get())
        except ValueError:
            return
        _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
        state["updating"] = True
        height_var.set(str(h))
        state["updating"] = False

    def _on_height_change(*_):
        if state["updating"] or not lock_aspect_var.get() or not state["orig_w"]:
            return
        try:
            h = int(height_var.get())
        except ValueError:
            return
        w, _ = locked_dimension(state["orig_w"], state["orig_h"], known_h=h)
        state["updating"] = True
        width_var.set(str(w))
        state["updating"] = False

    width_var.trace_add("write", _on_width_change)
    height_var.trace_add("write", _on_height_change)

    # Facing + mode
    mode_frame = tk.Frame(frame, bg='#f0f0f0')
    mode_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=4)

    tk.Label(mode_frame, text="Facing:", bg='#f0f0f0').pack(side="left")
    facing_var = tk.StringVar(value="north")
    ttk.Combobox(mode_frame, textvariable=facing_var, values=["north", "south", "east", "west"],
                 width=10, state="readonly").pack(side="left", padx=(4, 20))

    convert_to_blocks_var = tk.BooleanVar(value=True)
    tk.Checkbutton(mode_frame, text="Convert to blocks (uncheck for a command block wall)",
                   variable=convert_to_blocks_var, bg='#f0f0f0',
                   command=lambda: _toggle_pos_state()).pack(side="left")

    # Player position (only meaningful in command-block-wall mode)
    pos_frame = tk.Frame(frame, bg='#f0f0f0')
    pos_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=4)
    tk.Label(pos_frame, text="Player Position when scanned (X Y Z):", bg='#f0f0f0').pack(side="left")
    player_x = tk.StringVar(value="0")
    player_y = tk.StringVar(value="64")
    player_z = tk.StringVar(value="0")
    px_entry = tk.Entry(pos_frame, textvariable=player_x, width=8)
    py_entry = tk.Entry(pos_frame, textvariable=player_y, width=8)
    pz_entry = tk.Entry(pos_frame, textvariable=player_z, width=8)
    px_entry.pack(side="left", padx=4)
    py_entry.pack(side="left", padx=4)
    pz_entry.pack(side="left", padx=4)

    def _toggle_pos_state():
        state_ = "disabled" if convert_to_blocks_var.get() else "normal"
        for e in (px_entry, py_entry, pz_entry):
            e.config(state=state_)

    _toggle_pos_state()

    # Status / output
    status_var = tk.StringVar(value="Load a palette and an image to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=6, column=0, columnspan=4, sticky="w", padx=12, pady=(6, 0))

    text_out = tk.Text(frame, height=12, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=7, column=0, columnspan=4, sticky="nsew", padx=10, pady=8)

    def do_generate():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first (from the Resource Pack Scanner tab).")
            return
        if not state["image"]:
            messagebox.showwarning("No image", "Load an image first.")
            return
        try:
            target_w = int(width_var.get())
            target_h = int(height_var.get())
            if target_w < 1 or target_h < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid size", "Width and height must be positive integers.")
            return

        pixel_grid = build_pixel_grid(state["image"], target_w, target_h)
        block_grid = match_palette(pixel_grid, state["palette"])
        facing = facing_var.get()

        if convert_to_blocks_var.get():
            new_root = generate_direct_block_schem(block_grid, facing)
            title = "Save block pixel art schematic"
        else:
            try:
                pos = (float(player_x.get()), float(player_y.get()), float(player_z.get()))
            except ValueError:
                messagebox.showwarning("Invalid position", "Player X/Y/Z must be numbers.")
                return
            new_root = generate_command_block_wall_schem(block_grid, facing, pos)
            title = "Save command block wall schematic"

        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem", filetypes=[("Schematic", "*.schem")], title=title,
            initialdir=get_dir("schem_output"))
        if not out_path:
            return

        try:
            save_schematic(new_root, out_path)
            remember("schem_output", out_path)
            used_blocks = sorted({b for row in block_grid for b in row if b is not None})
            status_var.set(f"Saved {target_w}x{target_h} pixel art to {out_path} ({len(used_blocks)} unique blocks)")
            text_out.delete("1.0", "end")
            text_out.insert("end", f"Saved: {out_path}\nDimensions: {target_w} x {target_h}\n"
                                    f"Facing: {facing}\nMode: {'Direct blocks' if convert_to_blocks_var.get() else 'Command block wall'}\n"
                                    f"Unique blocks used: {len(used_blocks)}\n\n" + "\n".join(used_blocks[:100]))
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Pixel art schematic saved to {out_path}", "normal")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=8, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    tk.Button(btn_frame, text="Generate Pixel Art Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=28).pack(side="left", padx=6)

    return frame


def _browse_palette(var, state, status_var):
    path = filedialog.askopenfilename(filetypes=[("Block color palette", "*.json")],
                                       initialdir=get_dir("palette_json"))
    if not path:
        return
    try:
        state["palette"] = load_palette(path)
        var.set(path)
        remember("palette_json", path)
        status_var.set(f"Loaded palette: {len(state['palette'])} block colors.")
    except Exception as e:
        messagebox.showerror("Failed to load palette", str(e))


def _browse_image(var, state, width_var, height_var, status_var):
    path = filedialog.askopenfilename(
        filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        initialdir=get_dir("image_file"))
    if not path:
        return
    try:
        image = load_source_image(path)
        state["image"] = image
        state["orig_w"], state["orig_h"] = image.size
        var.set(path)
        remember("image_file", path)
        status_var.set(f"Loaded image: {image.size[0]} x {image.size[1]} px")
    except Exception as e:
        messagebox.showerror("Failed to load image", str(e))
