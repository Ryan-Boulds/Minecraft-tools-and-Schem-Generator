# worldedit_tab/common/image_preview.py
"""
Shared photo preview widget, with two modes:

  * "Stretched" (the original behavior) -- shows the currently loaded
    image smoothly resized to whatever target width:height ratio the
    tab's current settings imply, so you can see squish/stretch effects
    live as you edit. Not a preview of the eventual blocky output.

  * "2D Render" -- shows the ACTUAL matched palette colors, one flat
    color per pixel cell, exactly what the real conversion would place.
    This is NOT computed automatically (matching every pixel against the
    palette is real work for a big image) -- it's built on demand via
    the "Load 2D Preview" button, using whatever palette/size/rotation
    the tab currently has set. Supports mouse-wheel zoom and click-drag
    pan, since seeing individual pixel colors clearly usually means
    zooming in past the small preview box's native size.

Includes a rotate button (90 degree steps) since a source photo's
correct orientation for a build isn't always how it was shot or how the
file's EXIF tag left it.
"""

import tkinter as tk
from PIL import Image, ImageTk

PREVIEW_MAX = 240
ZOOM_MIN, ZOOM_MAX = 1.0, 32.0
ZOOM_STEP = 1.25
UNMATCHED_FILL = (40, 40, 40)  # dark neutral fill for transparent/unmatched cells in the 2D render


