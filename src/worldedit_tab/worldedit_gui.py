# worldedit_tab/worldedit_gui.py
import tkinter as tk
from tkinter import ttk

from .convert_to_command_blocks.gui import create_converter_subframe
from .resource_pack_scanner.gui import create_resource_pack_scanner_subframe
from .image_to_pixelart.gui import create_image_to_pixelart_subframe
from .gif_placeholder.gui import create_gif_placeholder_subframe
from .video_placeholder.gui import create_video_placeholder_subframe


def create_worldedit_schematic_gui(frame, gui):
    """WorldEdit Schematic Tab - now a Notebook with multiple subtabs:
       Conv to cmd blocks, Resource Pack Scanner, Image to Pixel Art,
       GIF (placeholder), Video (placeholder)."""
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    notebook = ttk.Notebook(frame)
    notebook.grid(row=0, column=0, sticky="nsew")

    tabs = [
        ("Conv to cmd blocks", _scrollable(notebook, lambda parent: create_converter_subframe(parent, gui))),
        ("Resource Pack Scanner", _scrollable(notebook, lambda parent: create_resource_pack_scanner_subframe(parent, gui))),
        ("Image to Pixel Art", _scrollable(notebook, lambda parent: create_image_to_pixelart_subframe(parent, gui))),
        ("GIF (soon)", _scrollable(notebook, lambda parent: create_gif_placeholder_subframe(parent, gui))),
        ("Video (soon)", _scrollable(notebook, lambda parent: create_video_placeholder_subframe(parent, gui))),
    ]

    for label, tab_frame in tabs:
        notebook.add(tab_frame, text=label)


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
