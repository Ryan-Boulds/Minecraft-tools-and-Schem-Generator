# worldedit_tab/convert_to_command_blocks/loader.py
"""
Thin wrapper kept for backwards compatibility - all real logic now lives in
worldedit_tab.common.schem_io so every tab loads .schem files the same way
(and benefits from the same fix for legacy/unwrapped files).
"""

from ..common.schem_io import load_schematic

__all__ = ["load_schematic"]
