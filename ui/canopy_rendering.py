"""Representación consistente de formas de copa en Matplotlib 2D/3D."""
from __future__ import annotations

import math
import numpy as np
from matplotlib.patches import Circle, Ellipse, Polygon, RegularPolygon

from core.crown_shapes import canopy_profile, normalize_canopy_shape


def draw_canopy_2d(ax, tree, *, facecolor="green", edgecolor="darkgreen", alpha=0.66, zorder=6, label=None):
    """Dibuja una simbología de planta de la copa en unidades de datos."""
    x = float(getattr(tree, "x", 0.0))
    y = float(getattr(tree, "y", 0.0))
    r = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
    shape = normalize_canopy_shape(getattr(tree, "forma_copa", None))
    artists = []

    def add(patch, *, main=False):
        if main and label:
            patch.set_label(label)
        ax.add_patch(patch)
        artists.append(patch)

    common = dict(facecolor=facecolor, edgecolor=edgecolor, linewidth=1.0, alpha=alpha, zorder=zorder)
    if shape == "Esférica":
        add(Circle((x, y), r, **common), main=True)
    elif shape == "Cónica":
        add(Circle((x, y), r, **common), main=True)
        add(Circle((x, y), r * 0.38, facecolor="none", edgecolor=edgecolor,
                   linewidth=0.9, alpha=min(1.0, alpha + 0.15), zorder=zorder + 0.1))
        for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            ax.plot([x, x + r * math.cos(ang)], [y, y + r * math.sin(ang)],
                    color=edgecolor, linewidth=0.55, alpha=0.45, zorder=zorder + 0.2)
    elif shape == "Columnar":
        add(Ellipse((x, y), width=1.10 * r, height=2.0 * r, **common), main=True)
    elif shape == "Piramidal":
        add(RegularPolygon((x, y), numVertices=4, radius=r, orientation=math.pi / 4, **common), main=True)
    elif shape == "Extendida":
        add(Ellipse((x, y), width=2.0 * r, height=1.10 * r, **common), main=True)
    elif shape == "Irregular":
        angles = np.linspace(0.0, 2.0 * math.pi, 11)[:-1]
        factors = np.array([1.00, 0.78, 0.92, 0.70, 0.98, 0.76, 0.88, 0.72, 0.96, 0.80])
        points = np.column_stack((x + r * factors * np.cos(angles), y + r * factors * np.sin(angles)))
        add(Polygon(points, closed=True, **common), main=True)
    else:  # Llora
        add(Circle((x, y), r * 0.70, **common), main=True)
        for ang in np.linspace(0.0, 2.0 * math.pi, 6, endpoint=False):
            cx = x + r * 0.52 * math.cos(ang)
            cy = y + r * 0.52 * math.sin(ang)
            add(Circle((cx, cy), r * 0.38, facecolor=facecolor, edgecolor=edgecolor,
                       linewidth=0.8, alpha=alpha * 0.92, zorder=zorder - 0.05))
    return artists


def _ellipsoid(ax, center, radii, color, alpha):
    cx, cy, cz = center
    rx, ry, rz = radii
    u = np.linspace(0, 2 * np.pi, 24)
    v = np.linspace(0, np.pi, 14)
    X = cx + rx * np.outer(np.cos(u), np.sin(v))
    Y = cy + ry * np.outer(np.sin(u), np.sin(v))
    Z = cz + rz * np.outer(np.ones_like(u), np.cos(v))
    return ax.plot_surface(X, Y, Z, color=color, alpha=alpha, linewidth=0, shade=True)


def draw_canopy_3d_mpl(ax, tree, *, color="green", alpha=0.88):
    """Representa las siete formas de copa en el fallback Matplotlib 3D."""
    x = float(getattr(tree, "x", 0.0))
    y = float(getattr(tree, "y", 0.0))
    h = max(0.2, float(getattr(tree, "h", getattr(tree, "altura", 1.0)) or 1.0))
    r = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
    p = canopy_profile(getattr(tree, "forma_copa", None), r, h)
    shape = p["shape"]
    ch = float(p["crown_height"])
    base = float(p["crown_base"])
    center = float(p["crown_center"])

    if shape == "Cónica":
        th = np.linspace(0, 2 * np.pi, 28)
        zz = np.linspace(base, h, 16)
        TH, ZZ = np.meshgrid(th, zz)
        RR = r * np.clip((h - ZZ) / max(ch, 1e-6), 0.0, 1.0)
        ax.plot_surface(x + RR * np.cos(TH), y + RR * np.sin(TH), ZZ,
                        color=color, alpha=alpha, linewidth=0, shade=True)
    elif shape == "Piramidal":
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        q = r / math.sqrt(2)
        b = [(x-q,y-q,base),(x+q,y-q,base),(x+q,y+q,base),(x-q,y+q,base)]
        apex = (x, y, h)
        faces = [[b[i], b[(i+1)%4], apex] for i in range(4)] + [b]
        ax.add_collection3d(Poly3DCollection(faces, facecolor=color, edgecolor="darkgreen", alpha=alpha))
    elif shape == "Columnar":
        _ellipsoid(ax, (x, y, center), (r*0.56, r*0.56, ch/2), color, alpha)
    elif shape == "Extendida":
        _ellipsoid(ax, (x, y, center), (r, r*0.56, ch/2), color, alpha)
        _ellipsoid(ax, (x-r*0.38, y, center-ch*0.04), (r*0.58, r*0.45, ch*0.38), color, alpha*0.92)
        _ellipsoid(ax, (x+r*0.38, y, center-ch*0.03), (r*0.58, r*0.45, ch*0.36), color, alpha*0.92)
    elif shape == "Irregular":
        specs = [(0,0,0,0.72,0.70,0.50),(0.35,0.08,0.02,0.55,0.48,0.38),(-0.30,-0.12,-0.04,0.58,0.54,0.40),(0.05,0.34,-0.08,0.48,0.52,0.34)]
        for dx,dy,dz,sx,sy,sz in specs:
            _ellipsoid(ax, (x+r*dx,y+r*dy,center+ch*dz), (r*sx,r*sy,ch*sz), color, alpha*0.95)
    elif shape == "Llora":
        _ellipsoid(ax, (x,y,h-ch*0.28), (r*0.72,r*0.70,ch*0.28), color, alpha)
        for ang in np.linspace(0, 2*np.pi, 6, endpoint=False):
            _ellipsoid(ax, (x+r*0.50*np.cos(ang), y+r*0.50*np.sin(ang), base+ch*0.43),
                       (r*0.30,r*0.30,ch*0.43), color, alpha*0.90)
    else:
        _ellipsoid(ax, (x, y, center), (r, r, ch/2), color, alpha)
