import logging
import pyperclip
import tkinter as tk
import re

def modify_properties_command(gui):
    try:
        clipboard_content = pyperclip.paste().strip()
        command_type = gui.command_type.get()
        block_type = gui.block_text.get().replace("__", ":") or "minecraft:lime_concrete"
        tag = gui.change_block_tag.get() or "beam1"
        
        # Parse input values with defaults
        try:
            x = float(gui.laser_x.get()) if gui.laser_x.get() else 0.0
            y = float(gui.laser_y.get()) if gui.laser_y.get() else 0.0
            z = float(gui.laser_z.get()) if gui.laser_z.get() else 0.0
            scale_x = float(gui.scale_x.get()) if gui.scale_x.get() else 0.1
            scale_y = float(gui.scale_y.get()) if gui.scale_y.get() else 0.1
            scale_z = float(gui.scale_z.get()) if gui.scale_z.get() else -150.0
            target_x = int(float(gui.end_beam_target_x.get())) if gui.end_beam_target_x.get() else 0
            target_y = int(float(gui.end_beam_target_y.get())) if gui.end_beam_target_y.get() else 0
            target_z = int(float(gui.end_beam_target_z.get())) if gui.end_beam_target_z.get() else 0
        except ValueError:
            logging.warning("Invalid coordinate or scale values, using defaults")
            x, y, z = 0.0, 0.0, 0.0
            scale_x, scale_y, scale_z = 0.1, 0.1, -150.0
            target_x, target_y, target_z = 0, 0, 0

        modified_command = clipboard_content
        if command_type == "laser":
            # Regex for /summon minecraft:block_display command
            block_display_pattern = r'^/summon minecraft:block_display\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+\{.*block_state:\{Name:"([\w:]+)"\}.*transformation:\{[^}]*scale:\[(-?\d+\.?\d*f),(-?\d+\.?\d*f),(-?\d+\.?\d*f)\].*Tags:\["([^"]+)"\].*\}$'
            block_display_match = re.match(block_display_pattern, clipboard_content)

            if block_display_match:
                orig_x, orig_y, orig_z, orig_block, orig_scale_x, orig_scale_y, orig_scale_z, orig_tag = block_display_match.groups()
                # Update fields based on checkbox states
                if gui.modify_coords.get():
                    modified_command = re.sub(
                        r'^/summon minecraft:block_display\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)',
                        f'/summon minecraft:block_display {x:.6f} {y:.6f} {z:.6f}',
                        modified_command
                    )
                if gui.modify_block.get():
                    modified_command = re.sub(
                        r'block_state:\{Name:"[\w:]+"\}',
                        f'block_state:{{Name:"{block_type}"}}',
                        modified_command
                    )
                if gui.modify_tag.get():
                    modified_command = re.sub(
                        r'Tags:\["[^"]+"\]',
                        f'Tags:["{tag}"]',
                        modified_command
                    )
                if gui.modify_scale.get():
                    modified_command = re.sub(
                        r'scale:\[-?\d+\.?\d*f,-?\d+\.?\d*f,-?\d+\.?\d*f\]',
                        f'scale:[{scale_x:.1f}f,{scale_y:.1f}f,{scale_z:.1f}f]',
                        modified_command
                    )
                logging.debug(f"Modified block display command: {modified_command}")
            else:
                # Generate new command if clipboard is invalid
                modified_command = (
                    f"/summon minecraft:block_display {x:.6f} {y:.6f} {z:.6f} "
                    f'{{block_state:{{Name:"{block_type}"}},transformation:{{translation:[0.5f,0.0f,0.0f],'
                    f'scale:[{scale_x:.1f}f,{scale_y:.1f}f,{scale_z:.1f}f],left_rotation:[0f,0f,0f,1f],'
                    f'right_rotation:[0f,0f,0f,1f]}},brightness:15728880,shadow:false,billboard:"fixed",Tags:["{tag}"]}}'
                )
                logging.debug(f"Generated new block display command: {modified_command}")

        elif command_type == "end beam":
            # Regex for /summon end_crystal command
            end_crystal_pattern = r'^/summon end_crystal\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+\{.*Tags:\["([^"]+)"\].*BeamTarget:\{X:(-?\d+),Y:(-?\d+),Z:(-?\d+)\}\}'
            end_crystal_match = re.match(end_crystal_pattern, clipboard_content)

            if end_crystal_match:
                orig_x, orig_y, orig_z, orig_tag, orig_target_x, orig_target_y, orig_target_z = end_crystal_match.groups()
                # Update fields based on checkbox states
                if gui.modify_coords.get():
                    modified_command = re.sub(
                        r'^/summon end_crystal\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)',
                        f'/summon end_crystal {x:.6f} {y:.6f} {z:.6f}',
                        modified_command
                    )
                if gui.modify_tag.get():
                    modified_command = re.sub(
                        r'Tags:\["[^"]+"\]',
                        f'Tags:["{tag}"]',
                        modified_command
                    )
                if gui.modify_target_coords.get():
                    modified_command = re.sub(
                        r'BeamTarget:\{X:-?\d+,Y:-?\d+,Z:-?\d+\}',
                        f'BeamTarget:{{X:{target_x:d},Y:{target_y:d},Z:{target_z:d}}}',
                        modified_command
                    )
                logging.debug(f"Modified end crystal command: {modified_command}")
            else:
                # Generate new command if clipboard is invalid
                modified_command = (
                    f"/summon end_crystal {x:.6f} {y:.6f} {z:.6f} "
                    f'{{ShowBottom:0b,Invulnerable:1b,Tags:["{tag}"],BeamTarget:{{X:{target_x:d},Y:{target_y:d},Z:{target_z:d}}}}}'
                )
                logging.debug(f"Generated new end crystal command: {modified_command}")

        else:
            logging.warning("Unsupported command type")
            if hasattr(gui, 'modify_properties_cmd_text') and gui.modify_properties_cmd_text.winfo_exists():
                gui.modify_properties_cmd_text.delete("1.0", tk.END)
                gui.modify_properties_cmd_text.insert("1.0", "Error: Unsupported command type.")
            return ""

        if hasattr(gui, 'modify_properties_cmd_text') and gui.modify_properties_cmd_text.winfo_exists():
            gui.modify_properties_cmd_text.delete("1.0", tk.END)
            gui.modify_properties_cmd_text.insert("1.0", modified_command)
        else:
            logging.warning("modify_properties_cmd_text not found or not initialized")

        pyperclip.copy(modified_command.encode('utf-8').decode('utf-8'))
        logging.debug("Modified command copied to clipboard.")
        return modified_command
    except Exception as e:
        logging.error(f"Error modifying command: {e}")
        if hasattr(gui, 'modify_properties_cmd_text') and gui.modify_properties_cmd_text.winfo_exists():
            gui.modify_properties_cmd_text.delete("1.0", tk.END)
            gui.modify_properties_cmd_text.insert("1.0", f"Error: Failed to parse or modify command. {e}")
        return ""

def generate_kill_block_display_command(gui):
    try:
        tag = gui.change_block_tag.get() or "beam1"
        command = f"/kill @e[tag={tag}]"

        if hasattr(gui, 'modify_properties_cmd_text') and gui.modify_properties_cmd_text.winfo_exists():
            gui.modify_properties_cmd_text.delete("1.0", tk.END)
            gui.modify_properties_cmd_text.insert("1.0", command)
        else:
            logging.warning("modify_properties_cmd_text not found or not initialized")

        pyperclip.copy(command.encode('utf-8').decode('utf-8'))
        logging.debug("Kill command copied to clipboard.")
        logging.debug(f"Generated Kill Command: {command}")
        return command
    except Exception as e:
        logging.error(f"Error generating kill command: {e}")
        if hasattr(gui, 'modify_properties_cmd_text') and gui.modify_properties_cmd_text.winfo_exists():
            gui.modify_properties_cmd_text.delete("1.0", tk.END)
            gui.modify_properties_cmd_text.insert("1.0", "Error: Failed to generate kill command.")
        return ""

def process_command(gui):
    return modify_properties_command(gui)