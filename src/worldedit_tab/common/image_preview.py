# worldedit_tab/common/image_preview.py
"""
Shared photo preview widget: shows the currently loaded image stretched
to whatever target width:height ratio the tab's current settings imply,
scaled to fit a small display box, so you can see squish/stretch effects
before committing to a conversion. This is a quick smooth-resize sanity
check, not a preview of the eventual blocky output -- no attempt is made
to look pixelated or match the real block palette. Includes a rotate
button (90 degree steps) since a source photo's correct orientation for
a build isn't always how it was shot or how the file's EXIF tag left it.
"""

import tkinter as tk
from PIL import Image, ImageTk

PREVIEW_MAX = 240


def create_preview_widget(parent, on_rotate, bg="#f0f0f0"):
    """on_rotate: called with no args when the Rotate button is clicked.
    The caller owns rotation state -- rotate its own image, then call the
    returned refresh() with the newly-rotated image to redraw.

    Returns (container_frame, refresh_fn). refresh_fn(pil_image,
    target_w, target_h): redraw showing `pil_image` stretched to the
    target_w:target_h ratio (ints or floats, only their ratio matters),
    scaled to fit the preview box. Pass pil_image=None to clear it.
    """
    container = tk.Frame(parent, bg=bg)

    canvas = tk.Canvas(container, width=PREVIEW_MAX, height=PREVIEW_MAX, bg="#dddddd",
                        highlightthickness=1, highlightbackground="#999999")
    canvas.pack(side="top")

    info_var = tk.StringVar(value="No image loaded.")
    tk.Label(container, textvariable=info_var, bg=bg, fg="#555555").pack(side="top", pady=(4, 0))

    tk.Button(container, text="Rotate 90\u00b0 \u21bb", command=on_rotate,
              bg="#607D8B", fg="white").pack(side="top", pady=4)

    photo_ref = {"img": None}  # keep a reference alive so Tk doesn't GC it

    def refresh(pil_image, target_w, target_h):
        canvas.delete("all")
        if pil_image is None or not target_w or not target_h:
            info_var.set("No image loaded.")
            photo_ref["img"] = None
            return

        ratio = target_w / target_h
        if ratio >= 1:
            disp_w = PREVIEW_MAX
            disp_h = max(1, round(PREVIEW_MAX / ratio))
        else:
            disp_h = PREVIEW_MAX
            disp_w = max(1, round(PREVIEW_MAX * ratio))

        preview_img = pil_image.convert("RGB").resize((disp_w, disp_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(preview_img)
        photo_ref["img"] = photo

        x = (PREVIEW_MAX - disp_w) // 2
        y = (PREVIEW_MAX - disp_h) // 2
        canvas.create_image(x, y, anchor="nw", image=photo)
        info_var.set(f"Preview at target ratio {target_w} x {target_h}")

    return container, refresh
