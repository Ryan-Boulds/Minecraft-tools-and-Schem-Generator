# worldedit_tab/common/schem_io.py
"""
Shared helpers for reading and writing WorldEdit .schem files (Sponge
Schematic Format, versions 1/2/3).

THE BIG ONE: BlockData IS A VARINT STREAM, NOT ONE BYTE PER VOXEL
-------------------------------------------------------------------
Per the official Sponge Schematic Specification, BlockData is typed
`varint[]`: "Each integer is bitpacked into a single byte with varint
encoding... depending on the length, each proceeding byte is or'ed and
current value bit shifted by the length multiplied by 7." Every writer
in this project (and every reader in convert_to_command_blocks) used to
treat BlockData as one raw byte per voxel instead. A palette index under
128 fits in exactly one varint byte, which is indistinguishable from
"just a byte" -- so small-palette schematics worked by coincidence,
right up until a palette passed 128 entries (index 128 needs a 2-byte
varint). Writing it as a single byte after that point misaligns every
voxel that follows, and the misread eventually lands on garbage that
doesn't match any palette entry -- a null block, which is exactly the
`NullPointerException` on `BlockStateHolder.toBaseBlock()` a 141-block
Mario pixel-art schematic hit. Worse, the naive write path could crash
outright: nbtlib's ByteArray refuses values outside -128..127, so
assigning a raw palette index of 128+ throws `OverflowError` before a
file even gets written.

Fixed with build_block_data() (write) and read_block_data() (read),
which correctly varint-encode/decode the whole stream. Every schem
writer and reader in this project goes through these now -- see their
docstrings below for the full explanation.

THE ROOT-WRAPPER BUG (fixed, then correctly un-fixed)
---------------------------------------------------------
An early version of this file wrapped every written .schem in
`{"Schematic": {...}}`, on the theory the format required it. It
doesn't -- WorldEdit's SpongeSchematicReader.getBaseTag() reads the NBT
root tag directly, no wrapper. That extra layer is what caused
`missing a "Version" tag` errors. Reverted: schematic data is written
straight to the NBT root.

BLOCKENTITY Id CASING
----------------------
Every block entity needs a *required* `Id` tag (capital I). Getting the
case wrong (lowercase "id") is a very plausible cause of a schematic
failing to load outright, since it's a required tag.
"""

import gzip
import logging

import nbtlib
from nbtlib.tag import Compound, Byte, Int, Long, Short, ByteArray, String, IntArray, List


