"""Indicadores solares discretos para visualizaciones 2D.

El módulo no recalcula geometría solar: solamente representa los valores de
azimut/elevación ya calculados por Proyecto Sombra.
"""
from __future__ import annotations

import math
from typing import Any

from matplotlib.patches import Circle


def _to_float(value: Any) -> float | None:
    if hasattr(value, "get"):
        try:
            value = value.get()
        except Exception:
            return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def add_solar_indicator_2d(ax, azimuth_deg: Any, altitude_deg: Any, *, corner: str = "upper-left") -> None:
    """Dibuja un mini-compás solar fuera del contenido científico principal."""
    azimuth = _to_float(azimuth_deg)
    altitude = _to_float(altitude_deg)
    if azimuth is None or altitude is None:
        return

    if corner == "upper-right":
        bounds = [0.755, 0.785, 0.23, 0.185]
    else:
        bounds = [0.015, 0.785, 0.23, 0.185]
    inset = ax.inset_axes(bounds)
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

    azi = math.radians(azimuth)
    x2 = cx + math.sin(azi) * radius * 0.82
    y2 = cy + math.cos(azi) * radius * 0.82
    inset.annotate(
        "", xy=(x2, y2), xytext=(cx, cy),
        arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#d88a00", shrinkA=0, shrinkB=0),
    )
    inset.add_patch(Circle((x2, y2), radius * 0.16, facecolor="#ffd34d", edgecolor="#d88a00", linewidth=0.9))
    inset.text(0.48, 0.80, "Sol", fontsize=7.5, weight="bold", color="#6b4c00", ha="left", va="center")
    inset.text(0.48, 0.55, f"Az {azimuth:.0f}°", fontsize=6.8, color="0.25", ha="left", va="center")
    inset.text(0.48, 0.33, f"El {altitude:.0f}°", fontsize=6.8, color="0.25", ha="left", va="center")
