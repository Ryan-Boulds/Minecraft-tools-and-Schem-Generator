from tkinter import ttk

from laser_animations.generate_laser_tab.generate_laser_gui import create_generate_laser_gui
from laser_animations.animator_tab.animator_tab_main import create_animator_gui
from laser_animations.duplicate_mirror_laser.duplicate_mirror_laser_main import create_duplicate_mirror_gui


def create_laser_animations_gui(parent_frame, app):
    """
    Builds the 'Laser Animations' main tab, containing its own sub-notebook
    with: Generate Laser, Animate, Duplicate/Mirror.

    Mirrors how create_modify_laser_gui() etc. are wired into the
    Command Generation sub-notebook in main.py.
    """
    app.laser_animations_notebook = ttk.Notebook(parent_frame)
    app.laser_animations_notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(0, weight=1)

    app.generate_laser_frame = ttk.Frame(app.laser_animations_notebook)
    app.animate_laser_frame = ttk.Frame(app.laser_animations_notebook)
    app.duplicate_mirror_laser_frame = ttk.Frame(app.laser_animations_notebook)

    app.laser_animations_notebook.add(app.generate_laser_frame, text="Generate Laser")
    app.laser_animations_notebook.add(app.animate_laser_frame, text="Animate")
    app.laser_animations_notebook.add(app.duplicate_mirror_laser_frame, text="Duplicate/Mirror")

    create_generate_laser_gui(app.generate_laser_frame, app)
    create_animator_gui(app.animate_laser_frame, app)
    create_duplicate_mirror_gui(app.duplicate_mirror_laser_frame, app)