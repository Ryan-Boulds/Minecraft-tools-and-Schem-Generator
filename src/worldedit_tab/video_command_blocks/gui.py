# worldedit_tab/video_command_blocks/gui.py

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from ..common.image_preview import create_preview_widget
from ..resource_pack_scanner.scanner import load_palette
from ..image_to_pixelart.converter import locked_dimension
from ..image_command_blocks.converter import CORNER_NAMES, compute_corners_fixed_size, compute_corners_stretch
from .converter import (
    extract_video_frames, scan_frame_folder, load_first_frame, stream_frame_block_grids,
    compute_frame_plan, select_kept_frames, generate_gif_command_block_schem,
)

LARGE_STRUCTURE_WARNING = 2000  # heads-up threshold for depth-axis extent; not a hard Minecraft limit like world height was


def create_video_command_blocks_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    state = {"palette": None, "frame_paths": None, "native_fps": None, "first_frame": None,
             "rotation": 0, "orig_w": None, "orig_h": None, "updating": False,
             "extracting": False, "generating": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Video \u2192 Command Blocks (animated)",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Each frame is a full wall of command blocks (and stone, for pixels that didn't change),\n"
                  "with a repeater relay between one wall and the next -- the picture's position genuinely\n"
                  "advances through the world one frame at a time, along whichever axis is \"depth\" for the\n"
                  "chosen facing. Long, high-fps videos are fully supported (frames are streamed one at a\n"
                  "time during both steps below, never all held in memory at once) -- a 60fps, 60-second\n"
                  "video is 3600 frames, and the structure grows along that depth axis accordingly. Unlike\n"
                  "an earlier version of this, that's not a world-height concern (X/Z have enormous headroom\n"
                  "in Minecraft) -- just something to keep an eye on for how long generation/pasting takes.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    # ================= STEP 1: EXTRACT FRAMES =================
    step1_label = tk.Label(frame, text="Step 1: Extract Frames from Video (skip if you already have a frame folder)",
                            font=("Arial", 11, "bold"), bg='#f0f0f0')
    step1_label.grid(row=2, column=0, sticky="w", padx=20, pady=(6, 2))

    video_frame = tk.Frame(frame, bg='#f0f0f0')
    video_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(video_frame, text="Video File:", bg='#f0f0f0').pack(side="left")
    video_path_var = tk.StringVar()
    tk.Entry(video_frame, textvariable=video_path_var, width=46).pack(side="left", padx=8)
    tk.Button(video_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_video(video_path_var)).pack(side="left")

    outdir_frame = tk.Frame(frame, bg='#f0f0f0')
    outdir_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(outdir_frame, text="Output Frame Folder:", bg='#f0f0f0').pack(side="left")
    outdir_var = tk.StringVar()
    tk.Entry(outdir_frame, textvariable=outdir_var, width=46).pack(side="left", padx=8)
    tk.Button(outdir_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_outdir(outdir_var)).pack(side="left")

    skip_frame = tk.Frame(frame, bg='#f0f0f0')
    skip_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(skip_frame, text="Extract every Nth frame (1 = every frame):", bg='#f0f0f0').pack(side="left")
    frame_skip_var = tk.StringVar(value="1")
    tk.Entry(skip_frame, textvariable=frame_skip_var, width=5).pack(side="left", padx=(4, 0))

    extract_status_var = tk.StringVar(value="No video extracted yet.")
    tk.Label(frame, textvariable=extract_status_var, bg='#f0f0f0', fg='#333333').grid(
        row=6, column=0, sticky="w", padx=20, pady=(2, 4))

    def do_extract():
        video_path = video_path_var.get().strip()
        out_dir = outdir_var.get().strip()
        if not video_path:
            messagebox.showwarning("No video", "Choose a video file first.")
            return
        if not out_dir:
            messagebox.showwarning("No output folder", "Choose an output folder for the extracted frames first.")
            return
        try:
            frame_skip = max(1, int(frame_skip_var.get()))
        except ValueError:
            messagebox.showwarning("Invalid value", "'Extract every Nth frame' must be a positive integer.")
            return
        if state["extracting"]:
            return

        state["extracting"] = True
        extract_status_var.set("Extracting...")

        # Tkinter widgets (including .after()) aren't safe to touch from a
        # background thread. The worker only ever pushes plain data into
        # this queue; only the main thread (via the self-rescheduling
        # _poll() below, itself only ever called from the main thread)
        # touches any widget.
        result_queue = queue.Queue()

        def progress(written, seen, total):
            result_queue.put(("progress", written, seen, total))

        def worker():
            try:
                count, fps = extract_video_frames(video_path, out_dir, frame_skip=frame_skip,
                                                   progress_callback=progress)
            except Exception as e:
                result_queue.put(("error", str(e)))
                return
            result_queue.put(("done", count, fps, out_dir))

        def _on_extract_error(msg):
            state["extracting"] = False
            extract_status_var.set("Extraction failed.")
            messagebox.showerror("Extraction failed", msg)

        def _on_extract_done(count, fps, out_dir):
            state["extracting"] = False
            extract_status_var.set(f"Extracted {count} frame(s) at {fps:.2f} fps to {out_dir}")
            # carry straight into Step 2
            frame_folder_var.set(out_dir)
            _load_frame_folder(out_dir)
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Extracted {count} video frames to {out_dir}", "normal")

        def _poll():
            try:
                while True:
                    item = result_queue.get_nowait()
                    if item[0] == "progress":
                        _, written, seen, total = item
                        label = f"Extracted {written} frame(s), seen {seen}" + (f" of ~{total}" if total else "")
                        extract_status_var.set(label)
                    elif item[0] == "done":
                        _, count, fps, out_dir = item
                        _on_extract_done(count, fps, out_dir)
                        return  # finished -- stop polling
                    elif item[0] == "error":
                        _on_extract_error(item[1])
                        return  # finished -- stop polling
            except queue.Empty:
                pass
            if state["extracting"]:
                frame.after(100, _poll)

        threading.Thread(target=worker, daemon=True).start()
        frame.after(100, _poll)

    tk.Button(frame, text="Extract Frames", command=do_extract,
              bg='#673AB7', fg='white', width=18).grid(row=7, column=0, sticky="w", padx=20, pady=(0, 10))

    ttk.Separator(frame, orient="horizontal").grid(row=8, column=0, sticky="ew", padx=20, pady=6)

    # ================= STEP 2: GENERATE FROM FOLDER =================
    tk.Label(frame, text="Step 2: Generate From Frame Folder",
             font=("Arial", 11, "bold"), bg='#f0f0f0').grid(row=9, column=0, sticky="w", padx=20, pady=(4, 2))

    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=10, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=46).pack(side="left", padx=8)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    ff_frame = tk.Frame(frame, bg='#f0f0f0')
    ff_frame.grid(row=11, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(ff_frame, text="Frame Folder:", bg='#f0f0f0').pack(side="left")
    frame_folder_var = tk.StringVar()
    tk.Entry(ff_frame, textvariable=frame_folder_var, width=46).pack(side="left", padx=8)
    tk.Button(ff_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_frame_folder(frame_folder_var, lambda p: _load_frame_folder(p))
              ).pack(side="left")

    manual_fps_frame = tk.Frame(frame, bg='#f0f0f0')
    manual_fps_frame.grid(row=12, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(manual_fps_frame, text="Source fps (auto-filled if extracted by this tool; enter manually otherwise):",
             bg='#f0f0f0').pack(side="left")
    native_fps_var = tk.StringVar(value="")

    def _on_native_fps_edit(*_):
        if state["updating"]:
            return
        try:
            state["native_fps"] = float(native_fps_var.get())
        except ValueError:
            state["native_fps"] = None
        _update_frame_plan()

    tk.Entry(manual_fps_frame, textvariable=native_fps_var, width=8).pack(side="left", padx=(4, 0))
    native_fps_var.trace_add("write", _on_native_fps_edit)

    def _do_rotate():
        if not state["first_frame"]:
            return
        state["rotation"] = (state["rotation"] + 90) % 360
        _apply_rotation_to_first_frame()
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
    preview_container.grid(row=10, column=1, rowspan=7, sticky="n", padx=(10, 10), pady=4)
    frame.columnconfigure(1, weight=0)

    def _apply_rotation_to_first_frame():
        rotated = state["_base_first_frame"].rotate(-state["rotation"], expand=True)
        state["first_frame"] = rotated
        state["orig_w"], state["orig_h"] = rotated.size

    def _load_frame_folder(folder_path):
        try:
            frame_paths, fps, size = scan_frame_folder(folder_path)
            first = load_first_frame(folder_path)
        except Exception as e:
            messagebox.showerror("Failed to load frame folder", str(e))
            return
        state["frame_paths"] = frame_paths
        state["rotation"] = 0
        state["_base_first_frame"] = first
        _apply_rotation_to_first_frame()
        remember("video_frame_folder", folder_path)

        state["updating"] = True
        if fps is not None:
            state["native_fps"] = fps
            native_fps_var.set(f"{fps:.2f}")
            target_fps_var.set(f"{fps:.2f}")
        else:
            state["native_fps"] = None
            native_fps_var.set("")
        state["updating"] = False

        status_var.set(f"Loaded frame folder: {len(frame_paths)} frames, {size[0]}x{size[1]} px"
                        + (f", {fps:.2f} fps (auto-detected)" if fps is not None else " -- enter fps manually above"))
        _update_corners_preview()
        _update_frame_plan()

    # --- size / facing ---
    size_frame = tk.Frame(frame, bg='#f0f0f0')
    size_frame.grid(row=13, column=0, sticky="ew", padx=20, pady=(10, 4))
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
    mode_frame.grid(row=14, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Radiobutton(mode_frame, text="Fixed size \u2014 place by one corner (scale locked)",
                   variable=mode_var, value="fixed", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")
    tk.Radiobutton(mode_frame, text="Stretch to fit two coordinates (must stay 2D)",
                   variable=mode_var, value="stretch", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")

    fixed_frame = tk.Frame(frame, bg='#f0f0f0')
    fixed_frame.grid(row=15, column=0, sticky="ew", padx=20, pady=4)
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
    stretch_frame.grid(row=15, column=0, sticky="ew", padx=20, pady=4)
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
    corners_preview_frame.grid(row=16, column=0, sticky="ew", padx=20, pady=(10, 6))
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
        preview_img = state.get("first_frame")
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
    timing_frame.grid(row=17, column=0, sticky="ew", padx=20, pady=(10, 4))
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

    tk.Label(frame, text="Target playback fps defaults to the detected source fps (preserves original timing\n"
                          "regardless of tick rate) -- change it for custom speed.",
             bg='#f0f0f0', fg='#777777', justify="left").grid(row=18, column=0, sticky="w", padx=20)

    frame_plan_frame = tk.Frame(frame, bg='#eef1f5', bd=1, relief="solid")
    frame_plan_frame.grid(row=19, column=0, sticky="ew", padx=20, pady=(6, 6))
    frame_plan_var = tk.StringVar(value="Load a frame folder to see its frame rate and timing plan.")
    tk.Label(frame_plan_frame, textvariable=frame_plan_var, bg='#eef1f5', justify="left",
             font=("Consolas", 10), anchor="w").pack(fill="x", padx=10, pady=8)

    def _update_frame_plan(*_):
        if not state["frame_paths"] or state["native_fps"] is None:
            if state["frame_paths"] and state["native_fps"] is None:
                frame_plan_var.set("No fps detected for this folder -- enter the source fps above to see a timing plan.")
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
        total_frames = len(state["frame_paths"])
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
    status_var = tk.StringVar(value="Load a palette and a frame folder to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=20, column=0, sticky="w", padx=20, pady=(4, 0))
    text_out = tk.Text(frame, height=8, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=21, column=0, sticky="nsew", padx=20, pady=8)
    frame.rowconfigure(21, weight=1)

    def do_generate():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first.")
            return
        if not state["frame_paths"]:
            messagebox.showwarning("No frames", "Load a frame folder first.")
            return
        if state["native_fps"] is None:
            messagebox.showwarning("No fps", "Enter the source fps for this frame folder first.")
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

        out_path = filedialog.asksaveasfilename(
            defaultextension=".schem", filetypes=[("Schematic", "*.schem")],
            title="Save animated command block schematic", initialdir=get_dir("schem_output"))
        if not out_path:
            return

        if state["generating"]:
            return
        state["generating"] = True
        status_var.set("Generating (streaming frames from disk)...")

        facing = facing_var.get()  # read on the main thread -- Tkinter Variables aren't safe from a worker thread
        result_queue = queue.Queue()

        def progress(i, total):
            result_queue.put(("progress", i, total))

        def worker():
            try:
                kept_paths = select_kept_frames(state["frame_paths"], plan["keep_every_n"])
                target_w, target_h = corners["width_blocks"], corners["height_blocks"]
                frame_block_grids = list(stream_frame_block_grids(
                    kept_paths, target_w, target_h, state["palette"],
                    rotation=state["rotation"], progress_callback=progress))
                new_root = generate_gif_command_block_schem(
                    frame_block_grids, facing, corners,
                    ticks_per_gap=plan["ticks_per_gap"], loop_count=loop_count)
                save_schematic(new_root, out_path)
            except Exception as e:
                result_queue.put(("error", str(e)))
                return
            result_queue.put(("done", len(kept_paths), target_w, target_h, facing))

        def _on_gen_error(msg):
            state["generating"] = False
            status_var.set("Generation failed.")
            messagebox.showerror("Generation failed", msg)

        def _on_gen_done(num_kept, target_w, target_h, facing):
            state["generating"] = False
            remember("schem_output", out_path)
            status_var.set(f"Saved {num_kept}-frame x{loop_count}-loop animation to {out_path}")
            text_out.delete("1.0", "end")
            text_out.insert("end", f"Saved: {out_path}\nFacing: {facing}\n"
                                    f"Picture size: {target_w} x {target_h}\n"
                                    f"Frames kept: {num_kept} of {len(state['frame_paths'])}, x{loop_count} loop(s)\n"
                                    f"Achieved playback: {plan['achieved_fps']:.2f} fps "
                                    f"({plan['ticks_per_gap']} redstone ticks, {plan['num_repeaters_per_gap']} repeater(s)/gap)\n"
                                    f"Bottom-Left: {corners['bottom_left']}   Top-Right: {corners['top_right']}\n")
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Animated command block schematic saved to {out_path}", "normal")

        def _poll():
            try:
                while True:
                    item = result_queue.get_nowait()
                    if item[0] == "progress":
                        _, i, total = item
                        status_var.set(f"Processing frame {i}/{total}...")
                    elif item[0] == "done":
                        _, num_kept, target_w, target_h, facing = item
                        _on_gen_done(num_kept, target_w, target_h, facing)
                        return
                    elif item[0] == "error":
                        _on_gen_error(item[1])
                        return
            except queue.Empty:
                pass
            if state["generating"]:
                frame.after(100, _poll)

        threading.Thread(target=worker, daemon=True).start()
        frame.after(100, _poll)

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=22, column=0, sticky="ew", padx=20, pady=(0, 10))
    tk.Button(btn_frame, text="Generate Animated Command Block Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=38).pack(side="left")

    _switch_mode()
    return frame


def _browse_video(var):
    path = filedialog.askopenfilename(
        filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"), ("All files", "*.*")],
        initialdir=get_dir("video_file"))
    if path:
        var.set(path)
        remember("video_file", path)


def _browse_outdir(var):
    path = filedialog.askdirectory(title="Select a folder to save extracted frames into",
                                    initialdir=get_dir("video_frames_output"))
    if path:
        var.set(path)
        remember("video_frames_output", path)


def _browse_frame_folder(var, on_selected):
    path = filedialog.askdirectory(title="Select a folder of numbered frame images",
                                    initialdir=get_dir("video_frame_folder"))
    if not path:
        return
    var.set(path)
    on_selected(path)


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
