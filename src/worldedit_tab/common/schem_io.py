# worldedit_tab/common/schem_io.py
"""
Shared helpers for reading and writing WorldEdit .schem files (Sponge
Schematic Format, versions 1/2/3).

THE BUG THAT WAS BREAKING EVERY GENERATED SCHEMATIC
-----------------------------------------------------
The Sponge Schematic spec requires the top-level NBT tag to be an UNNAMED
compound that contains exactly one key, "Schematic", which in turn holds
Version/Width/Height/Length/Palette/BlockData/etc.

The old code did:

    schematic = nbtlib.File(schematic_data)   # schematic_data = the data itself

That writes `schematic_data`'s keys directly at the NBT root, with no
"Schematic" wrapper. WorldEdit/Minecraft can't find `Schematic` at the root,
so //schem load (and dragging the file into a schematics folder) silently
fails or errors out. Every tab that saves a .schem needs to go through
`save_schematic()` below so this only has to be fixed in one place.
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
    (An earlier version of this file added one; that was wrong and broke
    loading. Verified against WorldEdit's actual source.) So this just
    writes `schematic_compound`'s keys straight to the NBT root, same as
    your known-working timeline_exporter code does.
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
