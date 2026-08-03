# worldedit_tab/resource_pack_scanner/scanner.py
"""
Scans a folder of Minecraft resource-pack textures (.png) and computes the
average RGB color of each one. The result is a simple {block_id: [r,g,b]}
palette, saved as JSON so the Image -> Pixel Art tab (and anything else) can
load it later without re-scanning.

WHAT "VALID" MEANS HERE (and why it changed twice):
Attempt 1 was "any real Minecraft block id" -- but that let torches,
tripwire, saplings, slabs, stairs, doors, anvils, cake, etc. through.
Those ARE real registered blocks, but they're not full 1x1x1 cubes, so
they're useless for a pixel-art wall (can't be placed freely, don't fill
their space, need supports/attachment context).

Attempt 2 checks actual collision-shape data instead of just registry
membership: valid_blocks.json is the set of vanilla blocks whose hitbox
is a single, full [0,0,0]-[1,1,1] cube in every state, derived from
Minecraft 1.21.3's real collision-shape data (PrismarineJS/minecraft-
data). That correctly excludes slabs/stairs/fences/doors/torches/
tripwire/anvils/cake/etc. even though they're valid block ids, and
correctly keeps solid single- or multi-texture cubes (wool, concrete,
glass, logs, ore blocks, terracotta, and so on).

This also still resolves the "multi-texture blocks show up as fake ids"
issue as a side effect (e.g. "grass_block_top" isn't a block id at all,
full-cube or otherwise, so it's filtered the same way).

Attempt 3: shape alone still isn't enough. `barrier`, `light`,
`jigsaw`, and the command-block family all occupy a full 1x1x1 cube
(so they passed the shape check) but they're creative-only/technical
blocks -- barrier is normally invisible, light is normally invisible,
jigsaw and the command blocks are structure/redstone utility blocks,
none of them a real "building material." TECHNICAL_BLOCK_BLACKLIST
below excludes these explicitly, regardless of shape.

Attempt 4: full-cube shape doesn't rule out gravity. Sand, red sand,
gravel, suspicious sand/gravel, and all 16 colors of concrete powder
are full 1x1x1 cubes, but they fall as soon as nothing supports them --
e.g. minecraft:orange_concrete_powder placed mid-air just turns into a
falling-sand entity and vanishes from the build. GRAVITY_AFFECTED_
BLOCKS below excludes these explicitly, same as the technical blacklist.

Both blacklists are always enforced, in every mode, with no way to turn
them back on -- there's no legitimate reason to want barrier or falling
sand in a pixel-art wall.

REQUIRE_FULL_CUBE IS ALWAYS ON. An earlier version let
scan_specific_files() (custom/curated folders) skip the full-cube
check by default. That's gone -- both scan_folder() and
scan_specific_files() always require a full-cube block now, no
exceptions, no toggle.

TWO LEVELS OF CHECK, for the custom/curated texture feature: the only
remaining difference between scan_folder() and scan_specific_files() is
scope (a whole resource pack vs. a folder/selection you picked), not
strictness -- both apply the exact same is_valid_block_name() filter
(full-cube + not blacklisted).

EMISSIVE TEXTURES: some custom/shader-oriented texture sets ship a
second, glow-map version of a texture alongside the normal one (common
suffixes: "_e", "_emissive", "_glow", "_emission", or a separate
"emissive" subfolder). Those are always skipped before anything else,
in every mode -- they're not meant to be scanned as their own block
color, just layered on the real texture for a shader.
"""

import json
import os

from PIL import Image

TEXTURE_EXTENSIONS = (".png",)

TECHNICAL_BLOCK_BLACKLIST = {
    "barrier", "light", "structure_void", "moving_piston", "jigsaw",
    "command_block", "chain_command_block", "repeating_command_block",
}

GRAVITY_AFFECTED_BLOCKS = {
    "sand", "red_sand", "gravel", "suspicious_sand", "suspicious_gravel",
    "white_concrete_powder", "orange_concrete_powder", "magenta_concrete_powder",
    "light_blue_concrete_powder", "yellow_concrete_powder", "lime_concrete_powder",
    "pink_concrete_powder", "gray_concrete_powder", "light_gray_concrete_powder",
    "cyan_concrete_powder", "purple_concrete_powder", "blue_concrete_powder",
    "brown_concrete_powder", "green_concrete_powder", "red_concrete_powder",
    "black_concrete_powder",
}

