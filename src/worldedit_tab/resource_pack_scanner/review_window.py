# worldedit_tab/resource_pack_scanner/review_window.py
"""
Post-scan review window: shows every texture kept by a scan as a big,
scrollable thumbnail list so odd matches (like a glazed terracotta
that scans oddly) can be spotted and removed by eye before saving the
palette. Click a row to select it, Remove/Delete to drop it, Undo to
bring the last removed one back, Save Selections to commit the edits
back into the caller's palette, or Cancel to discard them.
"""

import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

THUMB_SIZE = 96


def open_review_window(parent, state, status_var, refresh_preview, on_top_of=None):
    """parent: any widget to anchor the Toplevel to.
    state: the scanner tab's state dict -- state["palette"] and
      state["sources"] are read to build the list, and overwritten with
      the edited result if the user clicks Save Selections.
    status_var: the scanner tab's status StringVar, updated on save.
    refresh_preview: callback to refresh the scanner tab's text preview
      after a save.
    """
    if not state.get("palette"):
        return

    win = tk.Toplevel(on_top_of or parent)
    win.title("Review Scanned Textures")
    win.geometry("560x720")
    win.transient(on_top_of or parent)

    # Local working copy -- nothing touches state["palette"] until Save.
    sources = state.get("sources", {})
    items = [{"name": name, "rgb": rgb, "path": sources.get(name)}
              for name, rgb in sorted(state["palette"].items())]
    undo_stack = []  # [(item, index), ...]
    selected = {"name": None}
    thumb_cache = {}  # name -> PhotoImage, built once so scrolling/removal is instant
    row_widgets = {}  # name -> row Frame, for highlight/lookup

    # --- top/bottom chrome first, so pack() gives the middle to the canvas ---
    top_bar = tk.Frame(win)
    top_bar.pack(side="top", fill="x")
    count_var = tk.StringVar()
    tk.Label(top_bar, textvariable=count_var, font=("Arial", 10, "bold")).pack(side="left", padx=10, pady=8)
    tk.Label(top_bar, text="Click a texture to select it, then Remove or press Delete. Scroll to see more.",
             fg="#666666").pack(side="left", padx=6)

    bottom_bar = tk.Frame(win)
    bottom_bar.pack(side="bottom", fill="x", pady=8)

    def _count_text():
        return f"{len(items)} texture(s)"

    count_var.set(_count_text())

    # --- scrollable list ---
    list_area = tk.Frame(win)
    list_area.pack(side="top", fill="both", expand=True)

    canvas = tk.Canvas(list_area, highlightthickness=0, bg="#e8e8e8")
    scrollbar = ttk.Scrollbar(list_area, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#e8e8e8")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def get_thumb(item):
        name = item["name"]
        if name in thumb_cache:
            return thumb_cache[name]
        photo = None
        if item["path"] and os.path.isfile(item["path"]):
            try:
                im = Image.open(item["path"]).convert("RGBA")
                w, h = im.size
                if w > 0 and h > w and h % w == 0:
                    im = im.crop((0, 0, w, w))  # first animation frame only
                im = im.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
                photo = ImageTk.PhotoImage(im)
            except Exception:
                photo = None
        if photo is None:
            # Fallback: a plain color swatch from the stored RGB, so a
            # texture loaded from a saved palette JSON (no source path)
            # still shows *something*.
            r, g, b = item["rgb"]
            im = Image.new("RGB", (THUMB_SIZE, THUMB_SIZE), (r, g, b))
            photo = ImageTk.PhotoImage(im)
        thumb_cache[name] = photo
        return photo

    def select_row(name):
        if selected["name"] and selected["name"] in row_widgets:
            row_widgets[selected["name"]].config(bg="#ffffff")
            for child in row_widgets[selected["name"]].winfo_children():
                child.config(bg="#ffffff")
        selected["name"] = name
        if name in row_widgets:
            row_widgets[name].config(bg="#cce5ff")
            for child in row_widgets[name].winfo_children():
                if not isinstance(child, tk.Label) or not getattr(child, "_is_thumb", False):
                    child.config(bg="#cce5ff")

    def rebuild_list():
        for w in scrollable.winfo_children():
            w.destroy()
        row_widgets.clear()

        for item in items:
            name = item["name"]
            row = tk.Frame(scrollable, bg="#ffffff", bd=1, relief="solid")
            row.pack(fill="x", padx=8, pady=4)

            thumb = get_thumb(item)
            thumb_label = tk.Label(row, image=thumb, bg="#ffffff")
            thumb_label._is_thumb = True
            thumb_label.image = thumb  # extra reference, belt-and-suspenders against GC
            thumb_label.pack(side="left", padx=10, pady=10)

            info = tk.Frame(row, bg="#ffffff")
            info.pack(side="left", fill="both", expand=True, padx=8)
            tk.Label(info, text=name, font=("Consolas", 13, "bold"), bg="#ffffff", anchor="w").pack(fill="x", pady=(14, 2))
            tk.Label(info, text=f"rgb{tuple(item['rgb'])}", font=("Consolas", 10), bg="#ffffff",
                     fg="#666666", anchor="w").pack(fill="x")

            for widget in (row, thumb_label, info, *info.winfo_children()):
                widget.bind("<Button-1>", lambda e, n=name: select_row(n))

            row_widgets[name] = row

        count_var.set(_count_text())

    def remove_selected():
        name = selected["name"]
        if not name:
            return
        idx = next((i for i, it in enumerate(items) if it["name"] == name), None)
        if idx is None:
            return
        removed = items.pop(idx)
        undo_stack.append((removed, idx))
        selected["name"] = None
        rebuild_list()

    def undo_remove():
        if not undo_stack:
            return
        removed, idx = undo_stack.pop()
        idx = min(idx, len(items))
        items.insert(idx, removed)
        rebuild_list()

    win.bind("<Delete>", lambda e: remove_selected())
    win.bind("<BackSpace>", lambda e: remove_selected())

    tk.Button(bottom_bar, text="Remove Selected", command=remove_selected,
              bg="#f44336", fg="white", width=16).pack(side="left", padx=(10, 6))
    tk.Button(bottom_bar, text="Undo", command=undo_remove,
              bg="#607D8B", fg="white", width=10).pack(side="left", padx=6)

    def do_save():
        state["palette"] = {it["name"]: it["rgb"] for it in items}
        state["sources"] = {it["name"]: it["path"] for it in items if it["path"]}
        refresh_preview()
        status_var.set(f"Reviewed palette: {len(items)} texture(s) kept.")
        win.destroy()

    def do_cancel():
        win.destroy()

    tk.Button(bottom_bar, text="Cancel", command=do_cancel,
              bg="#9E9E9E", fg="white", width=10).pack(side="right", padx=(6, 10))
    tk.Button(bottom_bar, text="Save Selections", command=do_save,
              bg="#4CAF50", fg="white", width=16).pack(side="right", padx=6)

    rebuild_list()
    win.lift()
    win.focus_force()
