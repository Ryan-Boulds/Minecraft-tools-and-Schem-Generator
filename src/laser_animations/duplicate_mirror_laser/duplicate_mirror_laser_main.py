import tkinter as tk
from tkinter import ttk
import logging


def create_duplicate_mirror_gui(parent_frame, app):
    """
    Builds the 'Duplicate/Mirror' sub-tab under Laser Animations.

    This is a placeholder layout so the tab is wired up and runnable -
    replace the contents with the real duplicate/mirror controls.
    """
    parent_frame.columnconfigure(0, weight=1)

    title_label = tk.Label(
        parent_frame,
        text="Duplicate/Mirror",
        font=("Segoe UI", 16, "bold"),
        fg="#2e7d32",
    )
    title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

    placeholder_label = tk.Label(
        parent_frame,
        text="Duplicate/mirror controls go here.",
        font=("Segoe UI", 10),
    )
    placeholder_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)


def process_command(app, command):
    """
    Placeholder command processor for the 'Duplicate/Mirror' sub-tab.

    Wired into CommandModifierGUI.process_command() in main.py so
    clipboard-triggered processing on this tab doesn't error out.
    Replace with real duplicate/mirror command generation.
    """
    logging.debug("Duplicate/Mirror tab: process_command called (not yet implemented)")