# worldedit_tab/gif_command_blocks/gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from ..common.image_preview import create_preview_widget
from ..resource_pack_scanner.scanner import load_palette
from ..image_to_pixelart.converter import build_pixel_grid, match_palette, locked_dimension
from ..image_command_blocks.converter import CORNER_NAMES, compute_corners_fixed_size, compute_corners_stretch
from .converter import load_gif_frames, compute_frame_plan, select_kept_frames, generate_gif_command_block_schem

LARGE_STRUCTURE_WARNING = 2000  # heads-up threshold for depth-axis extent; not a hard Minecraft limit like world height was


def create_gif_command_blocks_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    state = {"palette": None, "base_frames": None, "frames": None, "rotation": 0,
              "native_fps": None, "orig_w": None, "orig_h": None, "updating": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="GIF \u2192 Command Blocks (animated)",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Each frame is a full wall of command blocks (and stone, for pixels that didn't change),\n"
                  "connected to the next wall by a repeater relay -- the picture's position genuinely\n"
                  "advances through the world one frame at a time. Repeaters always need a quartz block\n"
                  "directly beneath them; only every other row needs its own relay chain, since a hard-\n"
                  "powered row soft-powers its neighbor rows above and below for free.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    # --- palette / gif ---
    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=46).pack(side="left", padx=8)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    gif_frame = tk.Frame(frame, bg='#f0f0f0')
    gif_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(gif_frame, text="GIF File:", bg='#f0f0f0').pack(side="left")
    gif_path_var = tk.StringVar()
    tk.Entry(gif_frame, textvariable=gif_path_var, width=46).pack(side="left", padx=8)
    tk.Button(gif_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_gif(gif_path_var, state, status_var, target_fps_var, lambda: _after_gif_change())
              ).pack(side="left")

    def _do_rotate():
        if not state["base_frames"]:
            return
        state["rotation"] = (state["rotation"] + 90) % 360
        _apply_rotation()
        if mode_var.get() == "fixed" and lock_var.get():
            try:
                w = int(w_var.get())
                _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
                state["updating"] = True
                h_var.set(str(h))
                state["updating"] = False
            except ValueError:
                pass
        _update_corners_preview()

    preview_container, refresh_preview_widget = create_preview_widget(frame, on_rotate=_do_rotate)
    preview_container.grid(row=2, column=1, rowspan=6, sticky="n", padx=(10, 10), pady=4)
    frame.columnconfigure(1, weight=0)

    def _apply_rotation():
        state["frames"] = [f.rotate(-state["rotation"], expand=True) for f in state["base_frames"]]
        state["orig_w"], state["orig_h"] = state["frames"][0].size

    def _after_gif_change():
        state["rotation"] = 0
        _apply_rotation()
        _update_corners_preview()
        _update_frame_plan()

    # --- size / facing ---
    size_frame = tk.Frame(frame, bg='#f0f0f0')
    size_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(size_frame, text="Width (blocks):", bg='#f0f0f0').pack(side="left")
    w_var = tk.StringVar(value="16")
    tk.Entry(size_frame, textvariable=w_var, width=6).pack(side="left", padx=(4, 16))
    tk.Label(size_frame, text="Height (blocks):", bg='#f0f0f0').pack(side="left")
    h_var = tk.StringVar(value="16")
    tk.Entry(size_frame, textvariable=h_var, width=6).pack(side="left", padx=(4, 16))
    lock_var = tk.BooleanVar(value=True)
    tk.Checkbutton(size_frame, text="Lock aspect ratio", variable=lock_var, bg='#f0f0f0').pack(side="left", padx=(0, 16))
    tk.Label(size_frame, text="Facing:", bg='#f0f0f0').pack(side="left")
    facing_var = tk.StringVar(value="north")
    ttk.Combobox(size_frame, textvariable=facing_var, values=["north", "south", "east", "west"],
                 width=10, state="readonly").pack(side="left", padx=(4, 0))

    # --- corner placement (same model as Image Command Blocks) ---
    mode_var = tk.StringVar(value="fixed")
    mode_frame = tk.Frame(frame, bg='#f0f0f0')
    mode_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Radiobutton(mode_frame, text="Fixed size \u2014 place by one corner (scale locked)",
                   variable=mode_var, value="fixed", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")
    tk.Radiobutton(mode_frame, text="Stretch to fit two coordinates (must stay 2D)",
                   variable=mode_var, value="stretch", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")

    fixed_frame = tk.Frame(frame, bg='#f0f0f0')
    fixed_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=4)
    anchor_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_row.pack(fill="x", pady=2)
    tk.Label(anchor_row, text="Anchor corner:", bg='#f0f0f0').pack(side="left")
    anchor_corner_var = tk.StringVar(value="bottom_left")
    ttk.Combobox(anchor_row, textvariable=anchor_corner_var, values=list(CORNER_NAMES),
                 width=14, state="readonly").pack(side="left", padx=(4, 16))
    anchor_xyz_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_xyz_row.pack(fill="x", pady=2)
    tk.Label(anchor_xyz_row, text="Anchor X Y Z:", bg='#f0f0f0').pack(side="left")
    anchor_x_var, anchor_y_var, anchor_z_var = tk.StringVar(value="0"), tk.StringVar(value="64"), tk.StringVar(value="0")
    tk.Entry(anchor_xyz_row, textvariable=anchor_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_z_var, width=8).pack(side="left", padx=4)

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
    b_x_var, b_y_var, b_z_var = tk.StringVar(value="15"), tk.StringVar(value="79"), tk.StringVar(value="0")
    tk.Entry(b_row, textvariable=b_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(b_row, textvariable=b_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(b_row, textvariable=b_z_var, width=8).pack(side="left", padx=4)
    stretch_lock_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    stretch_lock_row.pack(fill="x", pady=(8, 2))
    stretch_lock_var = tk.BooleanVar(value=False)
    tk.Checkbutton(stretch_lock_row, text="Lock aspect ratio, based on:", variable=stretch_lock_var,
                   bg='#f0f0f0').pack(side="left")
    stretch_base_var = tk.StringVar(value="horizontal")
    tk.Radiobutton(stretch_lock_row, text="Horizontal", variable=stretch_base_var, value="horizontal",
                   bg='#f0f0f0').pack(side="left", padx=(6, 2))
    tk.Radiobutton(stretch_lock_row, text="Vertical", variable=stretch_base_var, value="vertical",
                   bg='#f0f0f0').pack(side="left")

    def _switch_mode():
        if mode_var.get() == "fixed":
            stretch_frame.grid_remove()
            fixed_frame.grid()
        else:
            fixed_frame.grid_remove()
            stretch_frame.grid()
        _update_corners_preview()

    corners_preview_frame = tk.Frame(frame, bg='#eef1f5', bd=1, relief="solid")
    corners_preview_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(10, 6))
    corners_preview_var = tk.StringVar(value="Corners will appear here once size/coordinates are set.")
    tk.Label(corners_preview_frame, textvariable=corners_preview_var, bg='#eef1f5', justify="left",
             font=("Consolas", 10), anchor="w").pack(fill="x", padx=10, pady=8)

    def _current_corners():
        facing = facing_var.get()
        if mode_var.get() == "fixed":
            try:
                w, h = int(w_var.get()), int(h_var.get())
                ax, ay, az = int(float(anchor_x_var.get())), int(float(anchor_y_var.get())), int(float(anchor_z_var.get()))
            except ValueError:
                return None
            return compute_corners_fixed_size(anchor_corner_var.get(), (ax, ay, az), w, h, facing)
        else:
            try:
                ax, ay, az = int(float(a_x_var.get())), int(float(a_y_var.get())), int(float(a_z_var.get()))
                bx, by, bz = int(float(b_x_var.get())), int(float(b_y_var.get())), int(float(b_z_var.get()))
            except ValueError:
                return None
            orig_w, orig_h = state["orig_w"] or 1, state["orig_h"] or 1
            return compute_corners_stretch((ax, ay, az), (bx, by, bz), facing, orig_w, orig_h,
                                            lock_aspect=stretch_lock_var.get(), base_on=stretch_base_var.get())

    def _update_corners_preview(*_):
        c = _current_corners()
        preview_img = state["frames"][0] if state.get("frames") else None
        if c is None:
            refresh_preview_widget(preview_img, state["orig_w"], state["orig_h"])
            return
        refresh_preview_widget(preview_img, c["width_blocks"], c["height_blocks"])
        lines = [f"Picture size: {c['width_blocks']} x {c['height_blocks']} blocks   (frame 0 depth: {c['depth']}, advances from there)",
                 f"Bottom-Left: {c['bottom_left']}   Top-Right: {c['top_right']}"]
        if c.get("depth_mismatch"):
            lines.append("\u26a0 Corner A/B disagree on depth -- using Corner A's value.")
        corners_preview_var.set("\n".join(lines))

    # --- timing controls ---
    timing_frame = tk.Frame(frame, bg='#f0f0f0')
    timing_frame.grid(row=8, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Label(timing_frame, text="Server tick rate (ticks/sec):", bg='#f0f0f0').pack(side="left")
    tick_rate_var = tk.StringVar(value="20")
    tk.Entry(timing_frame, textvariable=tick_rate_var, width=6).pack(side="left", padx=(4, 16))
    tk.Label(timing_frame, text="Target playback fps:", bg='#f0f0f0').pack(side="left")
    target_fps_var = tk.StringVar(value="10")
    tk.Entry(timing_frame, textvariable=target_fps_var, width=6).pack(side="left", padx=(4, 16))
    tk.Label(timing_frame, text="Loop count:", bg='#f0f0f0').pack(side="left")
    loop_count_var = tk.StringVar(value="1")
    tk.Entry(timing_frame, textvariable=loop_count_var, width=4).pack(side="left", padx=(4, 16))
    show_all_var = tk.BooleanVar(value=False)
    tk.Checkbutton(timing_frame, text="Show all frames (slow motion, don't skip)",
                   variable=show_all_var, bg='#f0f0f0').pack(side="left")

    tk.Label(frame, text="Target playback fps defaults to the GIF's own rate once loaded (preserves its\n"
                          "original timing regardless of tick rate) -- change it for custom speed.",
             bg='#f0f0f0', fg='#777777', justify="left").grid(row=9, column=0, sticky="w", padx=20)

    frame_plan_frame = tk.Frame(frame, bg='#eef1f5', bd=1, relief="solid")
    frame_plan_frame.grid(row=10, column=0, sticky="ew", padx=20, pady=(6, 6))
    frame_plan_var = tk.StringVar(value="Load a GIF to see its frame rate and timing plan.")
    tk.Label(frame_plan_frame, textvariable=frame_plan_var, bg='#eef1f5', justify="left",
             font=("Consolas", 10), anchor="w").pack(fill="x", padx=10, pady=8)

    def _update_frame_plan(*_):
        if not state["frames"]:
            return
        try:
            tick_rate = float(tick_rate_var.get())
            target_fps = float(target_fps_var.get())
            loop_count = int(loop_count_var.get())
        except ValueError:
            return
        try:
            plan = compute_frame_plan(state["native_fps"], tick_rate, target_fps, show_all_var.get())
        except ValueError as e:
            frame_plan_var.set(f"Invalid timing settings: {e}")
            return
        total_frames = len(state["frames"])
        kept = len(range(0, total_frames, plan["keep_every_n"]))
        total_steps = kept * max(1, loop_count)
        est_depth = (total_steps - 1) * plan["segment_length"] + 1
        warn = ""
        if est_depth > LARGE_STRUCTURE_WARNING:
            warn = (f"\n\u26a0 ~{est_depth} blocks along the depth axis -- generation and pasting a "
                     f"structure this large may be slow.")
        frame_plan_var.set(
            f"Source: {total_frames} frames at {plan['native_fps']:.2f} fps.   "
            f"Circuit: {plan['ticks_per_gap']} redstone ticks/gap "
            f"({plan['num_repeaters_per_gap']} repeater(s)) -> {plan['achieved_fps']:.2f} fps.\n"
            f"Keeping every {plan['keep_every_n']} frame(s) -> {kept} frame(s) x {max(1, loop_count)} "
            f"loop(s) = {total_steps} step(s), ~{est_depth} blocks along the depth axis.{warn}"
        )

    for v in (w_var, h_var, anchor_x_var, anchor_y_var, anchor_z_var, a_x_var, a_y_var, a_z_var,
              b_x_var, b_y_var, b_z_var, stretch_lock_var, stretch_base_var, anchor_corner_var, facing_var):
        v.trace_add("write", _update_corners_preview)
    for v in (tick_rate_var, target_fps_var, loop_count_var, show_all_var):
        v.trace_add("write", _update_frame_plan)

    def _on_w(*_):
        if state["updating"] or not lock_var.get() or not state["orig_w"]:
            _update_corners_preview()
            return
        try:
            w = int(w_var.get())
        except ValueError:
            return
        _, h = locked_dimension(state["orig_w"], state["orig_h"], known_w=w)
        state["updating"] = True
        h_var.set(str(h))
        state["updating"] = False
        _update_corners_preview()

    def _on_h(*_):
        if state["updating"] or not lock_var.get() or not state["orig_w"]:
            _update_corners_preview()
            return
        try:
            h = int(h_var.get())
        except ValueError:
            return
        w, _ = locked_dimension(state["orig_w"], state["orig_h"], known_h=h)
        state["updating"] = True
        w_var.set(str(w))
        state["updating"] = False
        _update_corners_preview()

    w_var.trace_add("write", _on_w)
    h_var.trace_add("write", _on_h)

    # --- status / output ---
    status_var = tk.StringVar(value="Load a palette and a GIF to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=11, column=0, sticky="w", padx=20, pady=(4, 0))
    text_out = tk.Text(frame, height=8, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=12, column=0, sticky="nsew", padx=20, pady=8)
    frame.rowconfigure(12, weight=1)

    def do_generate():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first.")
            return
        if not state["frames"]:
            messagebox.showwarning("No GIF", "Load a GIF first.")
            return
        corners = _current_corners()
        if corners is None:
            messagebox.showwarning("Invalid coordinates", "Check that all coordinate/size fields are numbers.")
            return
        try:
            tick_rate = float(tick_rate_var.get())
            target_fps = float(target_fps_var.get())
            loop_count = int(loop_count_var.get())
        except ValueError:
            messagebox.showwarning("Invalid timing", "Tick rate, target fps, and loop count must be numbers.")
            return

        try:
            plan = compute_frame_plan(state["native_fps"], tick_rate, target_fps, show_all_var.get())
        except ValueError as e:
            messagebox.showwarning("Invalid timing", str(e))
            return

        kept_frames = select_kept_frames(state["frames"], plan["keep_every_n"])
        target_w, target_h = corners["width_blocks"], corners["height_blocks"]

        frame_block_grids = []
        for src_frame in kept_frames:
            pixel_grid = build_pixel_grid(src_frame, target_w, target_h)
            frame_block_grids.append(match_palette(pixel_grid, state["palette"]))

        facing = facing_var.get()
        new_root = generate_gif_command_block_schem(frame_block_grids, facing, corners,
                                                      ticks_per_gap=plan["ticks_per_gap"], loop_count=loop_count)

        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem", filetypes=[("Schematic", "*.schem")],
            title="Save animated command block schematic", initialdir=get_dir("schem_output"))
        if not out_path:
            return

        try:
            save_schematic(new_root, out_path)
            remember("schem_output", out_path)
            status_var.set(f"Saved {len(kept_frames)}-frame x{loop_count}-loop animation to {out_path}")
            text_out.delete("1.0", "end")
            text_out.insert("end", f"Saved: {out_path}\nFacing: {facing}\n"
                                    f"Picture size: {target_w} x {target_h}\n"
                                    f"Frames kept: {len(kept_frames)} of {len(state['frames'])}, x{loop_count} loop(s)\n"
                                    f"Achieved playback: {plan['achieved_fps']:.2f} fps "
                                    f"({plan['ticks_per_gap']} redstone ticks, {plan['num_repeaters_per_gap']} repeater(s)/gap)\n"
                                    f"Bottom-Left: {corners['bottom_left']}   Top-Right: {corners['top_right']}\n")
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Animated command block schematic saved to {out_path}", "normal")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=13, column=0, sticky="ew", padx=20, pady=(0, 10))
    tk.Button(btn_frame, text="Generate Animated Command Block Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=38).pack(side="left")

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


def _browse_gif(var, state, status_var, target_fps_var, on_loaded):
    path = filedialog.askopenfilename(filetypes=[("GIF", "*.gif"), ("All files", "*.*")],
                                       initialdir=get_dir("gif_file"))
    if not path:
        return
    try:
        frames, native_fps = load_gif_frames(path)
        state["base_frames"] = frames
        state["native_fps"] = native_fps
        var.set(path)
        remember("gif_file", path)
        target_fps_var.set(f"{native_fps:.2f}")
        status_var.set(f"Loaded GIF: {len(frames)} frames, {frames[0].size[0]}x{frames[0].size[1]} px, "
                        f"{native_fps:.2f} fps")
        on_loaded()
    except Exception as e:
        messagebox.showerror("Failed to load GIF", str(e))
