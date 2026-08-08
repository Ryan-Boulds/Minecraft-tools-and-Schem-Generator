# worldedit_tab/resource_pack_scanner/gui.py

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from .scanner import scan_folder, scan_specific_files, collect_png_paths, save_palette, load_palette, find_texture_sources
from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args
from .review_window import open_review_window


def create_resource_pack_scanner_subframe(parent, gui):
    frame = tk.Frame(parent, bg='#f0f0f0')
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(6, weight=1)

    state = {"palette": {}, "sources": {}, "scanning": False}

    header = tk.Frame(frame, bg='#f0f0f0')
    header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(8, 12))
    tk.Label(header, text="Resource Pack Color Scanner",
             font=("Arial", 14, "bold"), bg='#f0f0f0').pack(side="left", padx=20)

    tk.Label(frame,
             text="Two ways to build a palette:\n"
                  "\u2022 Scan Folder \u2014 point at a whole resource pack (or its textures/block folder) for a\n"
                  "  broad, all-vanilla-blocks palette.\n"
                  "\u2022 Add Custom Folder / Add Individual File(s) below \u2014 point at a small folder you've\n"
                  "  curated yourself (e.g. just the colored concretes, retextured however you like) for a\n"
                  "  limited palette.\n"
                  "Both are always filtered to real, full-cube, non-gravity blocks (no sand/gravel/concrete\n"
                  "powder -- those fall). Emissive/glow-map variants (_e, _emissive, _glow, an \"emissive\"\n"
                  "subfolder) are always skipped too.",
             bg='#f0f0f0', fg='#555555', justify="left").grid(row=1, column=0, columnspan=3, sticky="w", padx=12)

    # Folder selection (main, replaces the palette)
    top_frame = tk.Frame(frame, bg='#f0f0f0')
    top_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=6)

    tk.Label(top_frame, text="Texture Folder:", bg='#f0f0f0').pack(side="left")
    folder_var = tk.StringVar()
    tk.Entry(top_frame, textvariable=folder_var, width=60).pack(side="left", padx=8)
    tk.Button(top_frame, text="Browse", command=lambda: _browse_folder(folder_var),
              bg='#2196F3', fg='white').pack(side="left")

    # Color matching mode
    mode_frame = tk.Frame(frame, bg='#f0f0f0')
    mode_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
    tk.Label(mode_frame, text="Color matching:", bg='#f0f0f0').pack(side="left")
    color_mode_var = tk.StringVar(value="dominant")
    tk.Radiobutton(mode_frame, text="Most common color (recommended)", variable=color_mode_var,
                   value="dominant", bg='#f0f0f0').pack(side="left", padx=(6, 12))
    tk.Radiobutton(mode_frame, text="Average of all pixels", variable=color_mode_var,
                   value="average", bg='#f0f0f0').pack(side="left")

    # Custom / curated additions -- merge into the current palette instead
    # of replacing it. Same full-cube + blacklist filtering as the main scan.
    custom_frame = tk.Frame(frame, bg='#f0f0f0')
    custom_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 6))
    tk.Label(custom_frame, text="Add custom / curated textures (merges into the palette above):",
             bg='#f0f0f0', fg='#555555').pack(side="left")

    # Progress / status
    status_var = tk.StringVar(value="No scan yet.")
    tk.Label(frame, textvariable=status_var, bg='#f0f0f0', fg='#333333').grid(
        row=5, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 0))

    # Output list
    text_list = tk.Text(frame, height=18, font=("Consolas", 10), wrap="word", bg="#fdfdfd")
    text_list.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=8)

    def _refresh_preview():
        palette = state["palette"]
        text_list.delete("1.0", "end")
        preview_lines = [f"{name}: rgb{tuple(rgb)}" for name, rgb in list(palette.items())[:200]]
        text_list.insert("end", "\n".join(preview_lines))
        if len(palette) > 200:
            text_list.insert("end", f"\n... and {len(palette) - 200} more.")

    def start_scan():
        folder = folder_var.get().strip()
        if not folder:
            messagebox.showwarning("No folder selected", "Choose a texture folder first.")
            return
        if state["scanning"]:
            return

        state["scanning"] = True
        text_list.delete("1.0", "end")
        status_var.set("Scanning...")

        color_mode = color_mode_var.get()  # read on the main thread -- Tkinter Variables aren't safe from a worker thread

        # Tkinter widgets (including .after()) aren't safe to touch from a
        # background thread -- the worker only ever pushes plain data into
        # this queue; only the main thread (via the self-rescheduling
        # _poll() below) touches any widget.
        result_queue = queue.Queue()

        def progress(i, total, name):
            if i % 25 == 0 or i == total:
                result_queue.put(("progress", i, total, name))

        def worker():
            try:
                palette, stats, sources = scan_folder(folder, progress_callback=progress,
                                                        color_mode=color_mode)
            except Exception as e:
                result_queue.put(("error", str(e)))
                return
            result_queue.put(("done", palette, stats, sources))

        def _on_error(msg):
            state["scanning"] = False
            status_var.set("Scan failed.")
            text_list.insert("end", f"Error scanning folder: {msg}\n")

        def _on_scan_done(palette, stats, sources):
            state["scanning"] = False
            state["palette"] = palette  # replaces -- this is the "start fresh from a pack" action
            state["sources"] = sources
            status_var.set(
                f"Done ({color_mode} color). {stats['scanned']} block colors kept, "
                f"{stats['not_a_block']} skipped (not a valid full-cube block), "
                f"{stats['emissive_skipped']} skipped (emissive/glow textures), "
                f"{stats['skipped']} skipped (transparent/unreadable), "
                f"{stats['total_found']} .png files found."
            )
            _refresh_preview()
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Resource pack scan complete: {len(palette)} colors.", "normal")

        def _poll():
            try:
                while True:
                    item = result_queue.get_nowait()
                    if item[0] == "progress":
                        _, i, total, name = item
                        status_var.set(f"Scanning {i}/{total}: {name}")
                    elif item[0] == "done":
                        _, palette, stats, sources = item
                        _on_scan_done(palette, stats, sources)
                        return
                    elif item[0] == "error":
                        _on_error(item[1])
                        return
            except queue.Empty:
                pass
            if state["scanning"]:
                frame.after(100, _poll)

        threading.Thread(target=worker, daemon=True).start()
        frame.after(100, _poll)

    def _add_paths(paths, source_label):
        if not paths:
            return
        if state["scanning"]:
            return
        state["scanning"] = True
        status_var.set(f"Adding {len(paths)} texture(s) from {source_label}...")

        color_mode = color_mode_var.get()  # read on the main thread -- Tkinter Variables aren't safe from a worker thread
        result_queue = queue.Queue()

        def progress(i, total, name):
            if i % 10 == 0 or i == total:
                result_queue.put(("progress", i, total, name))

        def worker():
            try:
                palette, stats, sources = scan_specific_files(
                    paths, progress_callback=progress, color_mode=color_mode,
                )
            except Exception as e:
                result_queue.put(("error", str(e)))
                return
            result_queue.put(("done", palette, stats, sources))

        def _on_error(msg):
            state["scanning"] = False
            status_var.set("Add failed.")
            messagebox.showerror("Add failed", msg)

        def _on_add_done(palette, stats, sources, label):
            state["scanning"] = False
            added = len(palette)
            state["palette"].update(palette)  # merge, don't replace
            state["sources"].update(sources)
            status_var.set(
                f"Added {added} block color(s) from {label} "
                f"({stats['not_a_block']} rejected -- not a real full-cube block, or barrier/light/"
                f"command/gravity blocks, which are always blocked; {stats['emissive_skipped']} "
                f"emissive/glow textures skipped; {stats['skipped']} unreadable/transparent). "
                f"Palette now has {len(state['palette'])} total."
            )
            _refresh_preview()
            if gui is not None and hasattr(gui, "print_to_text"):
                gui.print_to_text(f"Added {added} custom texture color(s) from {label}.", "normal")

        def _poll():
            try:
                while True:
                    item = result_queue.get_nowait()
                    if item[0] == "progress":
                        _, i, total, name = item
                        status_var.set(f"Adding {i}/{total}: {name}")
                    elif item[0] == "done":
                        _, palette, stats, sources = item
                        _on_add_done(palette, stats, sources, source_label)
                        return
                    elif item[0] == "error":
                        _on_error(item[1])
                        return
            except queue.Empty:
                pass
            if state["scanning"]:
                frame.after(100, _poll)

        threading.Thread(target=worker, daemon=True).start()
        frame.after(100, _poll)

    def add_custom_folder():
        path = filedialog.askdirectory(title="Select a folder of curated textures",
                                        initialdir=get_dir("texture_folder"))
        if not path:
            return
        remember("texture_folder", path)
        paths = collect_png_paths(path)
        if not paths:
            messagebox.showinfo("No textures found", "That folder has no .png files.")
            return
        _add_paths(paths, f"folder '{os.path.basename(path) or path}'")

    def add_individual_files():
        paths = filedialog.askopenfilenames(
            title="Select one or more texture files",
            initialdir=get_dir("texture_folder"),
            filetypes=[("PNG textures", "*.png"), ("All files", "*.*")]
        )
        if not paths:
            return
        remember("texture_folder", paths[0])
        _add_paths(list(paths), f"{len(paths)} selected file(s)")

    def save_current():
        if not state["palette"]:
            messagebox.showwarning("Nothing to save", "Run a scan or add some textures first.")
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Block color palette", "*.json")],
            title="Save block color palette",
            **get_initial_file_args("palette_json"),
        )
        if not out_path:
            return
        try:
            save_palette(state["palette"], out_path)
            remember_file("palette_json", out_path)
            status_var.set(f"Palette saved to {out_path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def load_existing():
        in_path = filedialog.askopenfilename(
            filetypes=[("Block color palette", "*.json")],
            title="Load block color palette",
            **get_initial_file_args("palette_json"),
        )
        if not in_path:
            return
        try:
            palette = load_palette(in_path)
            state["palette"] = palette
            state["sources"] = {}  # unknown -- loaded from JSON, not a live scan
            remember_file("palette_json", in_path)
            _refresh_preview()
            status_var.set(f"Loaded {len(palette)} colors from {in_path}")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))

    def review_palette():
        if not state["palette"]:
            messagebox.showinfo("Nothing to review", "Run a scan or add some textures first.")
            return
        open_review_window(frame, state, status_var, _refresh_preview, on_top_of=frame.winfo_toplevel())

    def locate_textures_for_preview():
        if not state["palette"]:
            messagebox.showinfo("Nothing loaded", "Load or scan a palette first.")
            return
        path = filedialog.askdirectory(title="Select a resource pack folder (to find texture previews)",
                                        initialdir=get_dir("texture_folder"))
        if not path:
            return
        remember("texture_folder", path)
        found = find_texture_sources(state["palette"].keys(), path)
        state["sources"].update(found)
        status_var.set(f"Found textures for {len(found)} of {len(state['palette'])} palette "
                        f"entries in {path} -- Review / Edit Palette will show them now.")

    # Buttons
    btn_frame = tk.Frame(frame, bg='#f0f0f0')
    btn_frame.grid(row=7, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))

    tk.Button(btn_frame, text="Scan Folder (replaces palette)", command=start_scan,
              bg='#4CAF50', fg='white', width=26).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Review / Edit Palette...", command=review_palette,
              bg='#3F51B5', fg='white', width=22).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Save Palette JSON", command=save_current,
              bg='#FF9800', fg='white', width=20).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Load Existing Palette", command=load_existing,
              bg='#607D8B', fg='white', width=22).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Locate Textures for Previews...", command=locate_textures_for_preview,
              bg='#795548', fg='white', width=26).pack(side="left", padx=6)

    custom_btn_frame = tk.Frame(frame, bg='#f0f0f0')
    custom_btn_frame.grid(row=8, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

    tk.Button(custom_btn_frame, text="Add Custom Folder...", command=add_custom_folder,
              bg='#009688', fg='white', width=22).pack(side="left", padx=6)
    tk.Button(custom_btn_frame, text="Add Individual File(s)...", command=add_individual_files,
              bg='#009688', fg='white', width=24).pack(side="left", padx=6)

    return frame


def _browse_folder(var: tk.StringVar):
    path = filedialog.askdirectory(title="Select resource pack texture folder",
                                    initialdir=get_dir("texture_folder"))
    if path:
        var.set(path)
        remember("texture_folder", path)
