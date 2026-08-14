# worldedit_tab/stage/scan_converter.py
"""
Scans a real, already-built WorldEdit schematic (a physical screen panel
you built and captured with //schematic save or //copy+export) and
records, for every (row, col) of its own width x height footprint, the
WORLD position of whichever block is its "front surface" -- the first
non-air block found scanning along the depth axis. This works exactly
the same whether the panel is a perfectly flat wall (every pixel gets
the same depth) or a curved/stepped/angled surface (each pixel's depth
varies independently) -- there's no assumption of flatness anywhere in
this code.

facing determines which local axis is "depth" (the axis scanned through
to find the front surface) and which is "width", using the SAME
north/south -> depth-is-Z, east/west -> depth-is-X convention as the
GIF/Video/Image command block tabs elsewhere in this project (is_ns).
Height is always local Y. Row 0 of the resulting shape is the TOP of
the panel (highest Y), matching the row-0-is-top convention used
throughout the rest of this project for image/frame data.

scan_from_min picks which side of the bounding box is "front": True
scans from the lowest depth-axis coordinate toward the highest, taking
the first non-air block found (front = the low-coordinate side); False
scans the other way. Get this backward and the scan still succeeds --
it'll just find the BACK surface of a multi-layer-thick build instead
of the front -- so it's worth checking the recorded positions against
what you expect before using them.

The world position for each pixel is computed as world_anchor + the
block's LOCAL position within the schematic (the same offset convention
used for the standing_pos/paste-target math elsewhere in this project:
no rotation, local (0,0,0) of the schematic corresponds to world_anchor).
world_anchor should be wherever this schematic's local (0,0,0) actually
sits in your world right now -- NOT necessarily where you're standing,
since the panel this describes is already built.
"""

import json

from ..common.schem_io import read_block_data

AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def scan_screen_shape(schem_data, facing: str, scan_from_min: bool = True):
    """Returns (width, height, shape_grid).

    shape_grid[row][col] is either None (no non-air block found in that
    entire depth-axis column) or (local_x, local_y, local_z) -- the
    LOCAL position (within the schematic's own bounding box) of the
    front-most non-air block for that pixel.
    """
    width_val = int(schem_data["Width"])
    height_val = int(schem_data["Height"])
    length_val = int(schem_data["Length"])

    if width_val <= 0 or height_val <= 0 or length_val <= 0:
        raise ValueError("Schematic has zero or negative dimensions -- nothing to scan.")

    palette = schem_data["Palette"]
    air_indices = set()
    for name, idx in palette.items():
        base_name = str(name).split("[")[0]
        if base_name in AIR_NAMES:
            air_indices.add(int(idx))
    if not air_indices:
        raise ValueError(
            "This schematic's palette has no air block at all -- can't tell 'solid' from "
            "'empty', so there's nothing to scan for a front surface."
        )

    indices = read_block_data(schem_data["BlockData"], width_val, height_val, length_val)

    is_ns = facing in ("north", "south")
    if is_ns:
        width_axis_size, depth_axis_size = width_val, length_val
    else:
        width_axis_size, depth_axis_size = length_val, width_val

    depth_range = range(depth_axis_size) if scan_from_min else range(depth_axis_size - 1, -1, -1)

    shape_grid = [[None] * width_axis_size for _ in range(height_val)]
    for row_i in range(height_val):
        y = height_val - 1 - row_i  # row 0 = top = highest local Y
        for col_i in range(width_axis_size):
            found = None
            for d in depth_range:
                if is_ns:
                    lx, lz = col_i, d
                else:
                    lx, lz = d, col_i
                if indices[y][lz][lx] not in air_indices:
                    found = (lx, y, lz)
                    break
            shape_grid[row_i][col_i] = found

    return width_axis_size, height_val, shape_grid


def build_screen_object(name: str, width: int, height: int, shape_grid, world_anchor: tuple):
    """Combines a scanned LOCAL shape_grid with a world anchor to produce
    the screen object's own saveable form -- every pixel's absolute
    WORLD position baked in directly (or None), so nothing downstream
    needs to re-derive it or care how it was scanned."""
    ax, ay, az = world_anchor
    pixels = []
    covered = 0
    for row in shape_grid:
        out_row = []
        for cell in row:
            if cell is None:
                out_row.append(None)
            else:
                lx, ly, lz = cell
                out_row.append([ax + lx, ay + ly, az + lz])
                covered += 1
        pixels.append(out_row)

    if covered == 0:
        raise ValueError(
            "No blocks were found anywhere in this scan -- every pixel came back empty. "
            "Check the facing and scan direction match how the panel was actually built."
        )

    return {
        "name": name,
        "width": width,
        "height": height,
        "pixels": pixels,
    }


def save_screen_object(screen_obj: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(screen_obj, f, indent=2)


def load_screen_object(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    for key in ("name", "width", "height", "pixels"):
        if key not in obj:
            raise ValueError(f"Not a valid screen object file -- missing '{key}'.")
    return obj
