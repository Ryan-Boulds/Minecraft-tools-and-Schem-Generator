# src/clipboard_parser/clipboard_parser.py
import re
import logging
import pyperclip

class ClipboardCoordinateParser:
    def __init__(self, gui):
        self.gui = gui

    def parse_coordinates(self, content):
        summon_match = re.match(
            r'/summon (?:minecraft:block_display|minecraft:end_crystal)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)',
            content,
            flags=re.DOTALL
        )
        if summon_match:
            return [summon_match.group(1), summon_match.group(2), summon_match.group(3)]

        raw_match = re.match(
            r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)',
            content,
            flags=re.DOTALL
        )
        if raw_match:
            return [raw_match.group(1), raw_match.group(2), raw_match.group(3)]

        logging.debug(f"Failed to parse coordinates from content: {content}")
        return None

    def autofill_coordinates(self, vars_list):
        try:
            content = pyperclip.paste().strip()
            coords = self.parse_coordinates(content)
            if coords:
                for var, coord in zip(vars_list, coords):
                    var.set(coord)
                logging.debug(f"Autofilled coordinates: {coords}")
                self.gui.print_to_text(f"Autofilled coordinates from clipboard: {coords}", "coord")
            else:
                logging.warning("No valid coordinates found in clipboard")
                self.gui.print_to_text("Error: No valid coordinates found in clipboard.", "normal")
        except Exception as e:
            logging.error(f"Error autofilling coordinates: {e}")
            self.gui.print_to_text(f"Error: Invalid clipboard format. Use '/summon minecraft:block_display 0.0 0.0 0.0' or 'X Y Z' format.", "normal")

    def autofill_integer_coordinates(self, vars_list):
        try:
            content = pyperclip.paste().strip()
            coords = self.parse_coordinates(content)
            if coords:
                for var, coord in zip(vars_list, coords):
                    var.set(str(int(float(coord))))
                logging.debug(f"Autofilled integer coordinates: {[str(int(float(coord))) for coord in coords]}")
                self.gui.print_to_text(f"Autofilled integer coordinates from clipboard: {[str(int(float(coord))) for coord in coords]}", "coord")
            else:
                logging.warning("No valid coordinates found in clipboard")
                self.gui.print_to_text("Error: No valid coordinates found in clipboard.", "normal")
        except Exception as e:
            logging.error(f"Error autofilling integer coordinates: {e}")
            self.gui.print_to_text(f"Error: Invalid clipboard format. Use '/summon minecraft:block_display 0.0 0.0 0.0' or 'X Y Z' format.", "normal")

    def autofill_fractional_coordinates(self, vars_list):
        try:
            content = pyperclip.paste().strip()
            coords = self.parse_coordinates(content)
            if coords:
                for var, coord in zip(vars_list, coords):
                    value = float(coord)
                    fractional = value - int(value)
                    var.set(str(fractional) if fractional != 0 else "0")
                logging.debug(f"Autofilled fractional coordinates: {[str(float(coord) - int(float(coord))) for coord in coords]}")
                self.gui.print_to_text(f"Autofilled fractional coordinates from clipboard: {[str(float(coord) - int(float(coord))) for coord in coords]}", "coord")
            else:
                logging.warning("No valid coordinates found in clipboard")
                self.gui.print_to_text("Error: No valid coordinates found in clipboard.", "normal")
        except Exception as e:
            logging.error(f"Error autofilling fractional coordinates: {e}")
            self.gui.print_to_text(f"Error: Invalid clipboard format. Use '/summon minecraft:block_display 0.0 0.0 0.0' or 'X Y Z' format.", "normal")