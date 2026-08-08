# worldedit_tab/image_command_blocks/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from ..common.image_preview import create_preview_widget
from ..resource_pack_scanner.scanner import load_palette
from ..image_to_pixelart.converter import (
    load_source_image, build_pixel_grid, match_palette, locked_dimension,
)
from .converter import (
    CORNER_NAMES, compute_corners_fixed_size, compute_corners_stretch,
    generate_command_block_wall_from_corners,
)

CORNER_LABELS = {
    "bottom_left": "Bottom-Left", "bottom_right": "Bottom-Right",
    "top_left": "Top-Left", "top_right": "Top-Right",
}


def create_image_command_blocks_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    state = {"base_image": None, "image": None, "rotation": 0,
             "palette": None, "orig_w": None, "orig_h": None, "updating": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Image \u2192 Command Blocks (place by coordinates)",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Always generates a command-block wall (for the direct-block picture, use the\n"
                  "Image to Pixel Art tab instead). Image left edge \u2192 lowest horizontal coordinate,\n"
                  "top edge \u2192 highest Y. Which axis is \"horizontal\" depends on facing: North/South \u2192 X,\n"
                  "East/West \u2192 Z.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    # --- palette / image ---
    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=46).pack(side="left", padx=8)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    img_frame = tk.Frame(frame, bg='#f0f0f0')
    img_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(img_frame, text="Image File:", bg='#f0f0f0').pack(side="left")
    image_path_var = tk.StringVar()
    tk.Entry(img_frame, textvariable=image_path_var, width=46).pack(side="left", padx=8)
    tk.Button(img_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_image(image_path_var, state, status_var, lambda: _after_image_change())
              ).pack(side="left")

    def _do_rotate():
        if not state["base_image"]:
            return
        state["rotation"] = (state["rotation"] + 90) % 360
        _apply_rotation()
        if mode_var.get() == "fixed" and fixed_lock_var.get():
            try:
                w = int(fixed_w_var.get())
                _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
                state["updating"] = True
                fixed_h_var.set(str(h))
                state["updating"] = False
            except ValueError:
                pass
        _update_corners_preview()

    preview_container, refresh_preview_widget = create_preview_widget(frame, on_rotate=_do_rotate)
    preview_container.grid(row=2, column=1, rowspan=5, sticky="n", padx=(10, 10), pady=4)
    frame.columnconfigure(1, weight=0)

    def _apply_rotation():
        state["image"] = state["base_image"].rotate(-state["rotation"], expand=True)
        state["orig_w"], state["orig_h"] = state["image"].size

    def _after_image_change():
        state["rotation"] = 0
        _apply_rotation()
        _update_corners_preview()

    # --- facing ---
    facing_frame = tk.Frame(frame, bg='#f0f0f0')
    facing_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Label(facing_frame, text="Facing:", bg='#f0f0f0').pack(side="left")
    facing_var = tk.StringVar(value="north")
    facing_combo = ttk.Combobox(facing_frame, textvariable=facing_var,
                                 values=["north", "south", "east", "west"], width=10, state="readonly")
    facing_combo.pack(side="left", padx=(4, 0))

    # --- mode selector ---
    mode_var = tk.StringVar(value="fixed")
    mode_frame = tk.Frame(frame, bg='#f0f0f0')
    mode_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Radiobutton(mode_frame, text="Fixed size \u2014 place by one corner (scale locked)",
                   variable=mode_var, value="fixed", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")
    tk.Radiobutton(mode_frame, text="Stretch to fit two coordinates (must stay 2D)",
                   variable=mode_var, value="stretch", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")

    # --- FIXED mode fields ---
    fixed_frame = tk.Frame(frame, bg='#f0f0f0')
    fixed_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=4)

    size_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    size_row.pack(fill="x", pady=2)
    tk.Label(size_row, text="Width (blocks):", bg='#f0f0f0').pack(side="left")
    fixed_w_var = tk.StringVar(value="32")
    tk.Entry(size_row, textvariable=fixed_w_var, width=6).pack(side="left", padx=(4, 16))
    tk.Label(size_row, text="Height (blocks):", bg='#f0f0f0').pack(side="left")
    fixed_h_var = tk.StringVar(value="32")
    tk.Entry(size_row, textvariable=fixed_h_var, width=6).pack(side="left", padx=(4, 16))
    fixed_lock_var = tk.BooleanVar(value=True)
    tk.Checkbutton(size_row, text="Lock aspect ratio", variable=fixed_lock_var, bg='#f0f0f0').pack(side="left")

    anchor_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_row.pack(fill="x", pady=(8, 2))
    tk.Label(anchor_row, text="Anchor corner:", bg='#f0f0f0').pack(side="left")
    anchor_corner_var = tk.StringVar(value="bottom_left")
    ttk.Combobox(anchor_row, textvariable=anchor_corner_var,
                 values=list(CORNER_NAMES), width=14, state="readonly",
                 ).pack(side="left", padx=(4, 16))

    anchor_xyz_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_xyz_row.pack(fill="x", pady=2)
    tk.Label(anchor_xyz_row, text="Anchor X Y Z:", bg='#f0f0f0').pack(side="left")
    anchor_x_var = tk.StringVar(value="0")
    anchor_y_var = tk.StringVar(value="64")
    anchor_z_var = tk.StringVar(value="0")
    tk.Entry(anchor_xyz_row, textvariable=anchor_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_z_var, width=8).pack(side="left", padx=4)

    # --- STRETCH mode fields ---
    stretch_frame = tk.Frame(frame, bg='#f0f0f0')
    stretch_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=4)

    a_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    a_row.pack(fill="x", pady=2)
    tk.Label(a_row, text="Corner A  X Y Z:", bg='#f0f0f0').pack(side="left")
    a_x_var, a_y_var, a_z_var = tk.StringVar(value="0"), tk.StringVar(value="64"), tk.StringVar(value="0")
    tk.Entry(a_row, textvariable=a_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(a_row, textvariable=a_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(a_row, textvariable=a_z_var, width=8).pack(side="left", padx=4)

    b_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    b_row.pack(fill="x", pady=2)
    tk.Label(b_row, text="Corner B (diagonal) X Y Z:", bg='#f0f0f0').pack(side="left")
    b_x_var, b_y_var, b_z_var = tk.StringVar(value="31"), tk.StringVar(value="95"), tk.StringVar(value="0")
    tk.Entry(b_row, textvariable=b_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(b_row, textvariable=b_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(b_row, textvariable=b_z_var, width=8).pack(side="left", padx=4)

    stretch_lock_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    stretch_lock_row.pack(fill="x", pady=(8, 2))
    stretch_lock_var = tk.BooleanVar(value=False)
    tk.Checkbutton(stretch_lock_row, text="Lock aspect ratio, based on:", variable=stretch_lock_var,
                   bg='#f0f0f0').pack(side="left")
    stretch_base_var = tk.StringVar(value="horizontal")
    base_h_radio = tk.Radiobutton(stretch_lock_row, text="Horizontal", variable=stretch_base_var,
                                   value="horizontal", bg='#f0f0f0')
    base_v_radio = tk.Radiobutton(stretch_lock_row, text="Vertical", variable=stretch_base_var,
                                   value="vertical", bg='#f0f0f0')
    base_h_radio.pack(side="left", padx=(6, 2))
    base_v_radio.pack(side="left")
    tk.Label(stretch_lock_row, text="(unchecked = ignore aspect ratio, stretch freely)",
             bg='#f0f0f0', fg='#777777').pack(side="left", padx=8)

    def _switch_mode():
        if mode_var.get() == "fixed":
            stretch_frame.grid_remove()
            fixed_frame.grid()
        else:
            fixed_frame.grid_remove()
            stretch_frame.grid()
        _update_corners_preview()

    # --- corners preview (read-only, live) ---
    preview_frame = tk.Frame(frame, bg='#eef1f5', bd=1, relief="solid")
    preview_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(10, 6))
    preview_var = tk.StringVar(value="Corners will appear here once the image and coordinates are set.")
    tk.Label(preview_frame, textvariable=preview_var, bg='#eef1f5', justify="left",
             font=("Consolas", 10), anchor="w").pack(fill="x", padx=10, pady=8)

    def _update_corners_preview(*_):
        try:
            corners = _compute_corners_or_none()
        except Exception:
            corners = None
        if corners is None:
            refresh_preview_widget(state["image"], state["orig_w"], state["orig_h"])
            return
        refresh_preview_widget(state["image"], corners["width_blocks"], corners["height_blocks"])
        lines = [
            f"Width x Height: {corners['width_blocks']} x {corners['height_blocks']} blocks   "
            f"(depth coord: {corners['depth']})",
            f"Bottom-Left:  {corners['bottom_left']}      Bottom-Right: {corners['bottom_right']}",
            f"Top-Left:     {corners['top_left']}      Top-Right:    {corners['top_right']}",
        ]
        if corners.get("depth_mismatch"):
            lines.append("\u26a0 Corner A and Corner B don't agree on the depth axis -- using Corner A's value.")
        preview_var.set("\n".join(lines))

    def _compute_corners_or_none():
        facing = facing_var.get()
        if mode_var.get() == "fixed":
            try:
                w = int(fixed_w_var.get())
                h = int(fixed_h_var.get())
                ax = float(anchor_x_var.get())
                ay = float(anchor_y_var.get())
                az = float(anchor_z_var.get())
            except ValueError:
                return None
            return compute_corners_fixed_size(anchor_corner_var.get(), (int(ax), int(ay), int(az)),
                                               w, h, facing)
        else:
            try:
                ax, ay, az = float(a_x_var.get()), float(a_y_var.get()), float(a_z_var.get())
                bx, by, bz = float(b_x_var.get()), float(b_y_var.get()), float(b_z_var.get())
            except ValueError:
                return None
            orig_w = state["orig_w"] or 1
            orig_h = state["orig_h"] or 1
            return compute_corners_stretch((int(ax), int(ay), int(az)), (int(bx), int(by), int(bz)),
                                            facing, orig_w, orig_h,
                                            lock_aspect=stretch_lock_var.get(),
                                            base_on=stretch_base_var.get())

    # aspect-lock for fixed mode's width/height fields (same pattern as Image to Pixel Art)
    def _on_fixed_w(*_):
        if state["updating"] or not fixed_lock_var.get() or not state["orig_w"]:
            _update_corners_preview()
            return
        try:
            w = int(fixed_w_var.get())
        except ValueError:
            return
        _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
        state["updating"] = True
        fixed_h_var.set(str(h))
        state["updating"] = False
        _update_corners_preview()

    def _on_fixed_h(*_):
        if state["updating"] or not fixed_lock_var.get() or not state["orig_w"]:
            _update_corners_preview()
            return
        try:
            h = int(fixed_h_var.get())
        except ValueError:
            return
        w, _ = locked_dimension(state["orig_w"], state["orig_h"], known_h=h)
        state["updating"] = True
        fixed_w_var.set(str(w))
        state["updating"] = False
        _update_corners_preview()

    fixed_w_var.trace_add("write", _on_fixed_w)
    fixed_h_var.trace_add("write", _on_fixed_h)
    for v in (anchor_x_var, anchor_y_var, anchor_z_var):
        v.trace_add("write", _update_corners_preview)
    for v in (a_x_var, a_y_var, a_z_var, b_x_var, b_y_var, b_z_var):
        v.trace_add("write", _update_corners_preview)
    anchor_corner_var.trace_add("write", _update_corners_preview)
    facing_var.trace_add("write", _update_corners_preview)
    stretch_lock_var.trace_add("write", _update_corners_preview)
    stretch_base_var.trace_add("write", _update_corners_preview)

    # --- status / output ---
    status_var = tk.StringVar(value="Load a palette and an image to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=8, column=0, sticky="w", padx=20, pady=(4, 0))

    text_out = tk.Text(frame, height=8, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=9, column=0, sticky="nsew", padx=20, pady=8)
    frame.rowconfigure(9, weight=1)

    def do_generate():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first.")
            return
        if not state["image"]:
            messagebox.showwarning("No image", "Load an image first.")
            return

        corners = _compute_corners_or_none()
        if corners is None:
            messagebox.showwarning("Invalid coordinates", "Check that all coordinate/size fields are numbers.")
            return

        facing = facing_var.get()
        target_w = corners["width_blocks"]
        target_h = corners["height_blocks"]

        pixel_grid = build_pixel_grid(state["image"], target_w, target_h)
        block_grid = match_palette(pixel_grid, state["palette"])

        new_root = generate_command_block_wall_from_corners(block_grid, facing, corners)

        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem", filetypes=[("Schematic", "*.schem")],
            title="Save command block wall schematic", initialdir=get_dir("schem_output"))
        if not out_path:
            return

        try:
            save_schematic(new_root, out_path)
            remember("schem_output", out_path)
            used_blocks = sorted({b for row in block_grid for b in row if b is not None})
            status_var.set(f"Saved {target_w}x{target_h} command block wall to {out_path}")
            text_out.delete("1.0", "end")
            text_out.insert("end", f"Saved: {out_path}\nFacing: {facing}\nDimensions: {target_w} x {target_h}\n"
                                    f"Bottom-Left corner: {corners['bottom_left']}\n"
                                    f"Top-Right corner: {corners['top_right']}\n"
                                    f"Unique blocks used: {len(used_blocks)}\n")
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Command block wall schematic saved to {out_path}", "normal")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=10, column=0, sticky="ew", padx=20, pady=(0, 10))
    tk.Button(btn_frame, text="Generate Command Block Wall Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=32).pack(side="left")

    _switch_mode()
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
