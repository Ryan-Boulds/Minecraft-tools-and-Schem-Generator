# parser.py - Schematic parsing logic

import nbtlib
import os

def parse_schematic(path):
    blocks = []
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return blocks

    try:
        schematic = nbtlib.load(path)  # Auto-detects gzip
    except Exception as e:
        print(f"Failed to load schematic: {e}")
        return blocks

    try:
        data = schematic  # nbtlib.load returns root compound
        width = int(data['Width'])
        height = int(data['Height'])
        length = int(data['Length'])
        palette = data['Palette']
        block_data = data['BlockData']
        offset = data.get('Offset', [0, 0, 0])
        ox, oy, oz = [int(v) for v in offset]

        inverse_palette = {int(v): str(k) for k, v in palette.items()}
        block_indices = [int(b) for b in block_data]

        for y in range(height):
            for z in range(length):
                for x in range(width):
                    index = y * (length * width) + z * width + x
                    idx = block_indices[index]
                    state = inverse_palette.get(idx, "minecraft:air")
                    block_name = state.split('[')[0]
                    if block_name != "minecraft:air":
                        blocks.append((x + ox, y + oy, z + oz, block_name))
    except Exception as e:
        print(f"Error parsing NBT: {e}")

    return blocks