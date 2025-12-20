# Created on 01:17 PM CDT, Monday, September 01, 2025
import logging
from .schematic_generator import generate_schematic_from_command

def process_command(gui, command):
    """Process a command in the WorldEdit Schematic tab and generate a schematic."""
    logging.debug(f"Processing command in WorldEdit Schematic tab: {command}")
    file_path = generate_schematic_from_command(gui, command)
    if file_path:
        gui.print_to_text(f"Generated schematic from command: {file_path}", "normal")
        return command
    return command