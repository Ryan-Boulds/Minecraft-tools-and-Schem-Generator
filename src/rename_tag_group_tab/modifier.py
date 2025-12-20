import logging
import re
import tkinter as tk
import pyperclip

def process_command(gui, command):
    logging.debug(f"Processing command in Rename Tag/Group tab: {command}")
    try:
        # Get new tag from GUI, default to "beam1" if empty
        new_tag = gui.tag_text.get().strip() if gui.tag_text.get().strip() else "beam1"
        modified_command = command

        # Normalize command by adding leading '/' if missing
        if not command.startswith('/'):
            modified_command = '/' + command.strip()

        # Check if command is empty or just '/'
        if not modified_command.strip() or modified_command == '/':
            logging.warning("No command provided to rename tag")
            if hasattr(gui, 'rename_tag_cmd_text') and gui.rename_tag_cmd_text.winfo_exists():
                gui.rename_tag_cmd_text.delete("1.0", tk.END)
                gui.rename_tag_cmd_text.insert("1.0", "Error: No command provided to rename tag.")
            return command

        # Extract original tag for logging
        original_tag = None
        if 'Tags:' in modified_command:
            match = re.search(r'Tags:\s*\["([^"]*)"\]', modified_command, flags=re.DOTALL)
            if match:
                original_tag = match.group(1)
        elif 'tag=' in modified_command:
            match = re.search(r'tag=([^,\s\]]+)', modified_command, flags=re.DOTALL)
            if match:
                original_tag = match.group(1)

        # Handle /summon commands with Tags
        if 'Tags:' in modified_command:
            modified_command = re.sub(
                r'Tags:\s*\["([^"]*)"\]',
                f'Tags:["{new_tag}"]',
                modified_command,
                flags=re.DOTALL
            )
            logging.debug(f"Modified Tags in summon command: {modified_command}")
        # Handle /execute, /tp, or /kill commands with tag=
        elif 'tag=' in modified_command:
            modified_command = re.sub(
                r'tag=([^,\s\]]+)',
                f'tag={new_tag}',
                modified_command,
                flags=re.DOTALL
            )
            logging.debug(f"Modified tag in execute/tp/kill command: {modified_command}")
        else:
            logging.warning("No tag found in command")
            if hasattr(gui, 'rename_tag_cmd_text') and gui.rename_tag_cmd_text.winfo_exists():
                gui.rename_tag_cmd_text.delete("1.0", tk.END)
                gui.rename_tag_cmd_text.insert("1.0", "Warning: No tag found in command.")
            return command

        # Update the GUI text widget with only the modified command
        if hasattr(gui, 'rename_tag_cmd_text') and gui.rename_tag_cmd_text.winfo_exists():
            gui.rename_tag_cmd_text.delete("1.0", tk.END)
            gui.rename_tag_cmd_text.insert("1.0", modified_command)
        else:
            logging.warning("rename_tag_cmd_text not found or not initialized")

        # Copy modified command to clipboard
        pyperclip.copy(modified_command.encode('utf-8').decode('utf-8'))
        logging.debug("Command copied to clipboard.")

        # Log original and new tags for debugging
        if original_tag:
            logging.debug(f"Original Tag: {original_tag}")
            logging.debug(f"New Tag: {new_tag}")
        logging.debug(f"Modified Command: {modified_command}")

        return modified_command
    except Exception as e:
        logging.error(f"Error processing rename tag command: {e}")
        if hasattr(gui, 'rename_tag_cmd_text') and gui.rename_tag_cmd_text.winfo_exists():
            gui.rename_tag_cmd_text.delete("1.0", tk.END)
            gui.rename_tag_cmd_text.insert("1.0", f"Error: {e}")
        return command