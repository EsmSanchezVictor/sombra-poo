"""Backend Matplotlib independiente del controlador VTK; sólo representación."""
from __future__ import annotations
import math
import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from core.species import color_copa
from core.crown_shapes import canopy_profile, normalize_canopy_shape
from ui.canopy_rendering import draw_canopy_3d_mpl
from plot_style import CMAP_TEMPERATURA
from core.scene3d_data import Scene3DData, _finite_range, _scene_extent
from ui.scene3d_backend import vtk_installation_info

def render_matplotlib_fallback(
    parent: tk.Misc,
    data: Scene3DData,
    vtk_error: Exception | None,
) -> None:
    """Fallback compatible; también queda dentro del mismo frame."""
    top = tk.Frame(parent)
    top.pack(side=tk.TOP, fill=tk.X)
    text = "Motor 3D: Matplotlib (fallback)"
    if vtk_error is None:
        text += " · VTK no está instalado"
    else:
        text += " · VTK no pudo inicializarse"
    if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
        text += f" · ☀ Az {data.solar_azimuth_deg:.0f}° · El {data.solar_altitude_deg:.0f}°"
    tk.Label(top, text=text, anchor="w").pack(side=tk.LEFT, padx=6, pady=3)
    if vtk_error is not None:
        detail = f"{type(vtk_error).__name__}: {vtk_error}"
        diag = tk.Label(
            parent,
            text=f"{vtk_installation_info()} · {detail}",
            anchor="w",
            justify="left",
            fg="#8a2d2d",
            wraplength=1000,
        )
        diag.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 3))

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    X, Y, T = data.X, data.Y, data.temperature
    lo, hi = _finite_range(T)
    levels = np.linspace(lo, hi, 20)
    floor = ax.contourf(
        X,
        Y,
        T,
        levels=levels,
        zdir="z",
        offset=0,
        cmap=CMAP_TEMPERATURA,
        alpha=0.50,
    )
    # Isotermas también en el fallback para mantener la misma lectura visual.
    iso = ax.contour(
        X, Y, T, levels=np.linspace(lo, hi, 6), zdir="z", offset=0.015,
        colors="0.18", linewidths=0.8, alpha=0.80,
    )
    cbar = fig.colorbar(floor, ax=ax, shrink=0.68, aspect=14, pad=0.07)
    cbar.set_label(f"Temperatura ({data.temperature_unit})")

    for tree in data.trees:
        x = float(getattr(tree, "x", 0.0))
        y = float(getattr(tree, "y", 0.0))
        h = max(0.2, float(getattr(tree, "h", getattr(tree, "altura", 1.0)) or 1.0))
        r = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
        profile = canopy_profile(getattr(tree, "forma_copa", None), r, h)
        ax.plot([x, x], [y, y], [0, float(profile["trunk_height"])], color="saddlebrown", linewidth=2.5)
        draw_canopy_3d_mpl(
            ax, tree, color=color_copa(getattr(tree, "especie", "")), alpha=0.88
        )

    for structure in data.structures:
        tipo = str(getattr(structure, "tipo", ""))
        x1, y1 = float(structure.x1), float(structure.y1)
        x2, y2 = float(structure.x2), float(structure.y2)
        h = max(0.0, float(getattr(structure, "altura", 0.0) or 0.0))
        if tipo == "Pared":
            panel = [[(x1, y1, 0), (x2, y2, 0), (x2, y2, h), (x1, y1, h)]]
            ax.add_collection3d(
                Poly3DCollection(
                    panel, facecolor="0.5", alpha=0.72, edgecolor="0.25"
                )
            )
        else:
            z = h if tipo == "Galeria" else 0.04
            rect = [[(x1, y1, z), (x2, y1, z), (x2, y2, z), (x1, y2, z)]]
            color = "saddlebrown" if tipo == "Galeria" else "0.5"
            ax.add_collection3d(
                Poly3DCollection(rect, facecolor=color, alpha=0.55)
            )

    if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
        xmin, xmax, ymin, ymax, max_height = _scene_extent(data)
        span = max(xmax - xmin, ymax - ymin, 1.0)
        center = ((xmin + xmax) / 2, (ymin + ymax) / 2, max_height * 0.35)
        alt = math.radians(data.solar_altitude_deg)
        azi = math.radians(data.solar_azimuth_deg)
        sx = math.sin(azi) * math.cos(alt)
        sy = math.cos(azi) * math.cos(alt)
        sz = max(0.10, math.sin(alt))
        sun_distance = span * 0.45
        sun_x = center[0] + sx * sun_distance
        sun_y = center[1] + sy * sun_distance
        sun_z = center[2] + sz * sun_distance
        ax.scatter([sun_x], [sun_y], [sun_z], s=220, color="#ffd34d", edgecolors="#d88a00", depthshade=False)
        ax.plot([sun_x, center[0]], [sun_y, center[1]], [sun_z, max(0.05, center[2] * 0.12)], color="#d88a00", alpha=0.45, linewidth=1.4)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Altura (m)")
    ax.set_title(data.title)
    ax.view_init(elev=38, azim=-58)

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, parent, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    class _FallbackController:
        def close(self_nonlocal) -> None:
            try:
                canvas.get_tk_widget().destroy()
            except Exception:
                pass
            fig.clear()

    setattr(parent, "_sombra_scene3d_controller", _FallbackController())
