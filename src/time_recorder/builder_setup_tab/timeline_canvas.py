# ==================== time_recorder/builder_setup_tab/timeline_canvas.py ====================
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

def create_timeline_canvas(parent_frame, app):
    container = ttk.Frame(parent_frame)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, height=520, bg="#f8f8f8", highlightthickness=0)
    hbar = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
    vbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

    canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
    
    hbar.pack(side="bottom", fill="x")
    vbar.pack(side="right", fill="y")
    canvas.pack(side="top", fill="both", expand=True)

    # State variables
    PIXELS_PER_SECOND = [80.0]
    TRACK_HEIGHT = 72
    AUDIO_HEIGHT = 90          # Fixed height for audio section
    RULER_HEIGHT = 45
    LEFT_GUTTER = 50
    
    selected_clip = [None]
    drag_start_x = [0]
    drag_start_offset = [0.0]
    playhead_seconds = [0.0] 
    is_dragging_playhead = [False]
    last_offset_before_drag = [0.0]

    def pps(): return PIXELS_PER_SECOND[0]

    def draw_timeline():
        current_scroll_x = canvas.xview()
        current_scroll_y = canvas.yview()
        canvas.delete("all")

        if not app.sequences and app.audio_waveform is None:
            canvas.create_text(450, 200, text="No sequences or audio loaded.", fill="gray")
            return

        # Calculate total dimensions
        times = [s["offset"] + (s["sequence"][-1][1] if s["sequence"] else 2) for s in app.sequences]
        if app.audio_waveform is not None:
            times.append(app.audio_duration)
        max_time = max(times) if times else 10

        total_width = max(1000, LEFT_GUTTER + 200 + max_time * pps())
        command_area_height = len(app.sequences) * TRACK_HEIGHT + 80
        total_height = RULER_HEIGHT + AUDIO_HEIGHT + command_area_height + 30

        canvas.config(scrollregion=(0, 0, total_width, total_height))

        # ==================== AUDIO SECTION (Fixed Top) ====================
        audio_y_base = RULER_HEIGHT

        # Ruler (shared, drawn once above audio)
        canvas.create_line(LEFT_GUTTER, RULER_HEIGHT-5, LEFT_GUTTER + max_time * pps(), RULER_HEIGHT-5, fill="black", width=2)
        for sec in range(0, int(max_time) + 5):
            x = LEFT_GUTTER + sec * pps()
            canvas.create_line(x, RULER_HEIGHT-20, x, RULER_HEIGHT-5, fill="black")
            canvas.create_text(x, RULER_HEIGHT-30, text=f"{sec}s", font=("Arial", 8))

        # Audio waveform box
        if app.audio_waveform is not None:
            canvas.create_rectangle(LEFT_GUTTER-5, audio_y_base, 
                                  LEFT_GUTTER + max_time * pps() + 5, audio_y_base + AUDIO_HEIGHT,
                                  fill="#f0f0f0", outline="#555", width=2)
            
            audio_center_y = audio_y_base + AUDIO_HEIGHT // 2
            samples = len(app.audio_waveform)
            pixels_total = app.audio_duration * pps()
            step = max(1, int(samples / pixels_total))
            
            for i in range(0, samples, step):
                x = LEFT_GUTTER + (i / samples) * pixels_total
                amplitude = app.audio_waveform[i] * (AUDIO_HEIGHT * 0.45)
                canvas.create_line(x, audio_center_y - amplitude, 
                                   x, audio_center_y + amplitude, 
                                   fill="#3498db", width=1, tags="waveform")
            
            canvas.create_text(LEFT_GUTTER - 8, audio_center_y, text="AUDIO", 
                             anchor="e", font=("Arial", 9, "bold"), fill="#2c3e50")

        # ==================== COMMAND TIMELINES (Scrollable) ====================
        command_y_start = audio_y_base + AUDIO_HEIGHT + 25

        for i, seq in enumerate(app.sequences):
            y = command_y_start + i * TRACK_HEIGHT
            canvas.create_text(LEFT_GUTTER - 8, y + 25, text=seq["name"][:15], 
                             anchor="e", font=("Arial", 8, "bold"))

            start_x = LEFT_GUTTER + seq["offset"] * pps()
            duration = seq["sequence"][-1][1] if seq["sequence"] else 1
            width = max(duration * pps(), 60)
            
            clip_color = "#4a90e2" if selected_clip[0] != seq.get('id') else "#357abd"
            tag = f"clip_{seq['id']}"
            
            canvas.create_rectangle(start_x, y, start_x + width, y + 50, 
                                     fill=clip_color, outline="#2171b5", tags=tag, width=2)
            
            # Command dots
            for _, delay in seq["sequence"]:
                dot_x = start_x + delay * pps()
                canvas.create_oval(dot_x-3, y+22, dot_x+3, y+28, fill="red", outline="white", tags=tag)

        # Draw playhead across full height
        update_playhead(playhead_seconds[0])
        
        # Restore scroll
        canvas.xview_moveto(current_scroll_x[0])
        canvas.yview_moveto(current_scroll_y[0])

    def update_playhead(seconds):
        playhead_seconds[0] = seconds
        canvas.delete("playhead")
        
        # Safety check - only try to auto-scroll if scrollregion is properly set
        scrollregion = canvas.cget("scrollregion")
        if scrollregion and scrollregion.strip():
            try:
                scroll_region_width = float(scrollregion.split()[2])
                
                px = LEFT_GUTTER + (seconds * pps())
                
                # Auto-scroll horizontally
                x_left = canvas.canvasx(0)
                x_right = x_left + canvas.winfo_width()
                
                if px > x_right and canvas.winfo_width() > 1 and scroll_region_width > 0:
                    canvas.xview_moveto(px / scroll_region_width)
                elif seconds == 0:
                    canvas.xview_moveto(0)
            except (IndexError, ValueError):
                pass  # Canvas not ready yet - skip auto-scroll

        # Draw the playhead (full height red line + triangle)
        px = LEFT_GUTTER + (seconds * pps())
        canvas.create_line(px, 0, px, 2000, fill="#ff0000", width=2, tags="playhead")
        canvas.create_polygon(px-8, 0, px+8, 0, px+8, 12, px, 20, px-8, 12, 
                            fill="#ff0000", tags="playhead")

    # Click handling (clip priority first)
    def on_click(event):
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        
        # Check for clip first
        for item in canvas.find_overlapping(cx-5, cy-5, cx+5, cy+5):
            for tag in canvas.gettags(item):
                if tag.startswith("clip_"):
                    sid = int(tag.split("_")[1])
                    selected_clip[0] = sid
                    seq = next(s for s in app.sequences if s["id"] == sid)
                    drag_start_x[0], drag_start_offset[0] = cx, float(seq["offset"])
                    last_offset_before_drag[0] = float(seq["offset"])
                    draw_timeline()
                    return

        # Then check playhead
        playhead_x = LEFT_GUTTER + (playhead_seconds[0] * pps())
        if abs(cx - playhead_x) <= 12:
            selected_clip[0] = None
            is_dragging_playhead[0] = True
            return

        selected_clip[0] = None
        draw_timeline()

    def on_drag(event):
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)

        if is_dragging_playhead[0]:
            new_sec = max(0.0, (cx - LEFT_GUTTER) / pps())
            update_playhead(new_sec)
            return

        if selected_clip[0] is None:
            return

        seq = next(s for s in app.sequences if s["id"] == selected_clip[0])
        new_off = max(0.0, drag_start_offset[0] + (cx - drag_start_x[0]) / pps())
        seq["offset"] = round(new_off, 3)

        # Live vertical reordering of command tracks only
        current_idx = next((idx for idx, s in enumerate(app.sequences) if s["id"] == selected_clip[0]), None)
        if current_idx is not None:
            command_y_start = RULER_HEIGHT + AUDIO_HEIGHT + 25
            relative_y = cy - command_y_start
            target_idx = max(0, min(len(app.sequences)-1, int(relative_y // TRACK_HEIGHT)))
            if target_idx != current_idx:
                seq_to_move = app.sequences.pop(current_idx)
                app.sequences.insert(target_idx, seq_to_move)

        draw_timeline()

    def on_release(event):
        if is_dragging_playhead[0]:
            is_dragging_playhead[0] = False
        elif selected_clip[0] is not None:
            seq = next((s for s in app.sequences if s["id"] == selected_clip[0]), None)
            if seq and abs(seq.get("offset", 0) - last_offset_before_drag[0]) > 0.001:
                app._push_undo(f"Move '{seq['name']}'")
        selected_clip[0] = None
        draw_timeline()

    def handle_mousewheel(event):
        if event.state & 0x4:  # Ctrl = Zoom
            old_pps = pps()
            factor = 1.1 if event.delta > 0 else 0.9
            PIXELS_PER_SECOND[0] = max(10, min(1000, old_pps * factor))
            draw_timeline()
            return

        if event.state & 0x1:  # Shift = Horizontal
            scroll_amount = -1 if event.delta > 0 else 1
            canvas.xview_scroll(scroll_amount * 4, "units")
            return

        # Default = Vertical scroll (affects command tracks only)
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Right-click menu
    context_menu = tk.Menu(canvas, tearoff=0)
    
    def handle_right_click(event):
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        target_sid = None
        for item in canvas.find_overlapping(cx-5, cy-5, cx+5, cy+5):
            for tag in canvas.gettags(item):
                if tag.startswith("clip_"):
                    target_sid = int(tag.split("_")[1])
                    break
        
        if target_sid is not None:
            context_menu.delete(0, tk.END)
            context_menu.add_command(label="Rename", command=lambda: rename_seq(target_sid))
            context_menu.add_command(label="Duplicate", command=lambda: duplicate_seq(target_sid))
            context_menu.add_separator()
            context_menu.add_command(label="✂ Split at Playhead", 
                                   command=lambda sid=target_sid: split_at_playhead(sid))
            context_menu.add_separator()
            context_menu.add_command(label="Delete", command=lambda: delete_seq(target_sid), foreground="red")
            context_menu.post(event.x_root, event.y_root)

    def rename_seq(sid):
        seq = next(s for s in app.sequences if s["id"] == sid)
        name = simpledialog.askstring("Rename", "New name:", initialvalue=seq["name"])
        if name and name != seq["name"]:
            app._push_undo(f"Rename '{seq['name']}' → '{name}'")
            seq["name"] = name
            draw_timeline()

    def duplicate_seq(sid):
        original = next(s for s in app.sequences if s["id"] == sid)
        new_data = [cmd[:] for cmd in original["sequence"]]
        app.add_sequence(name=f"{original['name']} (Copy)", sequence=new_data, offset=original["offset"])

    def delete_seq(sid):
        app.delete_sequence(sid)

    def split_at_playhead(sid):
        app.split_sequence(sid, playhead_seconds[0])

    # Bindings
    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<MouseWheel>", handle_mousewheel)
    canvas.bind("<Button-3>", handle_right_click)

    app._refresh_builder = draw_timeline
    app._update_playhead = update_playhead
    
    draw_timeline()