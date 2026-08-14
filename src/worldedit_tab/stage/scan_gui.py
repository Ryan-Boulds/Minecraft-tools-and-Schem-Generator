# worldedit_tab/stage/scan_gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..common.schem_io import load_schematic
from ..common.recent_paths import get_dir, remember
from .scan_converter import scan_screen_shape, build_screen_object, save_screen_object

PREVIEW_CELL = 8  # pixels per grid cell in the coverage preview
PREVIEW_MAX_CELLS = 80  # cap the preview's own cell size so huge scans don't blow up the canvas


def create_scan_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)

    state = {"schem_data": None, "schem_path": None, "screen_obj": None}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Scan Screens", font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame, text="Scans a .schem of a screen panel you already built and captured with WorldEdit --\n"
                          "records the world position of its front surface, pixel by pixel. Works the same for a\n"
                          "flat wall or a curved/stepped one; there's no flatness assumption anywhere in this.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

    schem_frame = tk.Frame(frame, bg='#f0f0f0')
    schem_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(schem_frame, text="Panel .schem file:", bg='#f0f0f0').pack(side="left")
    schem_path_var = tk.StringVar(value="")
    tk.Entry(schem_frame, textvariable=schem_path_var, width=50, state="readonly").pack(side="left", padx=4)

    def do_browse():
        path = filedialog.askopenfilename(title="Choose a panel schematic",
                                           filetypes=[("Schematic", "*.schem"), ("All files", "*.*")],
                                           initialdir=get_dir("schem_scan_input"))
        if not path:
            return
        loaded, dbg = load_schematic(path)
        if not dbg["success"] or loaded is None:
            messagebox.showerror("Couldn't load", f"Failed to load that schematic: {dbg.get('error')}")
            return
        state["schem_data"] = loaded
        state["schem_path"] = path
        remember("schem_scan_input", path)
        schem_path_var.set(path)
        w, h, l = int(loaded["Width"]), int(loaded["Height"]), int(loaded["Length"])
        status_var.set(f"Loaded: {w} x {h} x {l} (Width x Height x Length). Choose facing and scan.")

    tk.Button(schem_frame, text="Browse", command=do_browse, bg='#2196F3', fg='white').pack(side="left", padx=4)

    facing_frame = tk.Frame(frame, bg='#f0f0f0')
    facing_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(facing_frame, text="Panel facing (which way the front points):", bg='#f0f0f0').pack(side="left")
    facing_var = tk.StringVar(value="south")
    ttk.Combobox(facing_frame, textvariable=facing_var, values=["north", "south", "east", "west"],
                 width=8, state="readonly").pack(side="left", padx=4)
    scan_dir_var = tk.StringVar(value="min")
    tk.Radiobutton(facing_frame, text="Front = low coordinate side", variable=scan_dir_var, value="min",
                   bg='#f0f0f0').pack(side="left", padx=(16, 4))
    tk.Radiobutton(facing_frame, text="Front = high coordinate side", variable=scan_dir_var, value="max",
                   bg='#f0f0f0').pack(side="left", padx=4)

    tk.Label(frame, text="Not sure which side is front? Scan either way and check the preview below -- a\n"
                          "correct scan fills in cleanly; a backward one usually looks broken or empty.",
             bg='#f0f0f0', fg='#777777', justify="left").grid(row=4, column=0, sticky="w", padx=20)

    anchor_frame = tk.Frame(frame, bg='#f0f0f0')
    anchor_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=4)
    tk.Label(anchor_frame, text="World anchor -- where local (0,0,0) of this schematic actually sits right now (X Y Z):",
             bg='#f0f0f0').pack(side="left")
    anchor_x_var, anchor_y_var, anchor_z_var = tk.StringVar(value=""), tk.StringVar(value=""), tk.StringVar(value="")
    tk.Entry(anchor_frame, textvariable=anchor_x_var, width=6).pack(side="left", padx=(4, 2))
    tk.Entry(anchor_frame, textvariable=anchor_y_var, width=6).pack(side="left", padx=2)
    tk.Entry(anchor_frame, textvariable=anchor_z_var, width=6).pack(side="left", padx=2)

    tk.Label(frame, text="This is the ALREADY-BUILT panel's real position -- not where you'll stand to paste\n"
                          "anything. If you captured this with //copy, that's usually wherever you stood when\n"
                          "you ran //copy; if from //schematic save of a region, it's that region's minimum corner.",
             bg='#f0f0f0', fg='#777777', justify="left").grid(row=6, column=0, sticky="w", padx=20)

    name_frame = tk.Frame(frame, bg='#f0f0f0')
    name_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(10, 4))
    tk.Label(name_frame, text="Screen name:", bg='#f0f0f0').pack(side="left")
    name_var = tk.StringVar(value="")
    tk.Entry(name_frame, textvariable=name_var, width=24).pack(side="left", padx=4)

    status_var = tk.StringVar(value="Load a panel .schem file to begin.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333', justify="left").grid(
        row=8, column=0, sticky="w", padx=20, pady=(4, 4))

    preview_canvas = tk.Canvas(frame, bg='#dddddd', width=400, height=200, highlightthickness=1,
                                highlightbackground='#999999')
    preview_canvas.grid(row=9, column=0, sticky="w", padx=20, pady=(0, 8))

    def draw_preview(width, height, screen_obj_pixels):
        preview_canvas.delete("all")
        cell = min(PREVIEW_CELL, max(1, PREVIEW_MAX_CELLS // max(width, height, 1)))
        preview_canvas.config(width=width * cell + 2, height=height * cell + 2)
        for row_i, row in enumerate(screen_obj_pixels):
            for col_i, cell_val in enumerate(row):
                x0, y0 = col_i * cell, row_i * cell
                color = '#4CAF50' if cell_val is not None else '#bbbbbb'
                preview_canvas.create_rectangle(x0, y0, x0 + cell, y0 + cell, fill=color, outline='')

    def do_scan():
        if state["schem_data"] is None:
            messagebox.showwarning("No schematic", "Load a panel .schem file first.")
            return
        try:
            ax = int(anchor_x_var.get())
            ay = int(anchor_y_var.get())
            az = int(anchor_z_var.get())
        except ValueError:
            messagebox.showwarning("Invalid anchor", "World anchor X, Y, Z must be whole numbers.")
            return
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("No name", "Give this screen a name first.")
            return

        try:
            w, h, shape = scan_screen_shape(state["schem_data"], facing_var.get(),
                                             scan_from_min=(scan_dir_var.get() == "min"))
            screen_obj = build_screen_object(name, w, h, shape, world_anchor=(ax, ay, az))
        except ValueError as e:
            messagebox.showwarning("Scan failed", str(e))
            return

        state["screen_obj"] = screen_obj
        covered = sum(1 for row in shape for cell in row if cell is not None)
        total = w * h
        status_var.set(f"Scanned '{name}': {w} x {h} ({covered} of {total} pixels found a block; "
                        f"{total - covered} empty). Check the preview below, then save.")
        draw_preview(w, h, screen_obj["pixels"])

    def do_save():
        if state["screen_obj"] is None:
            messagebox.showwarning("Nothing to save", "Scan a panel first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Screen object", "*.json")],
                                             title="Save screen object",
                                             initialfile=f"{state['screen_obj']['name']}.json",
                                             initialdir=get_dir("stage_screens"))
        if not path:
            return
        try:
            save_screen_object(state["screen_obj"], path)
            remember("stage_screens", path)
            status_var.set(f"Saved: {path}")
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Screen object saved to {path}", "normal")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=10, column=0, sticky="ew", padx=20, pady=(0, 10))
    tk.Button(btn_frame, text="Scan", command=do_scan, bg='#673AB7', fg='white', width=16).pack(side="left", padx=(0, 8))
    tk.Button(btn_frame, text="Save Screen Object", command=do_save, bg='#4CAF50', fg='white', width=20).pack(side="left")

    return frame