ALWAYS_BLOCKED = TECHNICAL_BLOCK_BLACKLIST | GRAVITY_AFFECTED_BLOCKS

EMISSIVE_SUFFIXES = ("_e", "_emissive", "_glow", "_emission")
EMISSIVE_FOLDER_NAMES = {"emissive"}

_ALL_BLOCKS_PATH = os.path.join(os.path.dirname(__file__), "all_blocks.json")
_FULL_CUBE_BLOCKS_PATH = os.path.join(os.path.dirname(__file__), "valid_blocks.json")
_all_block_names = None       # lazy-loaded, cached -- every real vanilla block id
_full_cube_block_names = None  # lazy-loaded, cached -- the subset that's a full 1x1x1 cube


def _load_json_set(path, cache_attr):
    value = globals()[cache_attr]
    if value is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                value = set(json.load(f))
        except Exception:
            value = set()  # fail open to "nothing validates" rather than crash
        globals()[cache_attr] = value
    return value


def _load_all_block_names() -> set:
    return _load_json_set(_ALL_BLOCKS_PATH, "_all_block_names")


def _load_full_cube_block_names() -> set:
    return _load_json_set(_FULL_CUBE_BLOCKS_PATH, "_full_cube_block_names")


def is_real_block_name(name: str) -> bool:
    """True if `name` (no "minecraft:" prefix) is a real, registered
    vanilla block id (any shape) as of Minecraft 1.21.3, and isn't on
    ALWAYS_BLOCKED (technical or gravity-affected)."""
    if name in ALWAYS_BLOCKED:
        return False
    return name in _load_all_block_names()


def is_valid_block_name(name: str) -> bool:
    """True if `name` is a real vanilla block whose hitbox is a full
    1x1x1 cube in every state, and isn't on ALWAYS_BLOCKED -- i.e. safe
    to drop into a solid pixel-art wall. This is the only filter used
    everywhere now; there's no looser mode."""
    if name in ALWAYS_BLOCKED:
        return False
    return name in _load_full_cube_block_names()


