import tkinter as tk
from tkinter import ttk
import logging
from .modifier import modify_properties_command, generate_kill_block_display_command

def create_modify_properties_gui(frame, gui):
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    # Title
    tk.Label(scrollable_frame, text="Modify Properties", font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#333333').grid(row=0, column=0, columnspan=4, pady=5, sticky="w")

    # Command Type Dropdown
    tk.Label(scrollable_frame, text="Command Type:", font=("Arial", 10), bg='#f0f0f0').grid(row=1, column=0, pady=2, sticky="w")
    command_types = ["laser", "end beam"]
    gui.command_type = tk.StringVar(value=command_types[0])
    command_combobox = ttk.Combobox(scrollable_frame, textvariable=gui.command_type, values=command_types, state="readonly", width=15)
    command_combobox.grid(row=1, column=1, pady=2, sticky="w")

    # Block Type (for laser)
    block_label = tk.Label(scrollable_frame, text="Block:", font=("Arial", 10), bg='#f0f0f0')
    block_label.grid(row=2, column=0, pady=2, sticky="w")
    gui.modify_block = tk.BooleanVar(value=True)
    block_check = tk.Checkbutton(scrollable_frame, text="Modify", variable=gui.modify_block, bg='#f0f0f0')
    block_check.grid(row=2, column=2, pady=2, sticky="w")
    block_entry = tk.Entry(scrollable_frame, textvariable=gui.block_text, width=20, bg='#ffffff', font=("Arial", 10))
    block_entry.grid(row=2, column=1, pady=2, sticky="w")

    # Tag
    tk.Label(scrollable_frame, text="Tag:", font=("Arial", 10), bg='#f0f0f0').grid(row=3, column=0, pady=2, sticky="w")
    gui.modify_tag = tk.BooleanVar(value=True)
    tk.Checkbutton(scrollable_frame, text="Modify", variable=gui.modify_tag, bg='#f0f0f0').grid(row=3, column=2, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.change_block_tag, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=3, column=1, pady=2, sticky="w")

    # Position Coordinates
    tk.Label(scrollable_frame, text="Position Coordinates:", font=("Arial", 10, "bold"), bg='#f0f0f0').grid(row=4, column=0, pady=5, sticky="w")
    gui.modify_coords = tk.BooleanVar(value=True)
    tk.Checkbutton(scrollable_frame, text="Modify", variable=gui.modify_coords, bg='#f0f0f0').grid(row=4, column=2, pady=5, sticky="w")
    tk.Label(scrollable_frame, text="X:", font=("Arial", 10), bg='#f0f0f0').grid(row=5, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_x, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=5, column=1, pady=2, sticky="w")
    tk.Label(scrollable_frame, text="Y:", font=("Arial", 10), bg='#f0f0f0').grid(row=6, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_y, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=6, column=1, pady=2, sticky="w")
    tk.Label(scrollable_frame, text="Z:", font=("Arial", 10), bg='#f0f0f0').grid(row=7, column=0, pady=2, sticky="w")
    tk.Entry(scrollable_frame, textvariable=gui.laser_z, width=10, bg='#ffffff', font=("Arial", 10)).grid(row=7, column=1, pady=2, sticky="w")

    # Scale (for laser)
    scale_label = tk.Label(scrollable_frame, text="Scale:", font=("Arial", 10, "bold"), bg='#f0f0f0')
    scale_label.grid(row=8, column=0, pady=5, sticky="w")
    gui.modify_scale = tk.BooleanVar(value=True)
    scale_check = tk.Checkbutton(scrollable_frame, text="Modify", variable=gui.modify_scale, bg='#f0f0f0')
    scale_check.grid(row=8, column=2, pady=5, sticky="w")
    scale_x_label = tk.Label(scrollable_frame, text="X Scale:", font=("Arial", 10), bg='#f0f0f0')
    scale_x_label.grid(row=9, column=0, pady=2, sticky="w")
    scale_x_entry = tk.Entry(scrollable_frame, textvariable=gui.scale_x, width=10, bg='#ffffff', font=("Arial", 10))
    scale_x_entry.grid(row=9, column=1, pady=2, sticky="w")
    scale_y_label = tk.Label(scrollable_frame, text="Y Scale:", font=("Arial", 10), bg='#f0f0f0')
    scale_y_label.grid(row=10, column=0, pady=2, sticky="w")
    scale_y_entry = tk.Entry(scrollable_frame, textvariable=gui.scale_y, width=10, bg='#ffffff', font=("Arial", 10))
    scale_y_entry.grid(row=10, column=1, pady=2, sticky="w")
    scale_z_label = tk.Label(scrollable_frame, text="Z Scale:", font=("Arial", 10), bg='#f0f0f0')
    scale_z_label.grid(row=11, column=0, pady=2, sticky="w")
    scale_z_entry = tk.Entry(scrollable_frame, textvariable=gui.scale_z, width=10, bg='#ffffff', font=("Arial", 10))
    scale_z_entry.grid(row=11, column=1, pady=2, sticky="w")

    # Target Coordinates (for end beam)
    target_label = tk.Label(scrollable_frame, text="Target Coordinates:", font=("Arial", 10, "bold"), bg='#f0f0f0')
    target_label.grid(row=12, column=0, pady=5, sticky="w")
    gui.modify_target_coords = tk.BooleanVar(value=True)
    target_check = tk.Checkbutton(scrollable_frame, text="Modify", variable=gui.modify_target_coords, bg='#f0f0f0')
    target_check.grid(row=12, column=2, pady=5, sticky="w")
    target_x_label = tk.Label(scrollable_frame, text="Target X:", font=("Arial", 10), bg='#f0f0f0')
    target_x_label.grid(row=13, column=0, pady=2, sticky="w")
    target_x_entry = tk.Entry(scrollable_frame, textvariable=gui.end_beam_target_x, width=10, bg='#ffffff', font=("Arial", 10))
    target_x_entry.grid(row=13, column=1, pady=2, sticky="w")
    target_y_label = tk.Label(scrollable_frame, text="Target Y:", font=("Arial", 10), bg='#f0f0f0')
    target_y_label.grid(row=14, column=0, pady=2, sticky="w")
    target_y_entry = tk.Entry(scrollable_frame, textvariable=gui.end_beam_target_y, width=10, bg='#ffffff', font=("Arial", 10))
    target_y_entry.grid(row=14, column=1, pady=2, sticky="w")
    target_z_label = tk.Label(scrollable_frame, text="Target Z:", font=("Arial", 10), bg='#f0f0f0')
    target_z_label.grid(row=15, column=0, pady=2, sticky="w")
    target_z_entry = tk.Entry(scrollable_frame, textvariable=gui.end_beam_target_z, width=10, bg='#ffffff', font=("Arial", 10))
    target_z_entry.grid(row=15, column=1, pady=2, sticky="w")

    # Buttons
    tk.Button(scrollable_frame, text="Copy from Clipboard", command=gui.modify_clipboard_command, font=("Arial", 10), bg='#2196F3', fg='#ffffff').grid(row=16, column=0, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Modify Command", command=gui.modify_properties_command, font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=16, column=1, pady=5, sticky="w")
    tk.Button(scrollable_frame, text="Despawn Entity", command=gui.generate_kill_properties_command, font=("Arial", 10), bg='#FF4444', fg='#ffffff').grid(row=16, column=2, pady=5, sticky="w")

    # Output Text
    gui.modify_properties_cmd_text = tk.Text(scrollable_frame, height=5, width=40)
    gui.modify_properties_cmd_text.grid(row=17, column=0, columnspan=3, pady=2, sticky="nsew")
    tk.Button(scrollable_frame, text="Copy", command=lambda: gui.copy_to_clipboard(gui.modify_properties_cmd_text.get("1.0", tk.END).strip()), font=("Arial", 10), bg='#4CAF50', fg='#ffffff').grid(row=17, column=3, pady=2, sticky="w")

    # Instructions
    tk.Label(scrollable_frame, text="Select 'laser' to modify block display commands or 'end beam' for end crystal commands. Check 'Modify' to update fields.", font=("Arial", 8), bg='#f0f0f0').grid(row=18, column=0, columnspan=4, pady=2, sticky="w")

    # Configure weights
    scrollable_frame.columnconfigure(0, weight=1)
    scrollable_frame.columnconfigure(1, weight=1)
    scrollable_frame.columnconfigure(2, weight=1)
    scrollable_frame.columnconfigure(3, weight=0)
    scrollable_frame.rowconfigure(17, weight=1)

    # Store original grid configurations
    widget_configs = {}
    laser_widgets = [block_label, block_check, block_entry, scale_label, scale_check, scale_x_label, scale_x_entry, scale_y_label, scale_y_entry, scale_z_label, scale_z_entry]
    end_beam_widgets = [target_label, target_check, target_x_label, target_x_entry, target_y_label, target_y_entry, target_z_label, target_z_entry]
    for widget in laser_widgets + end_beam_widgets:
        widget_configs[widget] = widget.grid_info()
        logging.debug(f"Stored config for widget {widget.winfo_class()} at row {widget.grid_info().get('row')}: {widget_configs[widget]}")

    # Dynamic UI adjustment based on command type
    def update_ui(*args):
        is_laser = gui.command_type.get() == "laser"
        logging.debug(f"Starting UI update: command_type={gui.command_type.get()}, is_laser={is_laser}")

        # Update laser-related widgets (Block and Scale)
        for widget in laser_widgets:
            if is_laser and widget_configs.get(widget):
                try:
                    widget.grid(**widget_configs[widget])
                    logging.debug(f"Gridded widget {widget.winfo_class()} at row {widget_configs[widget]['row']}")
                except tk.TclError as e:
                    logging.error(f"Error gridding widget {widget.winfo_class()}: {e}")
            else:
                try:
                    widget.grid_remove()
                    logging.debug(f"Removed widget {widget.winfo_class()} at row {widget_configs[widget]['row']}")
                except tk.TclError as e:
                    logging.error(f"Error removing widget {widget.winfo_class()}: {e}")

        # Update end beam-related widgets (Target Coordinates)
        for widget in end_beam_widgets:
            if not is_laser and widget_configs.get(widget):
                try:
                    widget.grid(**widget_configs[widget])
                    logging.debug(f"Gridded widget {widget.winfo_class()} at row {widget_configs[widget]['row']}")
                except tk.TclError as e:
                    logging.error(f"Error gridding widget {widget.winfo_class()}: {e}")
            else:
                try:
                    widget.grid_remove()
                    logging.debug(f"Removed widget {widget.winfo_class()} at row {widget_configs[widget]['row']}")
                except tk.TclError as e:
                    logging.error(f"Error removing widget {widget.winfo_class()}: {e}")

        # Force canvas update
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        logging.debug("Canvas updated after UI change")

    gui.command_type.trace_add("write", update_ui)
    command_combobox.bind("<<ComboboxSelected>>", lambda event: update_ui())
    update_ui()  # Initial UI setup