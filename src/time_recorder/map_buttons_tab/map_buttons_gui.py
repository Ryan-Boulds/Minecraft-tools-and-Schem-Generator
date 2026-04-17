# ==================== time_recorder/map_buttons_tab/map_buttons_gui.py ====================
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard as pynput_keyboard
import threading

def create_map_buttons_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # === TOP TOOLBAR ===
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=(0, 10))

    ttk.Button(toolbar, text="💾 Save Project", command=app.save_project).pack(side="left", padx=5)
    ttk.Button(toolbar, text="📂 Load Project", command=app.load_project).pack(side="left", padx=5)

    ttk.Label(toolbar, text="Mapped Commands", font=("Helvetica", 12, "bold")).pack(side="left", padx=20)

    # === ACTIVATE / DEACTIVATE BUTTON (Top Right) ===
    activate_btn = ttk.Button(toolbar, text="Activate", style="Green.TButton")
    activate_btn.pack(side="right", padx=10)

    style = ttk.Style()
    style.configure("Green.TButton", foreground="green", font=("Helvetica", 10, "bold"))
    style.configure("Red.TButton", foreground="red", font=("Helvetica", 10, "bold"))

    is_activated = [False]
    listener = [None]
    currently_pressed = set()   # Prevents spamming on hold

    status_label = ttk.Label(frame, text="Keybinds INACTIVE", 
                           font=("Helvetica", 10), foreground="gray")
    status_label.pack(pady=(0, 10))

    def on_press(key):
        """Called when a key is pressed (including repeats, but we filter them)"""
        try:
            key_name = key.char if key.char else str(key).replace("Key.", "")
        except:
            key_name = str(key).replace("Key.", "")

        if key_name in currently_pressed:
            return  # Already handling this hold → prevent spam

        currently_pressed.add(key_name)

        # Find matching mapping
        for mapping in app.mapped_commands:
            if mapping.get("key") and mapping.get("key").lower() == key_name.lower():
                mtype = mapping.get("type", "single")

                if mtype == "hold":
                    cmd = mapping.get("down_command")
                    if cmd:
                        app._trigger_minecraft_command(cmd)
                else:
                    # Single command on press
                    cmd = mapping.get("command")
                    if cmd:
                        app._trigger_minecraft_command(cmd)
                break

    def on_release(key):
        """Called when a key is released"""
        try:
            key_name = key.char if key.char else str(key).replace("Key.", "")
        except:
            key_name = str(key).replace("Key.", "")

        if key_name in currently_pressed:
            currently_pressed.remove(key_name)

        # Check for hold "up" command
        for mapping in app.mapped_commands:
            if mapping.get("key") and mapping.get("key").lower() == key_name.lower():
                if mapping.get("type") == "hold":
                    cmd = mapping.get("up_command")
                    if cmd:
                        app._trigger_minecraft_command(cmd)
                break

    def toggle_activation():
        if not is_activated[0]:
            # === ACTIVATE ===
            if not app.mapped_commands:
                messagebox.showwarning("No Mappings", "Please add at least one mapped command first!")
                return

            # Stop any old listener
            if listener[0]:
                try:
                    listener[0].stop()
                except:
                    pass

            # Start fresh pynput listener
            listener[0] = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
            listener[0].start()

            currently_pressed.clear()
            is_activated[0] = True
            activate_btn.config(text="Deactivate", style="Red.TButton")
            status_label.config(
                text="✅ Keybinds ACTIVE — Use mapped keys in Minecraft",
                foreground="green"
            )

        else:
            # === DEACTIVATE ===
            if listener[0]:
                try:
                    listener[0].stop()
                except:
                    pass
                listener[0] = None

            currently_pressed.clear()
            is_activated[0] = False
            activate_btn.config(text="Activate", style="Green.TButton")
            status_label.config(text="Keybinds INACTIVE", foreground="gray")

    activate_btn.config(command=toggle_activation)

    # === Mapping rows (unchanged from your original) ===
    rows_frame = ttk.Frame(frame)
    rows_frame.pack(fill="both", expand=True)

    def rebuild_rows():
        for widget in rows_frame.winfo_children():
            widget.destroy()

        for i, mapping in enumerate(app.mapped_commands):
            row = ttk.Frame(rows_frame)
            row.pack(fill="x", pady=4)

            mtype = mapping.get("type", "single")
            ttk.Label(row, text=f"#{i+1} [{mtype.upper()}]:").pack(side="left")

            if mtype == "hold":
                ttk.Label(row, text="DN:").pack(side="left", padx=(10, 2))
                dn_ent = ttk.Entry(row, width=30)
                dn_ent.insert(0, mapping.get("down_command", ""))
                dn_ent.bind("<KeyRelease>", lambda e, idx=i, ent=dn_ent: _update_data(idx, "down_command", ent.get()))
                dn_ent.pack(side="left", fill="x", expand=True)

                ttk.Label(row, text="UP:").pack(side="left", padx=(10, 2))
                up_ent = ttk.Entry(row, width=30)
                up_ent.insert(0, mapping.get("up_command", ""))
                up_ent.bind("<KeyRelease>", lambda e, idx=i, ent=up_ent: _update_data(idx, "up_command", ent.get()))
                up_ent.pack(side="left", fill="x", expand=True)
            else:
                cmd_ent = ttk.Entry(row, width=50)
                cmd_ent.insert(0, mapping.get("command", ""))
                cmd_ent.bind("<KeyRelease>", lambda e, idx=i, ent=cmd_ent: _update_data(idx, "command", ent.get()))
                cmd_ent.pack(side="left", padx=5, fill="x", expand=True)

            key_text = mapping.get("key") or "[None]"
            ttk.Label(row, text=key_text, width=12, relief="sunken", anchor="center").pack(side="left", padx=5)

            ttk.Button(row, text="Map", width=5, command=lambda idx=i: app._show_listening_popup(idx)).pack(side="left")
            ttk.Button(row, text="X", width=3, command=lambda idx=i: [app.mapped_commands.pop(idx), rebuild_rows()]).pack(side="left", padx=2)

    def _update_data(idx, field, text):
        if 0 <= idx < len(app.mapped_commands):
            app.mapped_commands[idx][field] = text

    def add_cmd(mtype):
        if mtype == "single":
            app.mapped_commands.append({"type": "single", "command": "", "key": None})
        else:
            app.mapped_commands.append({"type": "hold", "down_command": "", "up_command": "", "key": None})
        rebuild_rows()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=10)
    ttk.Button(btn_frame, text="+ Add Single", command=lambda: add_cmd("single")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="+ Add Hold", command=lambda: add_cmd("hold")).pack(side="left", padx=5)

    app._refresh_map_buttons = rebuild_rows
    rebuild_rows()

    # Start in inactive state
    toggle_activation()