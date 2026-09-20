"""Geometrías normalizadas de copa para representación 2D/3D.

La forma de copa es, por ahora, un atributo geométrico de representación.
No modifica el kernel científico de sombreado/radiación: cambiar esa física
requiere calibración independiente.
"""
from __future__ import annotations

import unicodedata

CANOPY_SHAPES = (
    "Esférica",
    "Cónica",
    "Columnar",
    "Piramidal",
    "Extendida",
    "Irregular",
    "Llora",
)
DEFAULT_CANOPY_SHAPE = "Esférica"


def _key(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return raw.strip().lower()


_ALIASES = {
    "esferica": "Esférica",
    "esferico": "Esférica",
    "redonda": "Esférica",
    "conica": "Cónica",
    "conico": "Cónica",
    "columnar": "Columnar",
    "piramidal": "Piramidal",
    "extendida": "Extendida",
    "extendido": "Extendida",
    "irregular": "Irregular",
    "llora": "Llora",
    "llorona": "Llora",
    "pendula": "Llora",
    "pendulo": "Llora",
}


def normalize_canopy_shape(value: object) -> str:
    """Devuelve una de las formas canónicas, conservando retrocompatibilidad."""
    return _ALIASES.get(_key(value), DEFAULT_CANOPY_SHAPE)


def canopy_profile(shape: object, radius: float, tree_height: float) -> dict[str, float | str]:
    """Proporciones gráficas 3D contenidas en la altura/radio del árbol.

    ``radio_copa`` se interpreta como envolvente horizontal máxima. Por eso
    ninguna forma supera ese radio en X/Y.
    """
    forma = normalize_canopy_shape(shape)
    r = max(0.15, float(radius or 0.15))
    h = max(0.2, float(tree_height or 0.2))

    factors = {
        "Esférica": (1.00, 1.00, 1.65, 0.34, 0.64),
        "Cónica": (1.00, 1.00, 2.15, 0.44, 0.74),
        "Columnar": (0.56, 0.56, 2.75, 0.54, 0.80),
        "Piramidal": (1.00, 1.00, 2.20, 0.46, 0.76),
        "Extendida": (1.00, 0.56, 1.05, 0.25, 0.46),
        "Irregular": (1.00, 0.92, 1.75, 0.36, 0.66),
        "Llora": (1.00, 0.95, 2.05, 0.46, 0.74),
    }
    sx, sy, r_mult, h_frac, max_frac = factors[forma]
    crown_height = min(max(r * r_mult, h * h_frac), h * max_frac)
    crown_height = max(0.20, min(crown_height, max(0.20, h - 0.05)))
    crown_base = max(0.05, h - crown_height)
    crown_center = crown_base + crown_height / 2.0
    trunk_height = max(0.15, min(h * 0.88, crown_base + crown_height * 0.08))
    return {
        "shape": forma,
        "radius": r,
        "height": h,
        "x_scale": sx,
        "y_scale": sy,
        "crown_height": crown_height,
        "crown_base": crown_base,
        "crown_center": crown_center,
        "trunk_height": trunk_height,
    }
