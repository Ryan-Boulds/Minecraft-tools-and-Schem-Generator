# worldedit_tab/convert_to_command_blocks/converter.py
"""
Reads an existing .schem (which may come from anywhere -- a real WorldEdit
build, not just this app's own output) and converts it into command-block
forms. Every function here used to read BlockData as one raw byte per
voxel; the Sponge spec actually defines it as a varint stream, so any
input schematic with a palette past 128 blocks (routine for a real,
detailed build) was being silently misread. Fixed via
common.schem_io.read_block_data() -- see that module's docstring for the
full story. The three functions that also WRITE a new schematic
(convert_to_command_blocks, convert_to_command_block_wall,
convert_to_command_block_wall_projected) only ever use 1-2 palette
entries in their OUTPUT, so their write side was never actually broken by
this, but they're routed through build_block_data() too for consistency.
"""
import math
from collections import defaultdict

from nbtlib.tag import Compound, Int, Short, IntArray, List

from ..common.schem_io import command_block_state, make_command_block_entity, build_block_data, read_block_data

AIR_BLOCK = "minecraft:air"


def generate_block_list(data, player_pos: tuple[float, float, float]) -> list[str]:
    lines = []
    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = player_pos
    inv_palette = {int(v): k for k, v in palette.items()}
    indices = read_block_data(data['BlockData'], width, height, length)

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                state_id = indices[hy][hz][hx]
                block = inv_palette.get(state_id)

                if block and block != AIR_BLOCK:
                    abs_x = px + int(offset[0]) + hx
                    abs_y = py + int(offset[1]) + hy
                    abs_z = pz + int(offset[2]) + hz
                    lines.append(f"Block at {abs_x} {abs_y} {abs_z}: {block}")

    return lines


def convert_to_command_blocks(data, player_pos: tuple[float, float, float]) -> Compound:
    # ... original shape (unchanged)
    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = map(int, player_pos)
    inv_palette = {int(v): k for k, v in palette.items()}
    indices = read_block_data(data['BlockData'], width, height, length)

    new_palette = Compound({})
    cb_state = command_block_state("up")
    new_palette[cb_state] = Int(0)

    new_block_entities = List[Compound]()

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                state_id = indices[hy][hz][hx]
                block = inv_palette.get(state_id)

                if not block or block == AIR_BLOCK:
                    continue

                abs_x = px + int(offset[0]) + hx
                abs_y = py + int(offset[1]) + hy
                abs_z = pz + int(offset[2]) + hz

                cmd = f"setblock {abs_x} {abs_y} {abs_z} {block}"
                new_block_entities.append(make_command_block_entity((hx, hy, hz), cmd))

    # Only one palette entry exists (the command-block state), so every
    # voxel in the bounding box is index 0 -- unchanged from the original
    # behavior. Positions with no matching BlockEntity above just become
    # blank/no-op command blocks.
    new_block_data = build_block_data(width, height, length, lambda x, y, z: 0)

    new_data = Compound({
        "Version": data["Version"],
        "DataVersion": data["DataVersion"],
        "Width": Short(width),
        "Height": Short(height),
        "Length": Short(length),
        "PaletteMax": Int(1),
        "Palette": new_palette,
        "BlockData": new_block_data,
        "BlockEntities": new_block_entities,
        "Offset": IntArray([0, 0, 0]),
        "Metadata": Compound({}),
    })

    return new_data


def convert_to_command_block_wall(data, player_pos, wall_width: int, facing: str) -> Compound:
    # Regular wall - unchanged
    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = map(int, player_pos)
    inv_palette = {int(v): k for k, v in palette.items()}
    indices = read_block_data(data['BlockData'], width, height, length)

    real_blocks = []
    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                state_id = indices[hy][hz][hx]
                block = inv_palette.get(state_id)

                if block and block != AIR_BLOCK:
                    real_blocks.append((hx, hy, hz, block))

    total_real = len(real_blocks)
    wall_height = math.ceil(total_real / wall_width)

    if facing in ("north", "south"):
        new_width = 1
        new_length = wall_width
    else:
        new_width = wall_width
        new_length = 1

    new_height = wall_height
    total_slots = new_width * new_height * new_length

    cb_state = command_block_state(facing)
    new_palette = Compound({
        cb_state: Int(0),
        "minecraft:stone": Int(1),
    })

    new_indices = [[[1] * new_width for _ in range(new_length)] for _ in range(new_height)]  # [y][z][x], default stone
    new_block_entities = List[Compound]()

    for i, (local_x, local_y, local_z, block_type) in enumerate(real_blocks):
        if i >= total_slots:
            break

        col = i % wall_width
        row = i // wall_width

        if facing in ("north", "south"):
            wx = 0
            wy = row
            wz = col
        else:
            wx = col
            wy = row
            wz = 0

        abs_x = px + int(offset[0]) + local_x
        abs_y = py + int(offset[1]) + local_y
        abs_z = pz + int(offset[2]) + local_z

        new_indices[wy][wz][wx] = 0

        cmd = f"setblock {abs_x} {abs_y} {abs_z} {block_type}"
        new_block_entities.append(make_command_block_entity((wx, wy, wz), cmd))

    new_block_data = build_block_data(new_width, new_height, new_length,
                                       lambda x, y, z: new_indices[y][z][x])

    if facing == "east":
        offset_x, offset_z = 1, 0
    elif facing == "west":
        offset_x, offset_z = -new_width, 0
    elif facing == "south":
        offset_x, offset_z = 0, 1
    elif facing == "north":
        offset_x, offset_z = 0, -new_length
    else:
        offset_x, offset_z = 0, 0

    new_data = Compound({
        "Version": data["Version"],
        "DataVersion": data["DataVersion"],
        "Width": Short(new_width),
        "Height": Short(new_height),
        "Length": Short(new_length),
        "PaletteMax": Int(2),
        "Palette": new_palette,
        "BlockData": new_block_data,
        "BlockEntities": new_block_entities,
        "Offset": IntArray([offset_x, 0, offset_z]),
        "Metadata": Compound({
            "WEOffsetX": Int(offset_x),
            "WEOffsetY": Int(0),
            "WEOffsetZ": Int(offset_z)
        }),
    })

    return new_data


