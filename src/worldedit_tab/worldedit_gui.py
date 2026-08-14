# worldedit_tab/worldedit_gui.py
import tkinter as tk
from tkinter import ttk

from .convert_to_command_blocks.gui import create_converter_subframe
from .resource_pack_scanner.gui import create_resource_pack_scanner_subframe
from .image_to_pixelart.gui import create_image_to_pixelart_subframe
from .image_command_blocks.gui import create_image_command_blocks_subframe
from .gif_command_blocks.gui import create_gif_command_blocks_subframe
from .video_command_blocks.gui import create_video_command_blocks_subframe
from .stage.scan_gui import create_scan_subframe
from .stage.arrange_gui import create_arrange_subframe
from .stage.generate_gui import create_stage_generate_subframe


def create_worldedit_schematic_gui(frame, gui):
    """WorldEdit Schematic Tab - a top-level Notebook with three tabs:
       Media Creator (Image to Pixel Art, Image Command Blocks, GIF
       Command Blocks, Video), Setup Tools (Conv to cmd blocks,
       Resource Pack Scanner), and Stage (Scan Screens, Arrange Stage,
       Generate) -- each holding its own nested Notebook of subtabs."""
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    top_notebook = ttk.Notebook(frame)
    top_notebook.grid(row=0, column=0, sticky="nsew")

    media_frame = ttk.Frame(top_notebook)
    setup_frame = ttk.Frame(top_notebook)
    stage_frame = ttk.Frame(top_notebook)
    top_notebook.add(media_frame, text="Media Creator")
    top_notebook.add(setup_frame, text="Setup Tools")
    top_notebook.add(stage_frame, text="Stage")

    media_notebook = _nested_notebook(media_frame)
    media_tabs = [
        ("Image to Pixel Art", _scrollable(media_notebook, lambda parent: create_image_to_pixelart_subframe(parent, gui))),
        ("Image Command Blocks", _scrollable(media_notebook, lambda parent: create_image_command_blocks_subframe(parent, gui))),
        ("GIF Command Blocks", _scrollable(media_notebook, lambda parent: create_gif_command_blocks_subframe(parent, gui))),
        ("Video", _scrollable(media_notebook, lambda parent: create_video_command_blocks_subframe(parent, gui))),
    ]
    for label, tab_frame in media_tabs:
        media_notebook.add(tab_frame, text=label)

    setup_notebook = _nested_notebook(setup_frame)
    setup_tabs = [
        ("Conv to cmd blocks", _scrollable(setup_notebook, lambda parent: create_converter_subframe(parent, gui))),
        ("Resource Pack Scanner", _scrollable(setup_notebook, lambda parent: create_resource_pack_scanner_subframe(parent, gui))),
    ]
    for label, tab_frame in setup_tabs:
        setup_notebook.add(tab_frame, text=label)

    stage_notebook = _nested_notebook(stage_frame)
    stage_tabs = [
        ("Scan Screens", _scrollable(stage_notebook, lambda parent: create_scan_subframe(parent, gui))),
        ("Arrange Stage", _scrollable(stage_notebook, lambda parent: create_arrange_subframe(parent, gui))),
        ("Generate", _scrollable(stage_notebook, lambda parent: create_stage_generate_subframe(parent, gui))),
    ]
    for label, tab_frame in stage_tabs:
        stage_notebook.add(tab_frame, text=label)


def _nested_notebook(parent):
    """A Notebook that fills its parent frame -- used for the inner
    (Media Creator / Setup Tools) tab groups."""
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)
    notebook = ttk.Notebook(parent)
    notebook.grid(row=0, column=0, sticky="nsew")
    return notebook


def _scrollable(notebook, build_content_fn):
    """Wrap a subtab's content in a scrollable canvas (mirrors the scroll
    behavior the original tab had) and return the outer frame to add to
    the Notebook."""
    outer = ttk.Frame(notebook)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=1)

    canvas = tk.Canvas(outer, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Only scroll this canvas when the mouse is over it, so multiple
    # subtabs don't fight over global mouse-wheel bindings.
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    content = build_content_fn(scrollable_frame)
    content.pack(fill="both", expand=True)

    return outer