def save_schematic(schematic_compound: Compound, file_path: str) -> None:
    """Write a schematic data Compound to `file_path` as a valid gzipped .schem.

    IMPORTANT: WorldEdit's SpongeSchematicReader.getBaseTag() reads the NBT
    root tag directly and requires Version/Width/Palette/BlockData/etc. to
    live right there -- there is NO "Schematic" wrapper key in this format.
    So this just writes `schematic_compound`'s keys straight to the NBT
    root, same as your known-working timeline_exporter code does.
    """
    nbt_file = nbtlib.File(schematic_compound)
    with open(file_path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb") as gz:
            nbt_file.write(gz)
    logging.debug(f"Schematic saved to {file_path}")


def load_schematic(file_path: str):
    """Load a .schem file and return (data_compound, debug_dict).

    Data lives directly at the NBT root. For backwards compatibility this
    also transparently unwraps files that have a top-level "Schematic" key
    -- that shape was produced briefly by a since-reverted bug in this
    project's own writer, so any such files lying around still load.
    """
    debug = {
        "file_path": file_path,
        "success": False,
        "error": None,
        "loaded_type": None,
        "wrapped": None,
        "has_width": False,
        "width_value": None,
        "palette_max": None,
        "offset": None,
        "sample_keys": [],
    }

    try:
        raw = nbtlib.load(file_path)
        debug["loaded_type"] = type(raw).__name__

        if "Version" not in raw and "Schematic" in raw:
            # Produced by the brief root-wrapper bug -- unwrap it.
            data = raw["Schematic"]
            debug["wrapped"] = True
        else:
            data = raw
            debug["wrapped"] = False

        debug["success"] = True
        debug["has_width"] = "Width" in data
        debug["width_value"] = data.get("Width")
        debug["palette_max"] = data.get("PaletteMax")
        debug["offset"] = data.get("Offset")
        debug["sample_keys"] = list(data.keys())[:12]

        return data, debug

    except Exception as e:
        debug["error"] = f"{type(e).__name__}: {str(e)}"
        logging.error(f"Failed to load schematic {file_path}: {debug['error']}")
        return None, debug


def command_block_state(facing: str) -> str:
    return f"minecraft:command_block[conditional=false,facing={facing}]"


def encode_varint(value: int):
    """LEB128-style varint encoding, exactly as the Sponge schematic spec
    requires for BlockData/BiomeData entries: 7 data bits per byte, high
    bit set on every byte except the last. Returns a list of UNSIGNED
    byte values (0-255) -- caller must convert to nbtlib's signed byte
    range before storing (see build_block_data)."""
    out = []
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return out


def decode_varint(data, pos: int = 0):
    """Inverse of encode_varint(). Returns (value, next_pos). `data` must
    be indexable and yield unsigned 0-255 byte values (see
    _unsigned_bytes() if reading from an nbtlib ByteArray)."""
    result = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _unsigned_bytes(values):
    """Convert an iterable of signed byte values (-128..127, e.g. from an
    nbtlib ByteArray) to unsigned (0..255)."""
    return [(v + 256) if v < 0 else v for v in values]


def build_block_data(width, height, length, index_at) -> ByteArray:
    """Build the BlockData ByteArray tag, correctly varint-encoded per the
    Sponge schematic spec.

    THIS IS THE FIX for a schematic that pastes as mostly-blank / loads
    with a NullPointerException on BlockStateHolder.toBaseBlock() once
    the palette passes 128 entries. The spec defines BlockData as a
    `varint[]`, NOT one raw byte per voxel -- a palette index under 128
    fits in a single varint byte (indistinguishable from "just a byte"),
    which is exactly why small-palette schematics worked fine and this
    stopped working the moment a palette grew past 128 unique blocks:
    index 128 needs a 2-byte varint, and writing it as one raw byte
    misaligns every voxel that follows, eventually landing on a byte
    sequence that decodes to an index with no matching palette entry --
    a null block, which is exactly the NPE this was causing.

    `index_at(x, y, z)` should return the palette index (int) for that
    voxel. Iterates in the exact order the spec requires -- x fastest,
    then z, then y (`x + z * Width + y * Width * Length`) -- and appends
    each voxel's variable-length varint to a growing byte stream, so the
    final array length is NOT necessarily width*height*length; it's
    exactly that only when every index fits in one byte.
    """
    raw = []
    for y in range(height):
        for z in range(length):
            for x in range(width):
                raw.extend(encode_varint(index_at(x, y, z)))
    signed = [(b - 256) if b > 127 else b for b in raw]
    return ByteArray(signed)


def read_block_data(block_data, width, height, length):
    """Decode a varint-encoded BlockData ByteArray (or plain list of
    signed byte values) into a 3D nested list indices[y][z][x] -> int
    palette index. This is the read-side counterpart to
    build_block_data() -- needed any time we load a schematic that might
    have come from somewhere else (a real WorldEdit build, not just our
    own output), since those routinely have palettes well past 128
    blocks and the old code's flat one-byte-per-voxel indexing would
    silently misread them the same way it silently miswrote them.
    """
    unsigned = _unsigned_bytes(block_data)
    pos = 0
    indices = [[[0] * width for _ in range(length)] for _ in range(height)]
    for y in range(height):
        for z in range(length):
            for x in range(width):
                val, pos = decode_varint(unsigned, pos)
                indices[y][z][x] = val
    return indices


def make_command_block_entity(pos, command: str, custom_name: str = None) -> Compound:
    """Build a BlockEntities compound entry for a command block at local Pos.

    IMPORTANT: the Sponge schematic spec requires the block entity's type
    tag to be "Id" (capital I), not "id". This is a *required* tag per the
    spec, so getting the case wrong isn't cosmetic -- it can make WorldEdit
    throw while parsing block entities and fail the whole load. The known-
    working timeline_exporter code uses "Id"; match it.
    """
    entity = Compound({
        "Id": String("minecraft:command_block"),
        "Pos": IntArray(list(pos)),
        "Command": String(command),
        "auto": Byte(0),
        "conditionMet": Byte(0),
        "powered": Byte(0),
        "TrackOutput": Byte(1),
        "SuccessCount": Int(0),
        "UpdateLastExecution": Byte(1),
        "LastExecution": Long(0),
        "LastOutput": String(""),
    })
    if custom_name:
        entity["CustomName"] = String(custom_name)
    return entity


def new_schematic_compound(width, height, length, palette, block_data, block_entities=None,
                            offset=(0, 0, 0), data_version=3578, metadata=None):
    """Convenience builder for the data Compound passed to save_schematic()."""
    return Compound({
        "Version": Int(2),
        "DataVersion": Int(data_version),
        "Width": Short(width),
        "Height": Short(height),
        "Length": Short(length),
        "PaletteMax": Int(len(palette)),
        "Palette": palette,
        "BlockData": block_data,
        "BlockEntities": block_entities if block_entities is not None else List[Compound](),
        "Offset": IntArray(list(offset)),
        "Metadata": metadata if metadata is not None else Compound({}),
    })
