import logging
import pyperclip
import tkinter as tk
import re

def modify_clipboard_command(gui):
    try:
        clipboard_content = pyperclip.paste().strip()
        block_type = gui.block_text.get().replace("__", ":") or "minecraft:lime_concrete"
        tag = gui.change_block_tag.get() or "beam1"

        # Regex for /setblock command
        setblock_pattern = r'^/setblock\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+([\w:]+)'
        # Regex for /summon minecraft:block_display command
        block_display_pattern = r'^/summon minecraft:block_display\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+\{.*block_state:\{Name:"([\w:]+)"\}.*Tags:\["([^"]+)"\].*\}$'

        setblock_match = re.match(setblock_pattern, clipboard_content)
        block_display_match = re.match(block_display_pattern, clipboard_content)

        if setblock_match:
            x, y, z, _ = setblock_match.groups()
            modified_command = f"/setblock {x} {y} {z} {block_type}"
            logging.debug(f"Modified setblock command: {modified_command}")
        elif block_display_match:
            x, y, z, _, old_tag = block_display_match.groups()
            # Replace block type and tag, preserving everything else
            modified_command = clipboard_content.replace(
                f'block_state:{{Name:"{block_display_match.group(4)}"}}',
                f'block_state:{{Name:"{block_type}"}}'
            ).replace(
                f'Tags:["{old_tag}"]',
                f'Tags:["{tag}"]'
            )
            logging.debug(f"Modified block display command: {modified_command}")
        else:
            logging.warning("Invalid clipboard command format")
            if hasattr(gui, 'change_block_cmd_text') and gui.change_block_cmd_text.winfo_exists():
                gui.change_block_cmd_text.delete("1.0", tk.END)
                gui.change_block_cmd_text.insert("1.0", "Error: Clipboard must contain a valid /setblock or /summon minecraft:block_display command.")
            return ""

        if hasattr(gui, 'change_block_cmd_text') and gui.change_block_cmd_text.winfo_exists():
            gui.change_block_cmd_text.delete("1.0", tk.END)
            gui.change_block_cmd_text.insert("1.0", modified_command)
        else:
            logging.warning("change_block_cmd_text not found or not initialized")

        pyperclip.copy(modified_command.encode('utf-8').decode('utf-8'))
        logging.debug("Modified command copied to clipboard.")
        return modified_command
    except Exception as e:
        logging.error(f"Error modifying clipboard command: {e}")
        if hasattr(gui, 'change_block_cmd_text') and gui.change_block_cmd_text.winfo_exists():
            gui.change_block_cmd_text.delete("1.0", tk.END)
            gui.change_block_cmd_text.insert("1.0", "Error: Failed to parse or modify clipboard command.")
        return ""

def generate_kill_block_display_command(gui):
    try:
        tag = gui.change_block_tag.get() or "beam1"
        command = f"/kill @e[tag={tag}]"

        if hasattr(gui, 'change_block_cmd_text') and gui.change_block_cmd_text.winfo_exists():
            gui.change_block_cmd_text.delete("1.0", tk.END)
            gui.change_block_cmd_text.insert("1.0", command)
        else:
            logging.warning("change_block_cmd_text not found or not initialized")

        pyperclip.copy(command.encode('utf-8').decode('utf-8'))
        logging.debug("Kill command copied to clipboard.")
        logging.debug(f"Generated Kill Block Display Command: {command}")
        return command
    except Exception as e:
        logging.error(f"Error generating kill block display command: {e}")
        if hasattr(gui, 'change_block_cmd_text') and gui.change_block_cmd_text.winfo_exists():
            gui.change_block_cmd_text.delete("1.0", tk.END)
            gui.change_block_cmd_text.insert("1.0", "Error: Failed to generate kill command.")
        return ""

def process_command(gui):
    return modify_clipboard_command(gui)