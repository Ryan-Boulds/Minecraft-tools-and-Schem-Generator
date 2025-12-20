# modify_laser_tab/modifier.py
# Fully updated & working: November 30, 2025

import re
import logging
import tkinter as tk
import pyperclip


def process_command(gui, command):
    """
    Main entry point — called from your main app when F12 or clipboard is processed.
    Now supports the new Modify Laser tab with input box, direction toggle, move-to, etc.
    """
    try:
        # If we're in the Modify Laser tab and there's an input box, use that instead
        if hasattr(gui, 'modify_input_text') and gui.modify_input_text.winfo_exists():
            raw_command = gui.modify_input_text.get("1.0", tk.END).strip()
            if raw_command:
                command = raw_command
                logging.debug("Using command from Modify Laser input box")
            else:
                gui.print_to_text("Error: Input box is empty.", "normal")
                return command

        if not command.startswith('/'):
            command = '/' + command

        # Extract original coordinates
        coord_match = re.match(
            r'/summon\s+minecraft:block_display\s+(-?[\d\.]+)\s+(-?[\d\.]+)\s+(-?[\d\.]+)',
            command, re.IGNORECASE
        )
        if not coord_match:
            gui.print_to_text("Error: No valid block_display coordinates found.", "normal")
            return command

        base_x, base_y, base_z = map(float, coord_match.groups())
        final_x = base_x
        final_y = base_y
        final_z = base_z

        # === Move To X Y Z (optional) ===
        if hasattr(gui, 'modify_move_to') and gui.modify_move_to.get():
            try:
                if gui.modify_x.get().strip():
                    final_x = float(gui.modify_x.get())
                if gui.modify_y.get().strip():
                    final_y = float(gui.modify_y.get())
                if gui.modify_z.get().strip():
                    final_z = float(gui.modify_z.get())
            except ValueError:
                gui.print_to_text("Warning: Invalid Move To coordinates — using original.", "normal")

        # === Direction Adjustment (optional) ===
        direction = getattr(gui, 'modify_laser_direction', tk.StringVar(value="North")).get()
        scale = "[0.1f,0.1f,-150f]"  # default

        if hasattr(gui, 'modify_direction') and gui.modify_direction.get():
            if direction == "North":
                final_x -= 0.08
                final_y += 0.42
                final_z -= 0.01
                scale = "[0.1f,0.1f,-150f]"
            elif direction == "South":
                final_x -= 0.02
                final_y += 0.42
                final_z += 1.01
                scale = "[0.1f,0.1f,150f]"
            elif direction == "East":
                final_y += 0.42
                final_z += 0.42
                scale = "[150f,0.1f,0.1f]"
            elif direction == "West":
                final_x -= 1.0
                final_y += 0.42
                final_z += 0.48
                scale = "[-150f,0.1f,0.1f]"

        # Clean number display
        def clean(n):
            return str(int(n)) if abs(n - int(n)) < 1e-6 else f"{n:.3f}".rstrip("0").rstrip(".")

        x_str = clean(final_x)
        y_str = clean(final_y)
        z_str = clean(final_z)

        # Block & Tag (optional)
        block = ("minecraft:lime_concrete", gui.modify_block_text.get().strip().replace("__", ":"))[gui.modify_block.get() and gui.modify_block_text.get().strip() != ""]
        tag = ("beam1", gui.modify_tag_text.get().strip())[gui.modify_tag.get() and gui.modify_tag_text.get().strip() != ""]

        # Build final command
        new_command = (
            f"/summon minecraft:block_display {x_str} {y_str} {z_str} "
            f"{{block_state:{{Name:\"{block}\"}},"
            f"transformation:{{translation:[0.5f,0.0f,0f],scale:{scale},"
            f"left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}},"
            f"brightness:15728880,shadow:false,billboard:\"fixed\",Tags:[\"{tag}\"]}}"
        )

        # Output to the correct text widget
        output_widget = getattr(gui, 'modify_output_text', None) or getattr(gui, 'cmd_text_set', None)
        if output_widget and output_widget.winfo_exists():
            output_widget.delete("1.0", tk.END)
            output_widget.insert("1.0", new_command)

        pyperclip.copy(new_command)
        gui.print_to_text(f"Modified → {direction} | {x_str} {y_str} {z_str}", "modified_coord")
        gui.print_to_text("Command copied to clipboard!", "normal")

        return new_command

    except Exception as e:
        logging.error(f"Modify Laser error: {e}")
        gui.print_to_text(f"Error: {str(e)}", "normal")
        return command


# Optional: Keep old presets if you still use them elsewhere
def set_laser_preset(gui):
    if hasattr(gui, 'modify_direction'):
        gui.modify_direction.set(True)
    if hasattr(gui, 'modify_laser_direction'):
        gui.modify_laser_direction.set("North")
    if hasattr(gui, 'modify_block'):
        gui.modify_block.set(True)
        gui.modify_block_text.set("minecraft:lime_concrete")
    if hasattr(gui, 'modify_tag'):
        gui.modify_tag.set(True)
        gui.modify_tag_text.set("beam1")
    gui.print_to_text("Applied Laser preset", "normal")


def set_lightbeam_preset(gui):
    if hasattr(gui, 'modify_direction'):
        gui.modify_direction.set(True)
    if hasattr(gui, 'modify_laser_direction'):
        gui.modify_laser_direction.set("North")
    if hasattr(gui, 'modify_block'):
        gui.modify_block.set(True)
        gui.modify_block_text.set("minecraft:light_blue_concrete")
    if hasattr(gui, 'modify_tag'):
        gui.modify_tag.set(True)
        gui.modify_tag_text.set("lightbeam1")
    gui.print_to_text("Applied Lightbeam preset", "normal")