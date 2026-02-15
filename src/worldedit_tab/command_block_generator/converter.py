# src/worldedit_tab/command_block_generator/converter.py
import logging
from nbtlib.tag import Compound, List, Byte, Int, Long, Short, ByteArray, String, IntArray

AIR_BLOCK = "minecraft:air"
COMMAND_BLOCK_STATE = "minecraft:command_block[conditional=false,facing=up]"

def generate_block_list(data, player_pos: tuple[float, float, float]) -> list[str]:
    """Generate human-readable list of blocks with absolute coordinates."""
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
                if block and block != AIR_BLOCK:  # optional: skip air
                    abs_x = px + int(offset[0]) + hx
                    abs_y = py + int(offset[1]) + hy
                    abs_z = pz + int(offset[2]) + hz
                    lines.append(f"Block at {abs_x} {abs_y} {abs_z}: {block}")
    return lines


def convert_to_command_blocks(data, player_pos: tuple[float, float, float]) -> Compound:
    """Convert schematic blocks → command blocks that place the original blocks."""
    width = int(data['Width'])
    height = int(data['Height'])
    length = int(data['Length'])
    palette = data['Palette']
    block_data = data['BlockData']
    offset = data.get('Offset', IntArray([0, 0, 0]))

    px, py, pz = player_pos
    inv_palette = {int(v): k for k, v in palette.items()}

    new_palette = Compound({})
    cb_idx = 0
    new_palette[COMMAND_BLOCK_STATE] = Int(cb_idx)
    palette_max = 1

    air_idx = None
    if AIR_BLOCK in palette:
        air_idx = palette_max
        new_palette[AIR_BLOCK] = Int(air_idx)
        palette_max += 1

    new_block_data = ByteArray([0] * (width * height * length))
    new_block_entities = List[Compound]()

    for hy in range(height):
        for hz in range(length):
            for hx in range(width):
                idx = hy * (length * width) + hz * width + hx
                state_id = int(block_data[idx])
                block = inv_palette.get(state_id)
                if not block:
                    continue

                abs_x = int(px + int(offset[0]) + hx)
                abs_y = int(py + int(offset[1]) + hy)
                abs_z = int(pz + int(offset[2]) + hz)

                if block == AIR_BLOCK and air_idx is not None:
                    new_block_data[idx] = air_idx
                else:
                    new_block_data[idx] = cb_idx

                    cmd = f"setblock {abs_x} {abs_y} {abs_z} {block}"
                    be = Compound({
                        "id": String("minecraft:command_block"),
                        "Pos": IntArray([hx, hy, hz]),
                        "Command": String(cmd),
                        "CustomName": String('{"text":"@"}'),
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
        "Width": data["Width"],
        "Height": data["Height"],
        "Length": data["Length"],
        "PaletteMax": Int(palette_max),
        "Palette": new_palette,
        "BlockData": new_block_data,
        "BlockEntities": new_block_entities,
        "Offset": data["Offset"],
        "Metadata": data.get("Metadata", Compound({})),
    })

    return new_data