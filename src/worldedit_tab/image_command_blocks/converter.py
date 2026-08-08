# worldedit_tab/image_command_blocks/converter.py
"""
Builds a wall of command blocks that recreates an image when powered,
placed at explicit world coordinates rather than a single player
position + local offsets (that's what Image to Pixel Art's command-block
mode already does, and it's left alone).

COORDINATE CONVENTION (documented once, here, since it's otherwise
ambiguous): the source image's left edge maps to the MINIMUM value of
the wall's horizontal axis, and its top edge maps to the MAXIMUM Y --
i.e. picture it lying flat and reading left-to-right, top-to-bottom,
exactly like the image file itself, then standing that up into the
world. Which world axis is "horizontal" depends on facing:
  * facing north or south -> horizontal axis is X, depth (thickness) is Z
  * facing east or west   -> horizontal axis is Z, depth (thickness) is X
Y is always vertical.

Two ways to size and place the wall:

1. compute_corners_fixed_size() -- you already know the wall's pixel
   dimensions (from the same width/height controls as Image to Pixel
   Art) and you're placing it by ONE corner. Pick which corner that is
   (bottom_left/bottom_right/top_left/top_right) and give its X/Y/Z; the
   other three corners are fully determined (scale is "locked" -- you
   can't stretch by moving a corner here, you can only reposition the
   whole rectangle).

2. compute_corners_stretch() -- you give two DIAGONAL corners and the
   wall's pixel grid is resized to exactly fill that span. Still flat
   (2D) -- only the horizontal and vertical extents come from the two
   points, the depth (single value) is taken from the first point.
   Optionally locks the resized grid to the source image's aspect
   ratio, driven by whichever axis you choose (the other axis's span
   from your two points is then overridden to match); leave it
   unlocked to stretch freely onto whatever span you gave, distorting
   the image if the two corners don't happen to match its aspect ratio.
"""

from nbtlib.tag import Compound, Int, Short, IntArray, List

from ..common.schem_io import command_block_state, make_command_block_entity, build_block_data

AIR_BLOCK = "minecraft:air"

CORNER_NAMES = ("bottom_left", "bottom_right", "top_left", "top_right")


def _corners_from_span(minH, maxH, minY, maxY, depth, is_ns):
    def to_xyz(h, y):
        return (h, y, depth) if is_ns else (depth, y, h)

    return {
        "bottom_left": to_xyz(minH, minY),
        "bottom_right": to_xyz(maxH, minY),
        "top_left": to_xyz(minH, maxY),
        "top_right": to_xyz(maxH, maxY),
        "minH": minH, "maxH": maxH, "minY": minY, "maxY": maxY, "depth": depth,
        "is_ns": is_ns,
        "width_blocks": maxH - minH + 1,
        "height_blocks": maxY - minY + 1,
    }


def compute_corners_fixed_size(anchor_corner: str, anchor_xyz, width_blocks: int,
                                height_blocks: int, facing: str) -> dict:
    """anchor_xyz: (x, y, z) of the corner named by `anchor_corner`
    (one of CORNER_NAMES). width_blocks/height_blocks: the wall's fixed
    pixel-grid size. Returns the same shape as compute_corners_stretch()."""
    if anchor_corner not in CORNER_NAMES:
        raise ValueError(f"anchor_corner must be one of {CORNER_NAMES}")
    if width_blocks < 1 or height_blocks < 1:
        raise ValueError("width_blocks and height_blocks must be positive")

    is_ns = facing in ("north", "south")
    ax, ay, az = anchor_xyz
    anchorH = ax if is_ns else az
    anchorY = ay
    depth = az if is_ns else ax

    is_left = anchor_corner in ("bottom_left", "top_left")
    is_bottom = anchor_corner in ("bottom_left", "bottom_right")

    minH = anchorH if is_left else anchorH - (width_blocks - 1)
    maxH = minH + (width_blocks - 1)
    minY = anchorY if is_bottom else anchorY - (height_blocks - 1)
    maxY = minY + (height_blocks - 1)

    return _corners_from_span(minH, maxH, minY, maxY, depth, is_ns)