def create_preview_widget(parent, on_rotate, on_load_palette_preview, bg="#f0f0f0"):
    """on_rotate: called with no args when the Rotate button is clicked.
    The caller owns rotation state -- rotate its own image, then call the
    returned refresh_stretched() (and, if a 2D render was already loaded,
    re-trigger on_load_palette_preview() too) to redraw.

    on_load_palette_preview: called with no args when "Load 2D Preview"
    is clicked. The caller should compute a block_grid (e.g. via
    build_pixel_grid + match_palette) against whatever palette/size/
    rotation it currently has, then call the returned set_palette_grid()
    with the result.

    Returns (container_frame, refresh_stretched, set_palette_grid).

    refresh_stretched(pil_image, target_w, target_h): redraw the
      "Stretched" mode (only actually visible if that mode is selected)
      showing `pil_image` stretched to the target_w:target_h ratio,
      scaled to fit the preview box. Pass pil_image=None to clear it.

    set_palette_grid(block_grid, palette): redraw the "2D Render" mode
      (and switch to it) using block_grid (row-major list of block-id-
      or-None, e.g. from match_palette) and palette ({block_id:
      [r,g,b]}) -- one flat-colored cell per pixel, using the palette's
      OWN stored color, not the original photo's.
    """
    container = tk.Frame(parent, bg=bg)

    mode_var = tk.StringVar(value="stretched")
    mode_row = tk.Frame(container, bg=bg)
    mode_row.pack(side="top", fill="x")
    tk.Radiobutton(mode_row, text="Stretched", variable=mode_var, value="stretched",
                   bg=bg, command=lambda: _switch_mode()).pack(side="left", padx=(0, 8))
    tk.Radiobutton(mode_row, text="2D Render", variable=mode_var, value="palette",
                   bg=bg, command=lambda: _switch_mode()).pack(side="left")

    canvas = tk.Canvas(container, width=PREVIEW_MAX, height=PREVIEW_MAX, bg="#dddddd",
                        highlightthickness=1, highlightbackground="#999999")
    canvas.pack(side="top", pady=(4, 0))

    info_var = tk.StringVar(value="No image loaded.")
    tk.Label(container, textvariable=info_var, bg=bg, fg="#555555",
             wraplength=PREVIEW_MAX, justify="left").pack(side="top", pady=(4, 0))

    btn_row = tk.Frame(container, bg=bg)
    btn_row.pack(side="top", pady=4)
    tk.Button(btn_row, text="Load 2D Preview", command=lambda: on_load_palette_preview(),
              bg="#3F51B5", fg="white").pack(side="left", padx=(0, 6))
    tk.Button(btn_row, text="Rotate 90\u00b0 \u21bb", command=on_rotate,
              bg="#607D8B", fg="white").pack(side="left")

    state = {
        "mode": "stretched",
        "stretched_image": None, "stretched_w": None, "stretched_h": None,
        "palette_image": None,  # small PIL image, 1 px per cell, built from the palette's own colors
        "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0,
        "photo_ref": None,  # keep a reference alive so Tk doesn't GC it
        "drag_start": None,
    }

    def _switch_mode():
        state["mode"] = mode_var.get()
        state["zoom"] = 1.0
        state["pan_x"] = 0.0
        state["pan_y"] = 0.0
        _render()

    def _render():
        canvas.delete("all")

        if state["mode"] == "stretched":
            img = state["stretched_image"]
            tw, th = state["stretched_w"], state["stretched_h"]
            if img is None or not tw or not th:
                info_var.set("No image loaded.")
                state["photo_ref"] = None
                return
            ratio = tw / th
            if ratio >= 1:
                disp_w = PREVIEW_MAX
                disp_h = max(1, round(PREVIEW_MAX / ratio))
            else:
                disp_h = PREVIEW_MAX
                disp_w = max(1, round(PREVIEW_MAX * ratio))
            preview_img = img.convert("RGB").resize((disp_w, disp_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(preview_img)
            state["photo_ref"] = photo
            x = (PREVIEW_MAX - disp_w) // 2
            y = (PREVIEW_MAX - disp_h) // 2
            canvas.create_image(x, y, anchor="nw", image=photo)
            info_var.set(f"Stretched preview at target ratio {tw} x {th}")
            return

        # "palette" mode
        img = state["palette_image"]
        if img is None:
            info_var.set('Click "Load 2D Preview" to render this using the loaded palette\'s colors.')
            state["photo_ref"] = None
            return

        base_w, base_h = img.size
        zoom = state["zoom"]
        disp_w = max(1, round(base_w * zoom))
        disp_h = max(1, round(base_h * zoom))
        zoomed = img.resize((disp_w, disp_h), Image.NEAREST)  # hard pixel edges, not smoothed

        max_pan_x = max(0, disp_w - PREVIEW_MAX)
        max_pan_y = max(0, disp_h - PREVIEW_MAX)
        state["pan_x"] = min(max(state["pan_x"], 0), max_pan_x)
        state["pan_y"] = min(max(state["pan_y"], 0), max_pan_y)

        left = int(state["pan_x"])
        top = int(state["pan_y"])
        right = min(disp_w, left + PREVIEW_MAX)
        bottom = min(disp_h, top + PREVIEW_MAX)
        view = zoomed.crop((left, top, right, bottom))

        photo = ImageTk.PhotoImage(view)
        state["photo_ref"] = photo
        x = max(0, (PREVIEW_MAX - view.size[0]) // 2)
        y = max(0, (PREVIEW_MAX - view.size[1]) // 2)
        canvas.create_image(x, y, anchor="nw", image=photo)
        info_var.set(f"2D render, {base_w} x {base_h} blocks, zoom {zoom:.1f}x -- "
                      f"scroll to zoom, drag to pan")

    def refresh_stretched(pil_image, target_w, target_h):
        state["stretched_image"] = pil_image
        state["stretched_w"] = target_w
        state["stretched_h"] = target_h
        if state["mode"] == "stretched":
            _render()

    def set_palette_grid(block_grid, palette):
        h = len(block_grid)
        w = len(block_grid[0]) if h else 0
        if w == 0 or h == 0:
            state["palette_image"] = None
            _render()
            return
        img = Image.new("RGB", (w, h), UNMATCHED_FILL)
        pixels = img.load()
        for y, row in enumerate(block_grid):
            for x, block in enumerate(row):
                if block is not None and block in palette:
                    r, g, b = palette[block]
                    pixels[x, y] = (r, g, b)
        state["palette_image"] = img
        # start at a zoom level that roughly fills the preview box, so a
        # small grid isn't shown tiny at 1x
        state["zoom"] = min(ZOOM_MAX, max(1.0, PREVIEW_MAX / max(w, h)))
        state["pan_x"] = 0.0
        state["pan_y"] = 0.0
        mode_var.set("palette")
        state["mode"] = "palette"
        _render()

    def _on_wheel(event):
        if state["mode"] != "palette" or state["palette_image"] is None:
            return
        old_zoom = state["zoom"]
        factor = ZOOM_STEP if event.delta > 0 else (1 / ZOOM_STEP)
        new_zoom = min(ZOOM_MAX, max(ZOOM_MIN, old_zoom * factor))
        if new_zoom == old_zoom:
            return
        # keep the same image point roughly centered while zooming
        state["pan_x"] = state["pan_x"] * (new_zoom / old_zoom)
        state["pan_y"] = state["pan_y"] * (new_zoom / old_zoom)
        state["zoom"] = new_zoom
        _render()

    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def _on_drag_start(event):
        state["drag_start"] = (event.x, event.y, state["pan_x"], state["pan_y"])

    def _on_drag_move(event):
        if state["mode"] != "palette" or state["drag_start"] is None:
            return
        sx, sy, start_pan_x, start_pan_y = state["drag_start"]
        state["pan_x"] = start_pan_x - (event.x - sx)
        state["pan_y"] = start_pan_y - (event.y - sy)
        _render()

    def _on_drag_end(_event):
        state["drag_start"] = None

    canvas.bind("<ButtonPress-1>", _on_drag_start)
    canvas.bind("<B1-Motion>", _on_drag_move)
    canvas.bind("<ButtonRelease-1>", _on_drag_end)

    return container, refresh_stretched, set_palette_grid
