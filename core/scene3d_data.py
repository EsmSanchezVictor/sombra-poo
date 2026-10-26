"""Datos de visualización a partir de matrices ya calculadas, sin backend gráfico."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math
import numpy as np

@dataclass(frozen=True)
class Scene3DData:
    X: np.ndarray
    Y: np.ndarray
    temperature: np.ndarray
    trees: tuple[Any, ...]
    structures: tuple[Any, ...]
    temperature_unit: str
    title: str
    solar_altitude_deg: float | None = None
    solar_azimuth_deg: float | None = None


def _optional_float(value: Any) -> float | None:
    if hasattr(value, "get"):
        try:
            value = value.get()
        except Exception:
            return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _finite_range(values: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = float(np.min(finite)), float(np.max(finite))
    if math.isclose(lo, hi, rel_tol=0.0, abs_tol=1e-12):
        eps = max(0.01, abs(lo) * 1e-6)
        return lo - eps, hi + eps
    return lo, hi


def _scene_extent(data: Scene3DData) -> tuple[float, float, float, float, float]:
    xmin = float(np.nanmin(data.X))
    xmax = float(np.nanmax(data.X))
    ymin = float(np.nanmin(data.Y))
    ymax = float(np.nanmax(data.Y))
    max_height = 1.0
    for tree in data.trees:
        max_height = max(max_height, float(getattr(tree, "h", 0.0) or 0.0))
    for structure in data.structures:
        max_height = max(max_height, float(getattr(structure, "altura", 0.0) or 0.0))
    return xmin, xmax, ymin, ymax, max_height


def _temperature_display(vars_dict: dict[str, Any]) -> tuple[np.ndarray, str]:
    T = np.asarray(vars_dict["T"], dtype=np.float32)
    app = vars_dict.get("_app_instance")
    if app is not None:
        return (
            np.asarray(app.convert_temperature_for_display(T), dtype=np.float32),
            app.get_temperature_unit_symbol(),
        )
    return T, "K"


def scene_data_from_vars(vars_dict: dict[str, Any], title: str) -> Scene3DData:
    """Construye los datos visuales a partir de resultados YA calculados."""
    X = np.asarray(vars_dict["X"], dtype=np.float32)
    Y = np.asarray(vars_dict["Y"], dtype=np.float32)
    temperature, unit = _temperature_display(vars_dict)
    return Scene3DData(
        X=X,
        Y=Y,
        temperature=temperature,
        trees=tuple(vars_dict.get("arboles", ()) or ()),
        structures=tuple(vars_dict.get("estructuras", ()) or ()),
        temperature_unit=unit,
        title=title,
        solar_altitude_deg=_optional_float(vars_dict.get("_render_solar_altitude_deg")),
        solar_azimuth_deg=_optional_float(vars_dict.get("_render_solar_azimuth_deg")),
    )


