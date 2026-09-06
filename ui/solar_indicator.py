"""Indicadores solares discretos para vistas 2D/3D.

Estos helpers son exclusivamente visuales: representan la posición del sol
usando azimut y elevación YA calculados por el proyecto.
"""
from __future__ import annotations

import math
from typing import Any

from matplotlib.patches import Circle


def _as_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def add_solar_indicator_2d(ax, azimuth_deg: Any, altitude_deg: Any) -> None:
    """Agrega un indicador solar limpio y discreto a un gráfico 2D.

    Muestra un mini-compás con la proyección del azimut solar y una etiqueta
    compacta con azimut/elevación. No depende de la escala del eje principal.
    """
    azimuth_deg = _as_float(azimuth_deg)
    altitude_deg = _as_float(altitude_deg)
    if azimuth_deg is None or altitude_deg is None:
        return

    inset = ax.inset_axes([0.015, 0.785, 0.235, 0.185])
    inset.set_xlim(0.0, 1.0)
    inset.set_ylim(0.0, 1.0)
    inset.set_xticks([])
    inset.set_yticks([])
    inset.patch.set_facecolor((1.0, 1.0, 1.0, 0.84))
    for spine in inset.spines.values():
        spine.set_edgecolor("0.72")
        spine.set_linewidth(0.8)

    cx, cy = 0.25, 0.52
    radius = 0.18
    inset.add_patch(Circle((cx, cy), radius, facecolor=(1, 1, 1, 0), edgecolor="0.55", linewidth=0.9))
    inset.plot([cx, cx], [cy - radius, cy + radius], color="0.80", lw=0.8)
    inset.plot([cx - radius, cx + radius], [cy, cy], color="0.80", lw=0.8)
    inset.text(cx, cy + radius + 0.05, "N", ha="center", va="bottom", fontsize=6.5, color="0.35")
    inset.text(cx + radius + 0.05, cy, "E", ha="left", va="center", fontsize=6.5, color="0.35")

    azi = math.radians(azimuth_deg)
    dx = math.sin(azi)
    dy = math.cos(azi)
    x2 = cx + dx * radius * 0.82
    y2 = cy + dy * radius * 0.82
    inset.annotate(
        "",
        xy=(x2, y2),
        xytext=(cx, cy),
        arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#d88a00", shrinkA=0, shrinkB=0),
    )
    inset.add_patch(Circle((x2, y2), radius * 0.16, facecolor="#ffd34d", edgecolor="#d88a00", linewidth=0.9))
    inset.text(0.48, 0.80, "Sol", fontsize=7.5, weight="bold", color="#6b4c00", ha="left", va="center")
    inset.text(0.48, 0.55, f"Az {azimuth_deg:.0f}°", fontsize=6.8, color="0.25", ha="left", va="center")
    inset.text(0.48, 0.33, f"El {altitude_deg:.0f}°", fontsize=6.8, color="0.25", ha="left", va="center")