def compute_corners_stretch(point_a, point_b, facing: str, orig_w: int, orig_h: int,
                             lock_aspect: bool = False, base_on: str = "horizontal") -> dict:
    """point_a/point_b: (x, y, z) of any two DIAGONALLY opposite corners
    (order doesn't matter -- min/max is taken automatically). The wall is
    resized to exactly span between them.

    If lock_aspect is True, the source image's aspect ratio (orig_w x
    orig_h) is preserved: base_on="horizontal" derives the height from
    the given horizontal span (overriding whatever vertical span the two
    points implied); base_on="vertical" does the reverse. If lock_aspect
    is False, both spans from the two points are used exactly as given,
    which will distort the image if they don't already match its aspect
    ratio.

    Adds "depth_mismatch": True to the result if the two points disagree
    on the depth (thickness) axis -- the first point's value is used,
    but the caller should warn the user.
    """
    is_ns = facing in ("north", "south")
    ax, ay, az = point_a
    bx, by, bz = point_b
    aH = ax if is_ns else az
    bH = bx if is_ns else bz
    depth_a = az if is_ns else ax
    depth_b = bz if is_ns else bx

    minH, maxH = min(aH, bH), max(aH, bH)
    minY, maxY = min(ay, by), max(ay, by)

    if lock_aspect:
        width_blocks = maxH - minH + 1
        height_blocks = maxY - minY + 1
        if base_on == "horizontal":
            height_blocks = max(1, round(width_blocks * orig_h / orig_w))
            maxY = minY + (height_blocks - 1)
        else:  # "vertical"
            width_blocks = max(1, round(height_blocks * orig_w / orig_h))
            maxH = minH + (width_blocks - 1)

    result = _corners_from_span(minH, maxH, minY, maxY, depth_a, is_ns)
    result["depth_mismatch"] = (depth_a != depth_b)
    return result


def generate_command_block_wall_from_corners(block_grid, facing: str, corners: dict,
                                              data_version: int = 3578) -> Compound:
    """Build the data Compound for a command-block wall recreating
    `block_grid` (as produced by image_to_pixelart.converter's
    build_pixel_grid + match_palette), placed at the world coordinates
    described by `corners` (from compute_corners_fixed_size() or
    compute_corners_stretch()).

    `block_grid`'s dimensions are used directly for the wall's pixel
    grid -- if it doesn't match corners["width_blocks"] / ["height_blocks"],
    resize the source image to that size before calling match_palette,
    so the two stay in sync (the GUI does this).
    """
    target_h = len(block_grid)
    target_w = len(block_grid[0]) if target_h else 0

    is_ns = corners["is_ns"]
    w = target_w if is_ns else 1
    l = 1 if is_ns else target_w
    height = target_h

    minH = corners["minH"]
    minY = corners["minY"]
    depth = corners["depth"]

    cb_state = command_block_state(facing)
    palette = Compound({AIR_BLOCK: Int(0), cb_state: Int(1)})
    index_layers = [[[0] * w for _ in range(l)] for _ in range(height)]  # [y][z][x]
    block_entities = List[Compound]()

    for row_i, row in enumerate(block_grid):
        hy = height - 1 - row_i  # image row 0 (top) -> top of the wall
        for col_i, block in enumerate(row):
            if block is None:
                continue
            hx = col_i if is_ns else 0
            hz = 0 if is_ns else col_i
            index_layers[hy][hz][hx] = 1

            world_h = minH + col_i
            world_y = minY + hy
            if is_ns:
                abs_x, abs_y, abs_z = world_h, world_y, depth
            else:
                abs_x, abs_y, abs_z = depth, world_y, world_h

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
