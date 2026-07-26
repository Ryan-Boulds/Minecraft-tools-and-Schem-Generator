# laser_animations/animator_tab/animator_preview.py
"""
3D preview of the path equation, shown in a small popup window, with a
Play button that animates a line growing from the origin out to the
current point as t sweeps from t_start to t_end, then loops back to the
start and repeats.

matplotlib is imported lazily so the rest of the Animate tab still works
fully (generation + export) if matplotlib isn't installed - only the
Preview Path button needs it.

Requires: matplotlib (pip install matplotlib)
"""
import tkinter as tk
from tkinter import ttk


def _lazy_imports():
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)
    return Figure, FigureCanvasTkAgg


class PathPreview:
    """Opens a Toplevel window plotting the 3D path, with Play/Pause
    animating the beam sweeping from t_start to t_end and looping."""

    @staticmethod
    def show(points, total_time_ms=2000):
        preview = PathPreview(points, total_time_ms)
        preview._build()
        return preview

    def __init__(self, points, total_time_ms):
        self.points = points
        self.xs = [p[0] for p in points]
        self.ys = [p[1] for p in points]
        self.zs = [p[2] for p in points]
        self.num_frames = len(points)
        # Spread the on-screen animation across roughly total_time_ms,
        # so the preview's pacing matches the real duration you entered.
        self.interval_ms = max(10, int(total_time_ms / max(1, self.num_frames)))
        self.frame_idx = 0
        self.playing = False
        self._after_id = None

    def _build(self):
        Figure, FigureCanvasTkAgg = _lazy_imports()

        self.window = tk.Toplevel()
        self.window.title("Path Preview")
        self.window.geometry("520x560")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = fig.add_subplot(111, projection="3d")

        # Faint full path for reference, plus a fixed marker at the
        # origin (where the already-spawned laser conceptually sits).
        self.ax.plot(self.xs, self.ys, self.zs, color="#cccccc", linewidth=1)
        self.ax.scatter([0], [0], [0], color="red", label="Origin")

        (self.anim_line,) = self.ax.plot([], [], [], color="#2e7d32", linewidth=2, label="Beam")
        (self.head_point,) = self.ax.plot([], [], [], marker="o", color="#1565c0")

        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        self.ax.legend(loc="upper left", fontsize=8)

        self._set_fixed_bounds()

        self.canvas = FigureCanvasTkAgg(fig, master=self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        controls = ttk.Frame(self.window)
        controls.pack(fill="x", pady=6)
        self.play_button = tk.Button(
            controls, text="Play", command=self._toggle_play,
            font=("Segoe UI", 10), bg="#4CAF50", fg="#ffffff", width=10,
        )
        self.play_button.pack(side="left", padx=10)

        self._draw_frame()

    def _set_fixed_bounds(self):
        all_x = self.xs + [0.0]
        all_y = self.ys + [0.0]
        all_z = self.zs + [0.0]

        cx = (max(all_x) + min(all_x)) / 2
        cy = (max(all_y) + min(all_y)) / 2
        cz = (max(all_z) + min(all_z)) / 2
        span = max(max(all_x) - min(all_x), max(all_y) - min(all_y), max(all_z) - min(all_z), 1e-6)
        half = span / 2 * 1.1

        self.ax.set_xlim(cx - half, cx + half)
        self.ax.set_ylim(cy - half, cy + half)
        self.ax.set_zlim(cz - half, cz + half)
        try:
            self.ax.set_box_aspect((1, 1, 1))
        except AttributeError:
            pass  # older matplotlib without set_box_aspect

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_button.config(text="Pause" if self.playing else "Play")
        if self.playing:
            self._step()

    def _draw_frame(self):
        i = self.frame_idx
        xs = self.xs[:i + 1]
        ys = self.ys[:i + 1]
        zs = self.zs[:i + 1]
        self.anim_line.set_data(xs, ys)
        self.anim_line.set_3d_properties(zs)
        self.head_point.set_data([self.xs[i]], [self.ys[i]])
        self.head_point.set_3d_properties([self.zs[i]])
        self.canvas.draw_idle()

    def _step(self):
        if not self.playing:
            return
        self._draw_frame()
        self.frame_idx = (self.frame_idx + 1) % self.num_frames
        self._after_id = self.canvas.get_tk_widget().after(self.interval_ms, self._step)

    def _on_close(self):
        self.playing = False
        if self._after_id is not None:
            try:
                self.canvas.get_tk_widget().after_cancel(self._after_id)
            except Exception:
                pass
        self.window.destroy()
