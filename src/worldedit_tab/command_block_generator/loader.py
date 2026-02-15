# loader.py
import nbtlib
import logging
from nbtlib.tag import Compound

def load_schematic(file_path: str):
    """
    Load .schem file and return both the raw loaded object and a debug dictionary.
    """
    debug = {
        "file_path": file_path,
        "success": False,
        "error": None,
        "loaded_type": None,
        "has_width": False,
        "width_value": None,
        "palette_max": None,
        "offset": None,
        "sample_keys": [],
        "str_preview": ""
    }

    try:
        schem = nbtlib.load(file_path)
        debug["success"] = True
        debug["loaded_type"] = type(schem).__name__

        # schem is the root compound / File object
        debug["has_width"]   = 'Width' in schem
        debug["width_value"] = schem.get('Width')
        debug["palette_max"] = schem.get('PaletteMax')
        debug["offset"]      = schem.get('Offset')

        debug["sample_keys"] = list(schem.keys())[:12]

        try:
            str_schem = str(schem)
            debug["str_preview"] = (str_schem[:1400] + "...") if len(str_schem) > 1400 else str_schem
        except:
            debug["str_preview"] = "[could not convert to str]"

        return schem, debug

    except Exception as e:
        debug["error"] = f"{type(e).__name__}: {str(e)}"
        logging.error(f"Failed to load schematic {file_path}: {debug['error']}")
        return None, debug