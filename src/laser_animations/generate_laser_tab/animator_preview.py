# laser_animations/animator_tab/animator_preview.py
"""
Optional 3D preview of the path equation, shown in a small popup window.
matplotlib is imported lazily so the rest of the Animate tab still works
fully (generation + export) if matplotlib isn't installed - only the
Preview Path button needs it.

Requires: matplotlib (pip install matplotlib)
"""
import tkinter as tk


def _lazy_imports():
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)
    return Figure, FigureCanvasTkAgg


class PathPreview:
    """Opens a Toplevel window plotting the 3D path, the origin (laser
    position), and the start/end points."""

    @staticmethod
    def show(points):
        Figure, FigureCanvasTkAgg = _lazy_imports()

        window = tk.Toplevel()
        window.title("Path Preview")
        window.geometry("500x500")

        fig = Figure(figsize=(5, 5), dpi=100)
        ax = fig.add_subplot(111, projection="3d")

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        zs = [p[2] for p in points]

        ax.plot(xs, ys, zs, color="#2e7d32", label="Path")
        ax.scatter([0], [0], [0], color="red", label="Origin (laser)")
        ax.scatter([xs[0]], [ys[0]], [zs[0]], color="blue", label="t start")
        ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color="orange", label="t end")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.legend(loc="upper left", fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
