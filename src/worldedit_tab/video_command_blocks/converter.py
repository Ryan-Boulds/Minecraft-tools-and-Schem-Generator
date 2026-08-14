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
     timing back automatically. Accepts a target_fps so you only extract
     as many frames as you'll actually use -- a 60fps, 1-minute 1080p
     video is 3600 frames (2GB+) if you extract everything, but only 900
     at 15fps. This is the main fix for extraction being slow and huge:
     don't write 4x more frames to disk than you need.

  2. scan_frame_folder() + stream_frame_block_grids() -- step 2 doesn't
     load any image data up front either: scan_frame_folder() just
     lists file paths and reads the fps sidecar (cheap), and
     stream_frame_block_grids() is a generator that loads, resizes down
     to the tiny target block grid, and discards ONE frame at a time --
     so peak memory during generation stays around a single full-
     resolution frame, regardless of whether the video is 10 frames or
     10,000. The resulting per-frame block grids are tiny (e.g. a 32x32
     grid of block-id strings) and cheap to keep all of them in a list
     for the final generation step. Extracting fewer frames up front
     (via target_fps above) also directly speeds this step up, since
     there are fewer files to read and decode.

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
MAX_RESIZE_HEIGHT = 384  # hard cap -- block art never needs more resolution than this


def probe_video(video_path: str):
    """Quickly reads a video's fps and frame count -- container metadata
    only, no frame decoding -- so this is fast even for large files.
    Used to show the source fps before extraction and to size a target-
    fps extraction correctly. Returns (fps, frame_count, duration_seconds).
    frame_count/duration may be 0 if the container doesn't report a count
    up front (rare, but some formats don't)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
        return fps, frame_count, duration
    finally:
        cap.release()


def extract_video_frames(video_path: str, output_folder: str, target_fps: float = None,
                          frame_skip: int = 1, max_height: int = None,
                          progress_callback=None):
    """Decode `video_path` into numbered PNGs (frame_000001.png, ...) in
    `output_folder`, one frame written to disk at a time.

    target_fps: if given (and > 0), only writes as many frames as needed
    to hit roughly this frame rate -- e.g. target_fps=15 on a 60fps
    source keeps 1 out of every 4 frames. This is one lever for the
    "2GB of images, took forever" problem: a 60fps, 1-minute 1080p video
    is 3600 frames if you extract everything, but only 900 at 15fps --
    a real reduction in both disk usage and how long extraction takes
    (though every source frame still has to be DECODED either way --
    video codecs don't generally support skipping undecoded frames
    reliably, so this saves the PNG-encode-and-write work for discarded
    frames, not the decode work itself).

    frame_skip: a lower-level "keep 1 out of every N" knob, used if
    target_fps isn't given (defaults to 1 = every frame). Ignored if
    target_fps is provided -- target_fps computes its own frame_skip
    from the source's actual fps (via probe_video-equivalent logic
    here) and takes precedence.

    max_height: the OTHER lever -- if given, each written frame is
    downscaled (preserving aspect ratio, never upscaled) so its height
    doesn't exceed this many pixels. E.g. max_height=384 on a 1080p
    (1920x1080) source writes 683x384 frames instead of 1920x1080 ones.
    This is independent of target_fps -- one cuts how many frames get
    written, the other cuts how big each one is -- and they combine.
    Capped at MAX_RESIZE_HEIGHT (384): raises ValueError above that,
    since block art never needs more resolution than this -- the
    eventual output is always downsized further to a target block
    width/height anyway.

    progress_callback(frames_written, frames_seen, total_estimate) is
    called periodically if provided (total_estimate may be 0 if the
    video's container doesn't report a frame count up front).

    Returns (frames_written, effective_fps) and writes a metadata
    sidecar into output_folder so scan_frame_folder() can read the
    original timing back automatically.
    """
    if max_height is not None and max_height > MAX_RESIZE_HEIGHT:
        raise ValueError(f"max_height can't exceed {MAX_RESIZE_HEIGHT}.")

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    try:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_estimate = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if target_fps is not None and target_fps > 0:
            frame_skip = max(1, round(source_fps / target_fps))

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
                if max_height is not None and im.height > max_height:
                    new_w = max(1, round(im.width * (max_height / im.height)))
                    im = im.resize((new_w, max_height), Image.LANCZOS)
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
        "max_height": max_height,
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
