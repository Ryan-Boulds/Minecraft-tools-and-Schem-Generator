import tkinter as tk
from tkinter import ttk, messagebox

def create_map_buttons_gui(parent, app):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="Mapped Commands", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))

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
                ttk.Label(row, text="Down:").pack(side="left", padx=(10, 2))
                down_entry = ttk.Entry(row, width=35)
                down_entry.insert(0, mapping.get("down_command", ""))
                down_entry.bind("<KeyRelease>", lambda e, idx=i: _update_down(idx, down_entry.get()))
                down_entry.pack(side="left", padx=2, fill="x", expand=True)

                ttk.Label(row, text="Up:").pack(side="left", padx=(10, 2))
                up_entry = ttk.Entry(row, width=35)
                up_entry.insert(0, mapping.get("up_command", ""))
                up_entry.bind("<KeyRelease>", lambda e, idx=i: _update_up(idx, up_entry.get()))
                up_entry.pack(side="left", padx=2, fill="x", expand=True)
            else:
                cmd_entry = ttk.Entry(row, width=50)
                cmd_entry.insert(0, mapping.get("command", ""))
                cmd_entry.bind("<KeyRelease>", lambda e, idx=i: _update_command(idx, cmd_entry.get()))
                cmd_entry.pack(side="left", padx=5, fill="x", expand=True)

            key_label = ttk.Label(row, text=mapping.get("key") or "[Not mapped]", 
                                  width=18, relief="sunken", anchor="center")
            key_label.pack(side="left", padx=8)

            def start_mapping(idx=i):
                app.current_mapping_index = idx
                app._show_listening_popup(idx)

            ttk.Button(row, text="Map Key", command=start_mapping).pack(side="left", padx=5)

    def _update_command(idx, text):
        if 0 <= idx < len(app.mapped_commands):
            app.mapped_commands[idx]["command"] = text

    def _update_down(idx, text):
        if 0 <= idx < len(app.mapped_commands):
            app.mapped_commands[idx]["down_command"] = text

    def _update_up(idx, text):
        if 0 <= idx < len(app.mapped_commands):
            app.mapped_commands[idx]["up_command"] = text

    def add_single_command():
        app.mapped_commands.append({"type": "single", "command": "", "key": None})
        rebuild_rows()

    def add_hold_command():
        app.mapped_commands.append({
            "type": "hold",
            "down_command": "",
            "up_command": "",
            "key": None
        })
        rebuild_rows()

    # Buttons
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=10)
    ttk.Button(btn_frame, text="+ Add Single Command", command=add_single_command).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="+ Add Hold Command", command=add_hold_command).pack(side="left", padx=5)

    # Expose refresh function for main.py
    app._refresh_map_buttons = rebuild_rows

    # Initial example
    if not app.mapped_commands:
        app.mapped_commands.append({"type": "single", "command": "kill @e[type=armor_stand]", "key": None})

    rebuild_rows()