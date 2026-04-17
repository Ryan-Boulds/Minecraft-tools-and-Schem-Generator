# ==================== time_recorder/builder_setup_tab/timeline_canvas.py ====================
import tkinter as tk

def create_timeline_canvas(parent_frame, app):
    canvas = tk.Canvas(parent_frame, height=480, bg="#f8f8f8", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    PIXELS_PER_SECOND = [80.0]
    TRACK_HEIGHT = 70
    RULER_HEIGHT = 40

    selected_clip = [None]
    drag_start_x = [0]
    drag_start_y = [0]
    drag_start_offset = [0.0]
    drag_start_index = [None]

    def pps():
        return PIXELS_PER_SECOND[0]

    def draw_timeline():
        canvas.delete("all")
        if not app.sequences:
            canvas.create_text(450, 200, 
                text="No timelines yet.\nGo to Timeline tab to record or add sequences.",
                fill="gray", font=("Arial", 12), justify="center")
            return

        max_time = max((s["offset"] + (s["sequence"][-1][1] if s["sequence"] else 0) 
                       for s in app.sequences), default=10)

        # Ruler
        canvas.create_line(50, RULER_HEIGHT, 50 + max_time * pps(), RULER_HEIGHT, fill="black", width=2)
        for sec in range(0, int(max_time) + 3):
            x = 50 + sec * pps()
            canvas.create_line(x, RULER_HEIGHT-10, x, RULER_HEIGHT+10, fill="black")
            canvas.create_text(x, RULER_HEIGHT-20, text=str(sec), font=("Arial", 9))

        for i, seq in enumerate(app.sequences):
            y = RULER_HEIGHT + 20 + i * TRACK_HEIGHT

            canvas.create_text(40, y + TRACK_HEIGHT//2, text=seq["name"][:16], 
                               anchor="e", font=("Arial", 10, "bold"))

            canvas.create_line(50, y + TRACK_HEIGHT//2, 50 + max_time * pps(), 
                               y + TRACK_HEIGHT//2, fill="#ddd", dash=(4,2))

            start_x = 50 + seq["offset"] * pps()
            duration = seq["sequence"][-1][1] if seq["sequence"] else 2
            width = max(duration * pps(), 80)

            clip_tag = f"clip_{seq['id']}"
            canvas.create_rectangle(start_x, y+10, start_x+width, y+TRACK_HEIGHT-10,
                                    fill="#4a90e2", outline="#2171b5", width=3, tags=clip_tag)

            # Red dots for every command
            for cmd, delay in seq["sequence"]:
                dot_x = start_x + delay * pps()
                canvas.create_oval(dot_x-4, y+22, dot_x+4, y+42, fill="#e74c3c", outline="white", tags=clip_tag)

            canvas.create_text(start_x + width//2, y + TRACK_HEIGHT//2,
                               text=f"{len(seq['sequence'])} cmds", 
                               fill="white", font=("Arial", 9, "bold"), tags=clip_tag)

    # ====================== DRAG LOGIC ======================
    def on_click(event):
        items = canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            for tag in canvas.gettags(item):
                if tag.startswith("clip_"):
                    seq_id = int(tag.split("_")[1])
                    for idx, s in enumerate(app.sequences):
                        if s["id"] == seq_id:
                            selected_clip[0] = seq_id
                            drag_start_index[0] = idx
                            drag_start_x[0] = event.x
                            drag_start_y[0] = event.y
                            drag_start_offset[0] = float(s["offset"])   # ensure float
                            return

    def on_drag(event):
        if not selected_clip[0]:
            return

        idx = drag_start_index[0]
        delta_x = event.x - drag_start_x[0]
        delta_y = event.y - drag_start_y[0]

        # HORIZONTAL DRAG - Change offset (this is the fix for the top clip)
        if abs(delta_x) > 6:                     # Lower threshold for better responsiveness
            current_offset = drag_start_offset[0]
            new_offset = current_offset + (delta_x / pps())
            new_offset = max(0.0, round(new_offset, 3))   # Never go below 0
            app.update_offset(app.sequences[idx]["id"], new_offset)

            # Update start values so continued dragging feels smooth
            drag_start_x[0] = event.x
            drag_start_offset[0] = new_offset

        # VERTICAL DRAG - Reorder tracks
        elif abs(delta_y) > 25:
            new_index = max(0, min(len(app.sequences)-1, int((event.y - 60) / TRACK_HEIGHT)))
            if new_index != idx:
                app.move_sequence(idx, new_index)
                drag_start_index[0] = new_index

    def on_release(event):
        selected_clip[0] = None
        draw_timeline()

    # ====================== ZOOM ======================
    def on_mouse_wheel(event):
        if event.state & 0x4:   # Ctrl pressed
            if event.delta > 0:
                PIXELS_PER_SECOND[0] = min(400, PIXELS_PER_SECOND[0] * 1.25)
            else:
                PIXELS_PER_SECOND[0] = max(20, PIXELS_PER_SECOND[0] / 1.25)
            draw_timeline()

    # Bindings
    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<MouseWheel>", on_mouse_wheel)

    app._refresh_builder = draw_timeline
    draw_timeline()