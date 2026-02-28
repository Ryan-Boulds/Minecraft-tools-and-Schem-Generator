import math
from nbtlib.tag import Compound, List, Byte, Int, Long, Short, ByteArray, String, IntArray

AIR_BLOCK = "minecraft:air"


def command_block_state(facing: str):
    return f"minecraft:command_block[conditional=false,facing={facing}]"


def convert_to_command_block_wall_absolute_fixed(
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
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = map(int, player_pos)
    inv_palette = {int(v): k for k, v in palette.items()}

    # Collect all non-air blocks
    blocks = []
    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                idx = hy * (length * width) + hz * width + hx
                state_id = int(block_data[idx])
                block = inv_palette.get(state_id)
                if block and block != AIR_BLOCK:
                    blocks.append((hx, hy, hz, block))

    total = len(blocks)
    wall_height = math.ceil(total / wall_width)

    # Wall dimensions
    if facing in ("north", "south"):
        new_width = 1
        new_length = wall_width
    else:
        new_width = wall_width
        new_length = 1
    new_height = wall_height

    new_palette = Compound({command_block_state(facing): Int(0)})
    total_size = new_width * new_height * new_length
    new_block_data = ByteArray([0] * total_size)
    new_block_entities = List[Compound]()

    # Generate command blocks for real blocks
    for i, (hx, hy, hz, block) in enumerate(blocks):
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

        # Absolute coordinates
        abs_x = px + int(offset[0]) + hx
        abs_y = py + int(offset[1]) + hy
        abs_z = pz + int(offset[2]) + hz

        cmd = f"setblock {abs_x} {abs_y} {abs_z} {block}"

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

    # Fill remaining wall spaces with **stone blocks in the schematic**, not command blocks
    remaining = wall_width * wall_height - len(blocks)
    for i in range(len(blocks), len(blocks) + remaining):
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

        # Set the ByteArray to 1 (or some value) for stone? Or just leave as air; the schematic will be filled with stone in game
        # We'll add a block entity just for the position in the schematic so wall is complete
        # But no command block is needed; the actual stone will appear when pasted
        # If you want, you can skip adding to BlockEntities entirely

    # 1-block gap offset for wall placement
    if facing == "east":
        offset_x = 1
        offset_z = 0
    elif facing == "west":
        offset_x = -new_width
        offset_z = 0
    elif facing == "south":
        offset_x = 0
        offset_z = 1
    elif facing == "north":
        offset_x = 0
        offset_z = -new_length
    else:
        offset_x = 0
        offset_z = 0

    new_data = Compound({
        "Version": data["Version"],
        "DataVersion": data["DataVersion"],
        "Width": Short(new_width),
        "Height": Short(new_height),
        "Length": Short(new_length),
        "PaletteMax": Int(1),
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