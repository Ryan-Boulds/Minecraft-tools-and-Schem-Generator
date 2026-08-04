# worldedit_tab/image_to_pixelart/converter.py
"""
Converts a photo into a grid of block ids using a color palette produced by
the Resource Pack Scanner tab, then builds either:
  * a direct-block .schem (the picture, made of real blocks) — "Convert to
    blocks" mode, or
  * a wall of command blocks whose setblock commands target the absolute
    world coordinates the player was standing at when the palette/scan was
    taken — "command block wall" mode.
"""

from PIL import Image
from nbtlib.tag import Compound, Int, Short, IntArray, List

from ..common.schem_io import command_block_state, make_command_block_entity, build_block_data

AIR_BLOCK = "minecraft:air"

try:
    _BOX_FILTER = Image.Resampling.BOX
except AttributeError:  # older Pillow
    _BOX_FILTER = Image.BOX

TRANSPARENCY_CUTOFF = 128  # pixels with alpha below this are treated as "no block"


def locked_dimension(orig_w: int, orig_h: int, known_w: int = None, known_h: int = None):
    """Given the source image size and one known target dimension, compute
    the other so the aspect ratio is preserved. Returns (width, height)."""
    if known_w is not None:
        height = max(1, round(known_w * orig_h / orig_w))
        return known_w, height
    if known_h is not None:
        width = max(1, round(known_h * orig_w / orig_h))
        return width, known_h
    raise ValueError("Must supply known_w or known_h")


def load_source_image(image_path: str) -> Image.Image:
    return Image.open(image_path).convert("RGBA")


def build_pixel_grid(image: Image.Image, target_w: int, target_h: int):
    """Downsample `image` to target_w x target_h using an area/box filter
    (true per-cell averaging, matching how the resource pack scanner
    averages texture colors) and return a row-major list of (r, g, b, a)."""
    small = image.resize((target_w, target_h), _BOX_FILTER)
    pixels = list(small.getdata())
    grid = []
    for row in range(target_h):
        grid.append(pixels[row * target_w:(row + 1) * target_w])
    return grid


def match_palette(pixel_grid, palette: dict):
    """Replace each (r,g,b,a) pixel with a matched block id (or None for
    transparent pixels). Uses a cache so repeated colors are only matched
    once, since a photo of any size usually reduces to a small color set."""
    palette_items = [(name, tuple(rgb)) for name, rgb in palette.items()]
    cache = {}

    def nearest(rgb):
        if rgb in cache:
            return cache[rgb]
        best_name, best_dist = None, None
        for name, prgb in palette_items:
            dist = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
            if best_dist is None or dist < best_dist:
                best_name, best_dist = name, dist
        cache[rgb] = best_name
        return best_name

    block_grid = []
    for row in pixel_grid:
        block_row = []
        for (r, g, b, a) in row:
            if a < TRANSPARENCY_CUTOFF:
                block_row.append(None)
            else:
                block_row.append(nearest((r, g, b)))
        block_grid.append(block_row)
    return block_grid


def _plane_dims(target_w, target_h, facing):
    """Return (width_axis_size, height_axis_size, thickness_axis_size, is_ns)
    for the given facing. north/south -> image spans X (thickness in Z).
    east/west -> image spans Z (thickness in X)."""
    is_ns = facing in ("north", "south")
    return target_w, target_h, 1, is_ns


def generate_direct_block_schem(block_grid, facing, data_version=3578):
    """Build a data Compound placing REAL blocks in the shape of the image
    (row 0 of block_grid is the top of the picture)."""
    target_h = len(block_grid)
    target_w = len(block_grid[0]) if target_h else 0
    width, height, thickness, is_ns = _plane_dims(target_w, target_h, facing)

    if is_ns:
        w, l = width, thickness
    else:
        w, l = thickness, width

    unique_blocks = sorted({b for row in block_grid for b in row if b is not None})
    palette = Compound({AIR_BLOCK: Int(0)})
    block_index = {AIR_BLOCK: 0}
    for i, name in enumerate(unique_blocks, start=1):
        palette[name] = Int(i)
        block_index[name] = i

    index_layers = [[[0] * w for _ in range(l)] for _ in range(height)]  # [y][z][x]

    for row_i, row in enumerate(block_grid):
        hy = height - 1 - row_i  # flip so image row 0 (top) ends up at the top
        for col_i, block in enumerate(row):
            if block is None:
                continue
            hx = col_i if is_ns else 0
            hz = 0 if is_ns else col_i
            index_layers[hy][hz][hx] = block_index[block]

    block_data = build_block_data(w, height, l, lambda x, y, z: index_layers[y][z][x])

    return Compound({
        "Version": Int(2),
        "DataVersion": Int(data_version),
        "Width": Short(w),
        "Height": Short(height),
        "Length": Short(l),
        "PaletteMax": Int(len(palette)),
        "Palette": palette,
        "BlockData": block_data,
        "BlockEntities": List[Compound](),
        "Offset": IntArray([0, 0, 0]),
        "Metadata": Compound({}),
    })


def generate_command_block_wall_schem(block_grid, facing, player_pos, data_version=3578):
    """Build a data Compound: a flat wall of command blocks (one per opaque
    pixel) whose Command runs `setblock` at the absolute world position
    derived from `player_pos` (the coordinates recorded when the reference
    scan/photo was taken) plus that pixel's offset in the wall."""
    target_h = len(block_grid)
    target_w = len(block_grid[0]) if target_h else 0
    width, height, thickness, is_ns = _plane_dims(target_w, target_h, facing)

    if is_ns:
        w, l = width, thickness
    else:
        w, l = thickness, width

    px, py, pz = map(int, player_pos)

    cb_state = command_block_state(facing)
    palette = Compound({AIR_BLOCK: Int(0), cb_state: Int(1)})
    index_layers = [[[0] * w for _ in range(l)] for _ in range(height)]  # [y][z][x]
    block_entities = List[Compound]()

    for row_i, row in enumerate(block_grid):
        hy = height - 1 - row_i
        for col_i, block in enumerate(row):
            if block is None:
                continue
            hx = col_i if is_ns else 0
            hz = 0 if is_ns else col_i
            index_layers[hy][hz][hx] = 1

            abs_x = px + hx
            abs_y = py + hy
            abs_z = pz + hz
            cmd = f"setblock {abs_x} {abs_y} {abs_z} {block}"
            block_entities.append(make_command_block_entity((hx, hy, hz), cmd))

    block_data = build_block_data(w, height, l, lambda x, y, z: index_layers[y][z][x])

    return Compound({
        "Version": Int(2),
        "DataVersion": Int(data_version),
        "Width": Short(w),
        "Height": Short(height),
        "Length": Short(l),
        "PaletteMax": Int(len(palette)),
        "Palette": palette,
        "BlockData": block_data,
        "BlockEntities": block_entities,
        "Offset": IntArray([0, 0, 0]),
        "Metadata": Compound({}),
    })
