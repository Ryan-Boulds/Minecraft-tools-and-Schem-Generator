# worldedit_tab/video_command_blocks/gui.py

import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import save_schematic
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from ..common.image_preview import create_preview_widget
from ..resource_pack_scanner.scanner import load_palette
from ..image_to_pixelart.converter import build_pixel_grid, match_palette, locked_dimension
from ..image_command_blocks.converter import CORNER_NAMES, compute_corners_fixed_size, compute_corners_stretch
from .converter import (
    extract_video_frames, scan_frame_folder, load_first_frame, stream_frame_block_grids,
    compute_frame_plan, select_kept_frames, generate_gif_command_block_schem, probe_video,
    MAX_RESIZE_HEIGHT,
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
                  "with a repeater relay between one wall and the next -- plus one more relay segment before\n"
                  "frame 0 (power that end to start the animation) and one more after the last frame (a tap\n"
                  "point for detecting when it's finished). That relay STRUCTURE advances along whichever\n"
                  "axis is \"depth\" for the chosen facing, but every frame's commands target the SAME fixed\n"
                  "on-screen position -- the picture repaints in place. Long, high-fps videos are fully\n"
                  "supported (frames are streamed one at a time during both steps below, never all held in\n"
                  "memory at once) -- a 60fps, 60-second video is 3600 frames, and the STORAGE structure\n"
                  "grows along the depth axis accordingly. That's not a world-height concern (X/Z have\n"
                  "enormous headroom in Minecraft) -- just something to keep an eye on for how long\n"
                  "generation/pasting takes.",
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
              command=lambda: _browse_video(video_path_var, extract_fps_var, source_info_var)
              ).pack(side="left")

    source_info_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=source_info_var, bg='#f0f0f0', fg='#777777').grid(
        row=4, column=0, sticky="w", padx=20, pady=(0, 2))

    outdir_frame = tk.Frame(frame, bg='#f0f0f0')
    outdir_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(outdir_frame, text="Output Frame Folder:", bg='#f0f0f0').pack(side="left")
    outdir_var = tk.StringVar()
    tk.Entry(outdir_frame, textvariable=outdir_var, width=46).pack(side="left", padx=8)
    tk.Button(outdir_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_outdir(outdir_var)).pack(side="left")

    skip_frame = tk.Frame(frame, bg='#f0f0f0')
    skip_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(skip_frame, text="Extract at fps (blank = every source frame):", bg='#f0f0f0').pack(side="left")
    extract_fps_var = tk.StringVar(value="")
    tk.Entry(skip_frame, textvariable=extract_fps_var, width=6).pack(side="left", padx=(4, 12))
    tk.Label(skip_frame, text="Lower than the source fps skips the frames you won't use, "
                              "saving disk space and time.", bg='#f0f0f0', fg='#777777').pack(side="left")

    res_frame = tk.Frame(frame, bg='#f0f0f0')
    res_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(res_frame, text=f"Max resolution height (blank = original size, max {MAX_RESIZE_HEIGHT}):",
              bg='#f0f0f0').pack(side="left")
    max_height_var = tk.StringVar(value="")
    tk.Entry(res_frame, textvariable=max_height_var, width=6).pack(side="left", padx=(4, 12))
    tk.Label(res_frame, text="Downscales each frame before writing it -- smaller frames are much\n"
                              "faster to read back during Generate too.",
              bg='#f0f0f0', fg='#777777', justify="left").pack(side="left")

    extract_status_var = tk.StringVar(value="No video extracted yet.")
    tk.Label(frame, textvariable=extract_status_var, bg='#f0f0f0', fg='#333333').grid(
        row=8, column=0, sticky="w", padx=20, pady=(2, 4))

    def do_extract():
        video_path = video_path_var.get().strip()
        out_dir = outdir_var.get().strip()
        if not video_path:
            messagebox.showwarning("No video", "Choose a video file first.")
            return
        if not out_dir:
            messagebox.showwarning("No output folder", "Choose an output folder for the extracted frames first.")
            return
        target_fps = None
        fps_text = extract_fps_var.get().strip()
        if fps_text:
            try:
                target_fps = float(fps_text)
                if target_fps <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid value", "'Extract at fps' must be a positive number, or blank.")
                return
        max_height = None
        height_text = max_height_var.get().strip()
        if height_text:
            try:
                max_height = int(height_text)
                if max_height <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid value", "'Max resolution height' must be a positive integer, or blank.")
                return
            if max_height > MAX_RESIZE_HEIGHT:
                messagebox.showwarning("Too large", f"'Max resolution height' can't exceed {MAX_RESIZE_HEIGHT}.")
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
                count, fps = extract_video_frames(video_path, out_dir, target_fps=target_fps,
                                                   max_height=max_height, progress_callback=progress)
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
              bg='#673AB7', fg='white', width=18).grid(row=9, column=0, sticky="w", padx=20, pady=(0, 10))

    ttk.Separator(frame, orient="horizontal").grid(row=10, column=0, sticky="ew", padx=20, pady=6)

    # ================= STEP 2: GENERATE FROM FOLDER =================
    tk.Label(frame, text="Step 2: Generate From Frame Folder",
             font=("Arial", 11, "bold"), bg='#f0f0f0').grid(row=11, column=0, sticky="w", padx=20, pady=(4, 2))

    pal_frame = tk.Frame(frame, bg='#f0f0f0')
    pal_frame.grid(row=12, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(pal_frame, text="Block Palette JSON:", bg='#f0f0f0').pack(side="left")
    palette_path_var = tk.StringVar()
    tk.Entry(pal_frame, textvariable=palette_path_var, width=46).pack(side="left", padx=8)
    tk.Button(pal_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_palette(palette_path_var, state, status_var)).pack(side="left")

    ff_frame = tk.Frame(frame, bg='#f0f0f0')
    ff_frame.grid(row=13, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(ff_frame, text="Frame Folder:", bg='#f0f0f0').pack(side="left")
    frame_folder_var = tk.StringVar()
    tk.Entry(ff_frame, textvariable=frame_folder_var, width=46).pack(side="left", padx=8)
    tk.Button(ff_frame, text="Browse", bg='#2196F3', fg='white',
              command=lambda: _browse_frame_folder(frame_folder_var, lambda p: _load_frame_folder(p))
              ).pack(side="left")

    manual_fps_frame = tk.Frame(frame, bg='#f0f0f0')
    manual_fps_frame.grid(row=14, column=0, sticky="ew", padx=20, pady=2)
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

    def _load_palette_preview():
        if not state["palette"]:
            messagebox.showwarning("No palette", "Load a block palette JSON first.")
            return
        if not state["first_frame"]:
            messagebox.showwarning("No frames", "Load a frame folder first.")
            return
        corners = _current_corners()
        if corners is None:
            messagebox.showwarning("Invalid coordinates", "Check that all coordinate/size fields are numbers.")
            return
        pixel_grid = build_pixel_grid(state["first_frame"], corners["width_blocks"], corners["height_blocks"])
        block_grid = match_palette(pixel_grid, state["palette"])
        set_palette_preview(block_grid, state["palette"])

    preview_container, refresh_preview_widget, set_palette_preview = create_preview_widget(
        frame, on_rotate=_do_rotate, on_load_palette_preview=_load_palette_preview)
    preview_container.grid(row=12, column=1, rowspan=7, sticky="n", padx=(10, 10), pady=4)
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
    size_frame.grid(row=15, column=0, sticky="ew", padx=20, pady=(10, 4))
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
    mode_frame.grid(row=16, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Radiobutton(mode_frame, text="Fixed size \u2014 place by one corner (scale locked)",
                   variable=mode_var, value="fixed", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")
    tk.Radiobutton(mode_frame, text="Stretch to fit two coordinates (must stay 2D)",
                   variable=mode_var, value="stretch", bg='#f0f0f0',
                   command=lambda: _switch_mode()).pack(anchor="w")

    fixed_frame = tk.Frame(frame, bg='#f0f0f0')
    fixed_frame.grid(row=17, column=0, sticky="ew", padx=20, pady=4)
    anchor_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_row.pack(fill="x", pady=2)
    tk.Label(anchor_row, text="Anchor corner:", bg='#f0f0f0').pack(side="left")
    anchor_corner_var = tk.StringVar(value="bottom_left")
    ttk.Combobox(anchor_row, textvariable=anchor_corner_var, values=list(CORNER_NAMES),
                 width=14, state="readonly").pack(side="left", padx=(4, 16))
    anchor_xyz_row = tk.Frame(fixed_frame, bg='#f0f0f0')
    anchor_xyz_row.pack(fill="x", pady=2)
    tk.Label(anchor_xyz_row, text="Anchor X Y Z:", bg='#f0f0f0').pack(side="left")
    anchor_x_var, anchor_y_var, anchor_z_var = tk.StringVar(value="0"), tk.StringVar(value="-62"), tk.StringVar(value="0")
    tk.Entry(anchor_xyz_row, textvariable=anchor_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(anchor_xyz_row, textvariable=anchor_z_var, width=8).pack(side="left", padx=4)

    stretch_frame = tk.Frame(frame, bg='#f0f0f0')
    stretch_frame.grid(row=17, column=0, sticky="ew", padx=20, pady=4)
    a_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    a_row.pack(fill="x", pady=2)
    tk.Label(a_row, text="Corner A  X Y Z:", bg='#f0f0f0').pack(side="left")
    a_x_var, a_y_var, a_z_var = tk.StringVar(value="0"), tk.StringVar(value="-62"), tk.StringVar(value="0")
    tk.Entry(a_row, textvariable=a_x_var, width=8).pack(side="left", padx=4)
    tk.Entry(a_row, textvariable=a_y_var, width=8).pack(side="left", padx=4)
    tk.Entry(a_row, textvariable=a_z_var, width=8).pack(side="left", padx=4)
    b_row = tk.Frame(stretch_frame, bg='#f0f0f0')
    b_row.pack(fill="x", pady=2)
    tk.Label(b_row, text="Corner B (diagonal) X Y Z:", bg='#f0f0f0').pack(side="left")
    b_x_var, b_y_var, b_z_var = tk.StringVar(value="15"), tk.StringVar(value="-47"), tk.StringVar(value="0")
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
    corners_preview_frame.grid(row=18, column=0, sticky="ew", padx=20, pady=(10, 6))
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
        lines = [f"Picture size: {c['width_blocks']} x {c['height_blocks']} blocks   (fixed display depth: {c['depth']})",
                 f"Bottom-Left: {c['bottom_left']}   Top-Right: {c['top_right']}"]
        if c.get("depth_mismatch"):
            lines.append("\u26a0 Corner A/B disagree on depth -- using Corner A's value.")
        corners_preview_var.set("\n".join(lines))

    # --- timing controls ---
    timing_frame = tk.Frame(frame, bg='#f0f0f0')
    timing_frame.grid(row=19, column=0, sticky="ew", padx=20, pady=(10, 4))
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
             bg='#f0f0f0', fg='#777777', justify="left").grid(row=20, column=0, sticky="w", padx=20)

    layer_frame = tk.Frame(frame, bg='#f0f0f0')
    layer_frame.grid(row=21, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(layer_frame, text="Max blocks per layer (blank = unlimited):", bg='#f0f0f0').pack(side="left")
    max_depth_var = tk.StringVar(value="")
    tk.Entry(layer_frame, textvariable=max_depth_var, width=8).pack(side="left", padx=(4, 12))
    tk.Label(layer_frame, text="Splits a too-long animation into layers, stacked 2 blocks\n"
                                "apart -- e.g. 512 for a 32-chunk render distance.",
              bg='#f0f0f0', fg='#777777', justify="left").pack(side="left")

    standing_frame = tk.Frame(frame, bg='#f0f0f0')
    standing_frame.grid(row=22, column=0, sticky="ew", padx=20, pady=2)
    tk.Label(standing_frame, text="Standing position when you //paste (X Y Z):", bg='#f0f0f0').pack(side="left")
    stand_x_var, stand_y_var, stand_z_var = tk.StringVar(value=""), tk.StringVar(value=""), tk.StringVar(value="")
    tk.Entry(standing_frame, textvariable=stand_x_var, width=6).pack(side="left", padx=(4, 2))
    tk.Entry(standing_frame, textvariable=stand_y_var, width=6).pack(side="left", padx=2)
    tk.Entry(standing_frame, textvariable=stand_z_var, width=6).pack(side="left", padx=(2, 12))
    tk.Label(standing_frame, text="Only needed with a layer limit above -- the fill command that\n"
                                   "starts each next layer is baked in as absolute coordinates.",
              bg='#f0f0f0', fg='#777777', justify="left").pack(side="left")

    frame_plan_frame = tk.Frame(frame, bg='#eef1f5', bd=1, relief="solid")
    frame_plan_frame.grid(row=23, column=0, sticky="ew", padx=20, pady=(6, 6))
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
        est_depth = 2 * plan["num_repeaters_per_gap"] + (total_steps - 1) * plan["segment_length"] + 1
        warn = ""
        if est_depth > LARGE_STRUCTURE_WARNING:
            warn = (f"\n\u26a0 ~{est_depth} blocks along the depth axis -- generation and pasting a "
                     f"structure this large may be slow.")
        layer_note = ""
        max_depth_text = max_depth_var.get().strip()
        if max_depth_text:
            try:
                max_depth = int(max_depth_text)
                valid_int = max_depth > 0
            except ValueError:
                max_depth = None
                valid_int = False
            if not valid_int:
                layer_note = "\n\u26a0 'Max blocks per layer' must be a positive integer, or blank."
            else:
                num_repeaters = plan["num_repeaters_per_gap"]
                segment_length = plan["segment_length"]
                lead_trail = num_repeaters

                def depth_needed(n):
                    return lead_trail + (n - 1) * segment_length + 1 + lead_trail

                min_needed = depth_needed(1)
                if max_depth < min_needed:
                    layer_note = f"\n\u26a0 Max blocks per layer ({max_depth}) is too small (needs at least {min_needed})."
                else:
                    num_layers_est = 0
                    start = 0
                    while start < total_steps:
                        n = 1
                        while start + n < total_steps and depth_needed(n + 1) <= max_depth:
                            n += 1
                        start += n
                        num_layers_est += 1
                    if num_layers_est > 1:
                        layer_note = (f"\n{num_layers_est} layer(s) needed at {max_depth} blocks/layer, stacked "
                                      f"vertically -- set your standing position below.")
                    else:
                        layer_note = f"\nFits in a single layer at {max_depth} blocks/layer -- no splitting needed."
        frame_plan_var.set(
            f"Source: {total_frames} frames at {plan['native_fps']:.2f} fps.   "
            f"Circuit: {plan['ticks_per_gap']} redstone ticks/gap "
            f"({plan['num_repeaters_per_gap']} repeater(s)) -> {plan['achieved_fps']:.2f} fps.\n"
            f"Keeping every {plan['keep_every_n']} frame(s) -> {kept} frame(s) x {max(1, loop_count)} "
            f"loop(s) = {total_steps} step(s), ~{est_depth} blocks along the depth axis.{warn}{layer_note}"
        )

    for v in (w_var, h_var, anchor_x_var, anchor_y_var, anchor_z_var, a_x_var, a_y_var, a_z_var,
              b_x_var, b_y_var, b_z_var, stretch_lock_var, stretch_base_var, anchor_corner_var, facing_var):
        v.trace_add("write", _update_corners_preview)
    for v in (tick_rate_var, target_fps_var, loop_count_var, show_all_var, max_depth_var):
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
        row=24, column=0, sticky="w", padx=20, pady=(4, 0))
    text_out = tk.Text(frame, height=8, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_out.grid(row=25, column=0, sticky="nsew", padx=20, pady=8)
    frame.rowconfigure(25, weight=1)

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

        max_depth = None
        max_depth_text = max_depth_var.get().strip()
        if max_depth_text:
            try:
                max_depth = int(max_depth_text)
                if max_depth <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid value", "'Max blocks per layer' must be a positive integer, or blank.")
                return

        standing_pos = None
        if max_depth is not None:
            try:
                standing_pos = (int(stand_x_var.get()), int(stand_y_var.get()), int(stand_z_var.get()))
            except ValueError:
                messagebox.showwarning(
                    "Standing position needed",
                    "With 'Max blocks per layer' set, enter the X Y Z you'll be standing at when you "
                    "run //paste -- the fill command connecting each layer needs it baked in.")
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
                    ticks_per_gap=plan["ticks_per_gap"], loop_count=loop_count,
                    max_depth_per_layer=max_depth, standing_pos=standing_pos)
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
                                    f"Bottom-Left: {corners['bottom_left']}   Top-Right: {corners['top_right']}\n"
                                    + (f"Split across layers stacked {target_h + 3} blocks apart. Paste standing "
                                       f"exactly at {standing_pos}, no rotation -- power the lead-in relay at the "
                                       f"bottom layer to start; the rest triggers automatically.\n"
                                       if max_depth else ""))
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
    btn_frame.grid(row=26, column=0, sticky="ew", padx=20, pady=(0, 10))
    tk.Button(btn_frame, text="Generate Animated Command Block Schematic", command=do_generate,
              bg='#4CAF50', fg='white', width=38).pack(side="left")

    _switch_mode()
    return frame


def _browse_video(var, extract_fps_var, source_info_var):
    path = filedialog.askopenfilename(
        filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"), ("All files", "*.*")],
        initialdir=get_dir("video_file"))
    if not path:
        return
    var.set(path)
    remember("video_file", path)
    try:
        fps, frame_count, duration = probe_video(path)
        extra = f", ~{duration:.1f}s" if duration else ""
        source_info_var.set(f"Source: {fps:.2f} fps, {frame_count} frame(s){extra}. "
                              f"Leave \"Extract at fps\" blank to keep all of them.")
    except Exception as e:
        source_info_var.set(f"Could not read video info: {e}")


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
