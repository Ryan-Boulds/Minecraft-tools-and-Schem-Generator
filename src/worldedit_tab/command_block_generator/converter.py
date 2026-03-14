import math
from nbtlib.tag import (
    Compound, List, Byte, Int, Long,
    Short, ByteArray, String, IntArray
)

AIR_BLOCK = "minecraft:air"


def command_block_state(facing: str):
    return f"minecraft:command_block[conditional=false,facing={facing}]"


# ─────────────────────────────────────────────────────────────
# DEBUG LISTING (unchanged)
# ─────────────────────────────────────────────────────────────

def generate_block_list(data, player_pos: tuple[float, float, float]) -> list[str]:
    lines = []
    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    block_data = data['BlockData']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = player_pos
    inv_palette = {int(v): k for k, v in palette.items()}

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                idx = hy * (length * width) + hz * width + hx
                state_id = int(block_data[idx])
                block = inv_palette.get(state_id)

                if block and block != AIR_BLOCK:
                    abs_x = px + int(offset[0]) + hx
                    abs_y = py + int(offset[1]) + hy
                    abs_z = pz + int(offset[2]) + hz
                    lines.append(f"Block at {abs_x} {abs_y} {abs_z}: {block}")

    return lines


# ─────────────────────────────────────────────────────────────
# ORIGINAL SHAPE CONVERSION (unchanged)
# ─────────────────────────────────────────────────────────────

def convert_to_command_blocks(
    data,
    player_pos: tuple[float, float, float]
) -> Compound:

    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    block_data = data['BlockData']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = map(int, player_pos)
    inv_palette = {int(v): k for k, v in palette.items()}

    new_palette = Compound({})
    cb_state = command_block_state("up")
    new_palette[cb_state] = Int(0)

    new_block_data = ByteArray([0] * (width * height * length))
    new_block_entities = List[Compound]()

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):

                idx = hy * (length * width) + hz * width + hx
                state_id = int(block_data[idx])
                block = inv_palette.get(state_id)

                if not block or block == AIR_BLOCK:
                    continue

                abs_x = px + int(offset[0]) + hx
                abs_y = py + int(offset[1]) + hy
                abs_z = pz + int(offset[2]) + hz

                cmd = f"setblock {abs_x} {abs_y} {abs_z} {block}"

                be = Compound({
                    "id": String("minecraft:command_block"),
                    "Pos": IntArray([hx, hy, hz]),
                    "Command": String(cmd),
                    "auto": Byte(0),
                    "conditionMet": Byte(0),
                    "powered": Byte(0),
                    "TrackOutput": Byte(1),
                    "SuccessCount": Int(0),
                    "UpdateLastExecution": Byte(1),
                    "LastExecution": Long(0),
                    "LastOutput": String("")
                })

                new_block_entities.append(be)

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


# ─────────────────────────────────────────────────────────────
# WALL CONVERSION — FIXED PADDING (no more stone at 0,0,0)
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# WALL CONVERSION — STONE FILLER + CORRECT ABSOLUTE COORDINATES
# ─────────────────────────────────────────────────────────────

def convert_to_command_block_wall(
    data,
    player_pos: tuple[float, float, float],
    wall_width: int,
    facing: str
) -> Compound:

    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    block_data = data['BlockData']
    offset = data.get('Offset', IntArray([0, 0, 0]))   # ← this was missing!

    # Player position you entered in the GUI (the point you stood at when //copy)
    px, py, pz = map(int, player_pos)

    inv_palette = {int(v): k for k, v in palette.items()}

    # Collect ONLY real non-air blocks + their local schematic coords
    real_blocks = []
    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                idx = hy * (length * width) + hz * width + hx
                state_id = int(block_data[idx])
                block = inv_palette.get(state_id)

                if block and block != AIR_BLOCK:
                    real_blocks.append((hx, hy, hz, block))

    total_real = len(real_blocks)
    wall_height = math.ceil(total_real / wall_width)

    # New wall dimensions
    if facing in ("north", "south"):
        new_width = 1
        new_length = wall_width
    else:
        new_width = wall_width
        new_length = 1

    new_height = wall_height
    total_slots = new_width * new_height * new_length

    # PALETTE: 0 = command block, 1 = minecraft:stone (filler)
    cb_state = command_block_state(facing)
    new_palette = Compound({
        cb_state:           Int(0),
        "minecraft:stone":  Int(1),
    })

    new_block_data = ByteArray([1] * total_slots)   # default = stone
    new_block_entities = List[Compound]()

    # Place command blocks ONLY for real blocks, using ABSOLUTE world coords
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

        # === ABSOLUTE COORDINATE CALCULATION (THIS IS THE FIX) ===
        abs_x = px + int(offset[0]) + local_x
        abs_y = py + int(offset[1]) + local_y
        abs_z = pz + int(offset[2]) + local_z

        # Mark position as command block
        flat_idx = wy * (new_length * new_width) + wz * new_width + wx
        new_block_data[flat_idx] = 0

        # Command now uses the REAL world position
        cmd = f"setblock {abs_x} {abs_y} {abs_z} {block_type}"

        be = Compound({
            "id": String("minecraft:command_block"),
            "Pos": IntArray([wx, wy, wz]),
            "Command": String(cmd),
            "auto": Byte(0),
            "conditionMet": Byte(0),
            "powered": Byte(0),
            "TrackOutput": Byte(1),
            "SuccessCount": Int(0),
            "UpdateLastExecution": Byte(1),
            "LastExecution": Long(0),
            "LastOutput": String("")
        })
        new_block_entities.append(be)

    # Offset for pasting the wall itself (1-block gap) — unchanged
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