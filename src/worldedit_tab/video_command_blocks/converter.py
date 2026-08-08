# worldedit_tab/video_command_blocks/converter.py
"""
Video -> animated command-block wall. Reuses the exact same redstone
circuit generator as GIF Command Blocks (generate_gif_command_block_schem,
compute_frame_plan, decompose_ticks, all imported from
gif_command_blocks.converter) -- one shared, already-verified generator
for both, so a fix to the circuit design fixes both tabs at once.

TWO STEPS, KEPT SEPARATE ON PURPOSE, because of scale: a 60fps,
60-second video is 3600 frames. Even at modest resolution, holding that
many full-resolution frames in memory simultaneously would be tens of
gigabytes -- completely impractical. So:

  1. extract_video_frames() -- decodes the video with OpenCV and writes
     each frame straight to disk as a numbered PNG, one at a time. Never
     holds more than a single frame in memory. Writes a small JSON
     sidecar recording the source fps, so step 2 can read the original
     timing back automatically.

  2. scan_frame_folder() + stream_frame_block_grids() -- step 2 doesn't
     load any image data up front either: scan_frame_folder() just
     lists file paths and reads the fps sidecar (cheap), and
     stream_frame_block_grids() is a generator that loads, resizes down
     to the tiny target block grid, and discards ONE frame at a time --
     so peak memory during generation stays around a single full-
     resolution frame, regardless of whether the video is 10 frames or
     10,000. The resulting per-frame block grids are tiny (e.g. a 32x32
     grid of block-id strings) and cheap to keep all of them in a list
     for the final generation step.

A REAL PRACTICAL LIMIT WORTH KNOWING: none of the above is about
Minecraft build size -- that's governed by world height (see GIF
Command Blocks' MAX_SAFE_HEIGHT warning, reused here). Thousands of
frames times however many repeater/quartz pairs each frame-gap needs
adds up in height fast. The tool will happily extract and process a
long, high-fps video without choking -- whether the resulting structure
is small enough to actually build is a separate question the UI's
height estimate is there to answer before you commit to generating.
"""

import json
import os

import cv2
from PIL import Image, ImageOps

# Re-exported for convenience so the GUI only needs one import line for
# both the video-specific helpers here and the shared circuit generator.
from ..gif_command_blocks.converter import (
    compute_frame_plan, decompose_ticks, select_kept_frames,
    generate_gif_command_block_schem,
)

METADATA_FILENAME = "video_frames_meta.json"


def extract_video_frames(video_path: str, output_folder: str, frame_skip: int = 1,
                          progress_callback=None):
    """Decode `video_path` into numbered PNGs (frame_000001.png, ...) in
    `output_folder`, one frame written to disk at a time.

    frame_skip: keep 1 out of every `frame_skip` source frames (1 = every
    frame) -- a disk-space/extraction-time knob, separate from the
    timing-driven frame skipping Generate From Folder applies later on
    top of whatever gets written here.

    progress_callback(frames_written, frames_seen, total_estimate) is
    called periodically if provided (total_estimate may be 0 if the
    video's container doesn't report a frame count up front).

    Returns (frames_written, effective_fps) and writes a metadata
    sidecar into output_folder so scan_frame_folder() can read the
    original timing back automatically.
    """
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    try:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_estimate = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        frames_seen = 0
        frames_written = 0

        while True:
            ok, bgr_frame = cap.read()
            if not ok:
                break
            frames_seen += 1

            if (frames_seen - 1) % max(1, frame_skip) == 0:
                frames_written += 1
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                im = Image.fromarray(rgb_frame)
                out_path = os.path.join(output_folder, f"frame_{frames_written:06d}.png")
                im.save(out_path)

            if progress_callback and (frames_seen % 10 == 0 or frames_seen == total_estimate):
                progress_callback(frames_written, frames_seen, total_estimate)
    finally:
        cap.release()

    effective_fps = source_fps / max(1, frame_skip)

    meta = {
        "source_fps": source_fps,
        "frame_skip": frame_skip,
        "effective_fps": effective_fps,
        "frame_count": frames_written,
    }
    with open(os.path.join(output_folder, METADATA_FILENAME), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return frames_written, effective_fps


def scan_frame_folder(folder_path: str):
    """Lists the numbered frame PNGs in `folder_path` (sorted) without
    loading any image data, and reads the fps sidecar if this folder
    came from extract_video_frames(). Returns (frame_paths, fps_or_None,
    (width, height)_of_first_frame)."""
    names = sorted(
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".png") and f != METADATA_FILENAME
    )
    frame_paths = [os.path.join(folder_path, n) for n in names]
    if not frame_paths:
        raise ValueError("No .png frames found in that folder.")

    fps = None
    meta_path = os.path.join(folder_path, METADATA_FILENAME)
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                fps = json.load(f).get("effective_fps")
        except Exception:
            fps = None

    with Image.open(frame_paths[0]) as im:
        im = ImageOps.exif_transpose(im)
        size = im.size

    return frame_paths, fps, size


def load_first_frame(folder_path: str):
    """Loads just the first frame (for the preview widget / aspect-lock
    sizing) -- the only place in this module that returns a full PIL
    Image rather than a path or a tiny block grid."""
    frame_paths, _fps, _size = scan_frame_folder(folder_path)
    im = Image.open(frame_paths[0])
    im = ImageOps.exif_transpose(im)
    return im.convert("RGBA")


def stream_frame_block_grids(frame_paths, target_w: int, target_h: int, palette: dict,
                              rotation: int = 0, progress_callback=None):
    """Yields one block_grid per path in `frame_paths` -- loads, rotates,
    resizes, and palette-matches ONE frame at a time, so peak memory
    during this stays around a single full-resolution frame no matter
    how many paths there are."""
    from ..image_to_pixelart.converter import build_pixel_grid, match_palette

    total = len(frame_paths)
    for i, path in enumerate(frame_paths):
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA")
            if rotation:
                im = im.rotate(-rotation, expand=True)
            pixel_grid = build_pixel_grid(im, target_w, target_h)
        block_grid = match_palette(pixel_grid, palette)
        yield block_grid

        if progress_callback and (i % 10 == 0 or i == total - 1):
            progress_callback(i + 1, total)
