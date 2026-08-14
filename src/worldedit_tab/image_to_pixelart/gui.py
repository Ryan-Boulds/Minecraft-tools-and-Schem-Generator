# worldedit_tab/image_to_pixelart/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from ..common.image_preview import create_preview_widget
from ..resource_pack_scanner.scanner import load_palette
from .converter import (
    load_source_image,
    build_pixel_grid,
    match_palette,
    locked_dimension,
    generate_direct_block_schem,
)


def create_image_to_pixelart_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(6, weight=1)

    state = {"base_image": None, "image": None, "rotation": 0,
             "palette": None, "orig_w": None, "orig_h": None, "updating": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Image \u2192 Pixel Art (direct blocks)", font=("Arial", 14, "bold"),
             bg='#f0f0f0').pack(side="left", padx=20)

    # Palette file
    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=50).pack(side="left", padx=8)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    # Image file
    img_frame = tk.Frame(frame, bg='#f0f0f0')
    img_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
    tk.Label(img_frame, text="Image File:", bg='#f0f0f0').pack(side="left")
    image_path_var = tk.StringVar()
    tk.Entry(img_frame, textvariable=image_path_var, width=50).pack(side="left", padx=8)
    tk.Button(img_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_image(image_path_var, state, status_var, lambda: _after_image_change())
              ).pack(side="left")

    # Size controls
    size_frame = tk.Frame(frame, bg='#f0f0f0')
    size_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=4)

    tk.Label(size_frame, text="Width (px/blocks):", bg='#f0f0f0').pack(side="left")
    width_var = tk.StringVar(value="32")
    tk.Entry(size_frame, textvariable=width_var, width=6).pack(side="left", padx=(4, 16))

    tk.Label(size_frame, text="Height (px/blocks):", bg='#f0f0f0').pack(side="left")
    height_var = tk.StringVar(value="32")
    tk.Entry(size_frame, textvariable=height_var, width=6).pack(side="left", padx=(4, 16))

    lock_aspect_var = tk.BooleanVar(value=True)
    tk.Checkbutton(size_frame, text="Lock aspect ratio", variable=lock_aspect_var,
                   bg='#f0f0f0').pack(side="left", padx=8)

    # --- preview, to the right of the controls ---
    def _do_rotate():
        if not state["base_image"]:
            return
        state["rotation"] = (state["rotation"] + 90) % 360
        _apply_rotation()
        if lock_aspect_var.get():
            try:
                w = int(width_var.get())
                _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
                state["updating"] = True
                height_var.set(str(h))
                state["updating"] = False
            except ValueError:
                pass
        _refresh_preview()

    def _load_palette_preview():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first.")
            return
        if not state["image"]:
            messagebox.showwarning("No image", "Load an image first.")
            return
        try:
            tw, th = int(width_var.get()), int(height_var.get())
            if tw < 1 or th < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid size", "Width and height must be positive integers.")
            return
        pixel_grid = build_pixel_grid(state["image"], tw, th)
        block_grid = match_palette(pixel_grid, state["palette"])
        set_palette_preview(block_grid, state["palette"])

    preview_container, refresh_preview_widget, set_palette_preview = create_preview_widget(
        frame, on_rotate=_do_rotate, on_load_palette_preview=_load_palette_preview)
    preview_container.grid(row=1, column=1, rowspan=4, sticky="n", padx=(10, 10), pady=4)

    def _refresh_preview():
        try:
            tw, th = int(width_var.get()), int(height_var.get())
        except ValueError:
            tw, th = state["orig_w"], state["orig_h"]
        refresh_preview_widget(state["image"], tw, th)

    def _apply_rotation():
        state["image"] = state["base_image"].rotate(-state["rotation"], expand=True)
        state["orig_w"], state["orig_h"] = state["image"].size

    def _after_image_change():
        state["rotation"] = 0
        _apply_rotation()
        # keep whatever's in the width field, recompute height to match if locked
        if lock_aspect_var.get():
            try:
                w = int(width_var.get())
                _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
                state["updating"] = True
                height_var.set(str(h))
                state["updating"] = False
            except ValueError:
                pass
        _refresh_preview()

    def _on_width_change(*_):
        if state["updating"]:
            return
        if lock_aspect_var.get() and state["orig_w"]:
            try:
                w = int(width_var.get())
                _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
                state["updating"] = True
                height_var.set(str(h))
                state["updating"] = False
            except ValueError:
                pass
        _refresh_preview()

    def _on_height_change(*_):
        if state["updating"]:
            return
        if lock_aspect_var.get() and state["orig_w"]:
            try:
                h = int(height_var.get())
                w, _ = locked_dimension(state["orig_w"], state["orig_h"], known_h=h)
                state["updating"] = True
                width_var.set(str(w))
                state["updating"] = False
            except ValueError:
                pass
        _refresh_preview()

    width_var.trace_add("write", _on_width_change)
    height_var.trace_add("write", _on_height_change)

    # Facing
    facing_frame = tk.Frame(frame, bg='#f0f0f0')
    facing_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=4)
    tk.Label(facing_frame, text="Facing:", bg='#f0f0f0').pack(side="left")
    facing_var = tk.StringVar(value="north")
    ttk.Combobox(facing_frame, textvariable=facing_var, values=["north", "south", "east", "west"],
                 width=10, state="readonly").pack(side="left", padx=(4, 20))

    # Status / output
    status_var = tk.StringVar(value="Load a palette and an image to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 0))

    text_out = tk.Text(frame, height=12, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=10, pady=8)

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

        new_root = generate_direct_block_schem(block_grid, facing)

        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem", filetypes=[("Schematic", "*.schem")],
            title="Save block pixel art schematic", initialdir=get_dir("schem_output"))
        if not out_path:
            return

        try:
            save_schematic(new_root, out_path)
            remember("schem_output", out_path)
            used_blocks = sorted({b for row in block_grid for b in row if b is not None})
            status_var.set(f"Saved {target_w}x{target_h} pixel art to {out_path} ({len(used_blocks)} unique blocks)")
            text_out.delete("1.0", "end")
            text_out.insert("end", f"Saved: {out_path}\nDimensions: {target_w} x {target_h}\n"
                                    f"Facing: {facing}\nUnique blocks used: {len(used_blocks)}\n\n"
                                    + "\n".join(used_blocks[:100]))
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Pixel art schematic saved to {out_path}", "normal")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
    tk.Button(btn_frame, text="Generate Pixel Art Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=28).pack(side="left", padx=6)

    return frame


def _browse_palette(var, state, status_var):
    path = filedialog.askopenfilename(filetypes=[("Block color palette", "*.json")],
                                       **get_initial_file_args("palette_json"))
    if not path:
        return
    try:
        state["palette"] = load_palette(path)
        var.set(path)
        remember_file("palette_json", path)
        status_var.set(f"Loaded palette: {len(state['palette'])} block colors.")
    except Exception as e:
        messagebox.showerror("Failed to load palette", str(e))


def _browse_image(var, state, status_var, on_loaded):
    path = filedialog.askopenfilename(
        filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        initialdir=get_dir("image_file"))
    if not path:
        return
    try:
        image = load_source_image(path)
        state["base_image"] = image
        var.set(path)
        remember("image_file", path)
        status_var.set(f"Loaded image: {image.size[0]} x {image.size[1]} px")
        on_loaded()
    except Exception as e:
        messagebox.showerror("Failed to load image", str(e))