def _average_rgb(image_path: str):
    """Return (r, g, b) averaged over the non-transparent pixels of an image,
    or None if the image has no opaque pixels / can't be read.

    Averaging looks wrong on textures with strong contrast between a few
    distinct colors (e.g. a mostly-white texture with black outline
    details averages toward gray, which doesn't match anything). See
    _dominant_rgb() for the usually-better alternative.

    Animated textures are stored as a vertical strip of square frames
    (width == frame size, height == frame size * frame count). Only the
    first frame is sampled so the average isn't diluted by the rest of the
    animation.
    """
    try:
        with Image.open(image_path) as im:
            im = im.convert("RGBA")
            width, height = im.size

            if width > 0 and height > width and height % width == 0:
                im = im.crop((0, 0, width, width))  # first animation frame only

            pixels = im.getdata()
            r_total = g_total = b_total = count = 0
            for r, g, b, a in pixels:
                if a == 0:
                    continue
                r_total += r
                g_total += g
                b_total += b
                count += 1

            if count == 0:
                return None
            return (r_total // count, g_total // count, b_total // count)
    except Exception:
        return None


def _dominant_rgb(image_path: str, bucket_size: int = 16):
    """Return the (r, g, b) of the most common color in the image, or None
    if it has no opaque pixels / can't be read.

    Raw pixel colors are quantized into `bucket_size`-wide buckets per
    channel first (most textures have some dithering/anti-aliasing noise,
    so two "the same" pixels are rarely byte-identical) and the winning
    bucket's own pixels are then averaged together for a clean
    representative color -- so a mostly-white texture with a few dark
    outline pixels reports as white, not as a washed-out gray the way a
    whole-image average would.

    Same first-animation-frame handling as _average_rgb().
    """
    try:
        with Image.open(image_path) as im:
            im = im.convert("RGBA")
            width, height = im.size

            if width > 0 and height > width and height % width == 0:
                im = im.crop((0, 0, width, width))

            buckets = {}  # (qr,qg,qb) -> [count, r_sum, g_sum, b_sum]
            for r, g, b, a in im.getdata():
                if a == 0:
                    continue
                key = (r // bucket_size, g // bucket_size, b // bucket_size)
                bucket = buckets.get(key)
                if bucket is None:
                    buckets[key] = [1, r, g, b]
                else:
                    bucket[0] += 1
                    bucket[1] += r
                    bucket[2] += g
                    bucket[3] += b

            if not buckets:
                return None

            count, r_sum, g_sum, b_sum = max(buckets.values(), key=lambda v: v[0])
            return (r_sum // count, g_sum // count, b_sum // count)
    except Exception:
        return None


def is_emissive_texture(path: str) -> bool:
    """True if this texture file looks like an emissive/glow-map variant
    rather than a real texture -- by filename suffix (block_e.png,
    block_emissive.png, ...) or by sitting in an "emissive" folder."""
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    if stem.endswith(EMISSIVE_SUFFIXES):
        return True
    parts = {p.lower() for p in os.path.normpath(path).split(os.sep)}
    return bool(parts & EMISSIVE_FOLDER_NAMES)


def _scan_paths(png_paths, progress_callback=None, color_mode: str = "dominant"):
    """Shared core: given a list of .png paths, return (palette, stats).
    Used by both scan_folder() (which builds the path list by walking a
    folder) and scan_specific_files() (an explicit, caller-supplied list --
    a custom/curated folder or an individual multi-file selection).
    Always requires a full-cube, non-blacklisted block -- see the module
    docstring."""
    color_fn = _dominant_rgb if color_mode == "dominant" else _average_rgb

    palette = {}
    scanned = 0
    skipped = 0
    not_a_block = 0
    emissive_skipped = 0
    total = len(png_paths)

    for i, path in enumerate(png_paths):
        name = os.path.splitext(os.path.basename(path))[0]

        if is_emissive_texture(path):
            emissive_skipped += 1
            if progress_callback:
                progress_callback(i + 1, total, name)
            continue

        if not is_valid_block_name(name):
            not_a_block += 1
            if progress_callback:
                progress_callback(i + 1, total, name)
            continue

        rgb = color_fn(path)

        if rgb is None:
            skipped += 1
        else:
            palette[f"minecraft:{name}"] = list(rgb)
            scanned += 1

        if progress_callback:
            progress_callback(i + 1, total, name)

    stats = {"scanned": scanned, "skipped": skipped, "not_a_block": not_a_block,
              "emissive_skipped": emissive_skipped, "total_found": total}
    return palette, stats


def collect_png_paths(folder_path: str):
    """Recursively collect all .png file paths under folder_path."""
    png_paths = []
    for root, _dirs, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(TEXTURE_EXTENSIONS):
                png_paths.append(os.path.join(root, fname))
    return png_paths


def scan_folder(folder_path: str, progress_callback=None, color_mode: str = "dominant"):
    """Walk `folder_path` recursively for .png textures and return
    (palette, stats). Auto-discover entry point for a whole resource
    pack. Always filtered to full-cube, non-blacklisted blocks."""
    return _scan_paths(collect_png_paths(folder_path), progress_callback=progress_callback,
                        color_mode=color_mode)


def scan_specific_files(paths, progress_callback=None, color_mode: str = "dominant"):
    """Scan an explicit list of .png paths -- for a custom/curated folder
    (e.g. a hand-picked set of 20 textures) or an individual multi-file
    selection, rather than an auto-discovered whole resource pack. Same
    filtering as scan_folder() -- full-cube, non-blacklisted blocks only
    -- the only difference is where the file list comes from."""
    png_paths = [p for p in paths if p.lower().endswith(TEXTURE_EXTENSIONS)]
    return _scan_paths(png_paths, progress_callback=progress_callback, color_mode=color_mode)


def save_palette(palette: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(palette, f, indent=2, sort_keys=True)


def load_palette(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
