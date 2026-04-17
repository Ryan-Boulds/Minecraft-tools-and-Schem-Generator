# ==================== time_recorder/builder_setup_tab/timeline_canvas.py ====================
import tkinter as tk
from tkinter import ttk

def create_timeline_canvas(parent_frame, app):
    container = ttk.Frame(parent_frame)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, height=480, bg="#f8f8f8", highlightthickness=0)
    hbar = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
    canvas.configure(xscrollcommand=hbar.set)
    
    hbar.pack(side="bottom", fill="x")
    canvas.pack(side="top", fill="both", expand=True)

    PIXELS_PER_SECOND = [80.0]
    TRACK_HEIGHT = 72
    RULER_HEIGHT = 45
    
    selected_clip = [None]
    drag_start_x = [0]
    drag_start_offset = [0.0]
    playhead_seconds = [0.0] 

    def pps(): return PIXELS_PER_SECOND[0]

    def draw_timeline():
        canvas.delete("all")
        if not app.sequences:
            canvas.create_text(450, 200, text="No sequences loaded.", fill="gray")
            return

        times = [s["offset"] + (s["sequence"][-1][1] if s["sequence"] else 2) for s in app.sequences]
        max_time = max(times) if times else 10
        # Ensure scrollregion is large enough for the playhead to return to 0
        canvas.config(scrollregion=(0, 0, max(1000, 200 + max_time * pps()), 480))

        # Draw Ruler
        canvas.create_line(50, RULER_HEIGHT, 50 + max_time * pps(), RULER_HEIGHT, fill="black", width=2)
        for sec in range(0, int(max_time) + 5):
            x = 50 + sec * pps()
            canvas.create_line(x, RULER_HEIGHT-10, x, RULER_HEIGHT, fill="black")
            canvas.create_text(x, RULER_HEIGHT-22, text=f"{sec}s", font=("Arial", 8))

        # Draw Tracks
        for i, seq in enumerate(app.sequences):
            y = RULER_HEIGHT + 25 + i * TRACK_HEIGHT
            canvas.create_text(45, y + 25, text=seq["name"][:12], anchor="e", font=("Arial", 8, "bold"))
            
            start_x = 50 + seq["offset"] * pps()
            duration = seq["sequence"][-1][1] if seq["sequence"] else 1
            width = max(duration * pps(), 60)
            
            tag = f"clip_{seq['id']}"
            canvas.create_rectangle(start_x, y, start_x + width, y + 50, 
                                    fill="#4a90e2", outline="#2171b5", tags=tag)
            for _, delay in seq["sequence"]:
                dot_x = start_x + delay * pps()
                canvas.create_oval(dot_x-3, y+22, dot_x+3, y+28, fill="red", outline="white", tags=tag)

        update_playhead(playhead_seconds[0])

    def update_playhead(seconds):
        playhead_seconds[0] = seconds
        canvas.delete("playhead")
        
        px = 50 + (seconds * pps())
        
        # --- AUTO-SCROLL LOGIC ---
        # Get visible boundaries in pixels
        x_left = canvas.canvasx(0)
        x_right = x_left + canvas.winfo_width()
        
        if px > x_right and canvas.winfo_width() > 1:
            # Move to next page
            canvas.xview_moveto(px / float(canvas.cget("scrollregion").split()[2]))
        elif seconds == 0:
            # Snap back to beginning when reset
            canvas.xview_moveto(0)

        canvas.create_line(px, 0, px, 480, fill="#ff0000", width=2, tags="playhead")
        canvas.create_polygon(px-8, 0, px+8, 0, px+8, 12, px, 20, px-8, 12, fill="#ff0000", tags="playhead")

    def on_click(event):
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        for item in canvas.find_overlapping(cx-2, cy-2, cx+2, cy+2):
            for tag in canvas.gettags(item):
                if tag.startswith("clip_"):
                    sid = int(tag.split("_")[1])
                    selected_clip[0] = sid
                    seq = next(s for s in app.sequences if s["id"] == sid)
                    drag_start_x[0], drag_start_offset[0] = cx, float(seq["offset"])
                    return

    def on_drag(event):
        if selected_clip[0] is None: return
        cx = canvas.canvasx(event.x)
        seq = next(s for s in app.sequences if s["id"] == selected_clip[0])
        new_off = max(0.0, drag_start_offset[0] + (cx - drag_start_x[0]) / pps())
        seq["offset"] = round(new_off, 3)
        draw_timeline()

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", lambda e: [selected_clip.pop(0), selected_clip.append(None), draw_timeline()])
    canvas.bind("<MouseWheel>", lambda e: (
        PIXELS_PER_SECOND.__setitem__(0, max(10, min(1000, pps() * (1.1 if e.delta > 0 else 0.9)))) 
        if e.state & 0x4 else canvas.xview_scroll(int(-1*(e.delta/120)), "units"), draw_timeline()))

    app._refresh_builder = draw_timeline
    app._update_playhead = update_playhead
    draw_timeline()