# ─────────────────────────────────────────────────────────────
# PROJECTED WALL — CONSISTENT & FIXED
# ─────────────────────────────────────────────────────────────

def convert_to_command_block_wall_projected(
    data,
    player_pos: tuple[float, float, float],
    facing: str
) -> Compound:

    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])

    palette = data['Palette']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = map(int, player_pos)
    inv_palette = {int(v): k for k, v in palette.items()}
    indices = read_block_data(data['BlockData'], width, height, length)

    # ------------------------------------------
    # Collect all real blocks
    # ------------------------------------------
    real_blocks = []

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                state_id = indices[hy][hz][hx]
                block = inv_palette.get(state_id)

                if block and block != AIR_BLOCK:
                    real_blocks.append((hx, hy, hz, block))

    if not real_blocks:
        return convert_to_command_block_wall(data, player_pos, 5, facing)

    # ------------------------------------------
    # Determine projection axis
    # ------------------------------------------
    if facing in ("north", "south"):
        # wall runs along Z
        proj_axis = lambda x, z: z
        wall_length = length
        new_width = 1
        new_length = wall_length
        is_ns = True
    else:
        # wall runs along X
        proj_axis = lambda x, z: x
        wall_length = width
        new_width = wall_length
        new_length = 1
        is_ns = False

    # ------------------------------------------
    # Stack overlaps
    # key = projected coordinate
    # ------------------------------------------
    stacks = defaultdict(list)

    for hx, hy, hz, block in real_blocks:
        p = proj_axis(hx, hz)
        stacks[p].append((hx, hy, hz, block))

    # sort by original Y first
    for p in stacks:
        stacks[p].sort(key=lambda b: b[1])

    max_height = max(len(v) for v in stacks.values())

    new_height = max_height

    cb_state = command_block_state(facing)

    new_palette = Compound({
        cb_state: Int(0),
        "minecraft:stone": Int(1)
    })

    new_indices = [[[1] * new_width for _ in range(new_length)] for _ in range(new_height)]  # [y][z][x], default stone
    new_block_entities = List[Compound]()

    # ------------------------------------------
    # Build wall
    # ------------------------------------------
    for proj_pos, block_list in stacks.items():

        for layer, (orig_x, orig_y, orig_z, block_type) in enumerate(block_list):

            if is_ns:
                wx = 0
                wz = proj_pos
            else:
                wx = proj_pos
                wz = 0

            wy = layer

            new_indices[wy][wz][wx] = 0

            # IMPORTANT:
            # command remains original coordinates
            abs_x = px + int(offset[0]) + orig_x
            abs_y = py + int(offset[1]) + orig_y
            abs_z = pz + int(offset[2]) + orig_z

            cmd = f"setblock {abs_x} {abs_y} {abs_z} {block_type}"
            new_block_entities.append(make_command_block_entity((wx, wy, wz), cmd))

    new_block_data = build_block_data(new_width, new_height, new_length,
                                       lambda x, y, z: new_indices[y][z][x])

    # ------------------------------------------
    # Correct offsets (same as normal wall)
    # ------------------------------------------
    if facing == "east":
        offset_x, offset_z = 1, 0
    elif facing == "west":
        offset_x, offset_z = -new_width, 0
    elif facing == "south":
        offset_x, offset_z = 0, 1
    elif facing == "north":
        offset_x, offset_z = 0, -new_length
    else:
        offset_x, offset_z = 0, 0

    return Compound({
        "Version": data["Version"],
        "DataVersion": data["DataVersion"],
        "Width": Short(new_width),
        "Height": Short(new_height),
        "Length": Short(new_length),
        "PaletteMax": Int(2),
        "Palette": new_palette,
        "BlockData": new_block_data,
        "BlockEntities": new_block_entities,
        "Offset": IntArray([offset_x, 0, offset_z]),
        "Metadata": Compound({
            "WEOffsetX": Int(offset_x),
            "WEOffsetY": Int(0),
            "WEOffsetZ": Int(offset_z)
        }),
    })
