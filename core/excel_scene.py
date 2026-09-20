"""Persistencia robusta de escenas y parámetros térmicos en Excel.

Objetivo principal: que un archivo guardado desde Edición pueda abrirse en
Modelo y reconstruir tanto la geometría como las condiciones del cálculo.
El formato es deliberadamente simple y retrocompatible:

- ``Árboles``: siempre se escribe con encabezados, aunque no haya árboles.
- ``Estructuras``: siempre se escribe con encabezados, aunque esté vacía.
- ``Parametros``: pares clave/valor con las condiciones necesarias para
  reproducir el cálculo.

Los lectores toleran archivos antiguos sin ``Parametros`` y las hojas vacías
sin encabezados generadas por versiones anteriores.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import math
import unicodedata

import pandas as pd

from core.model_registry import SCIENTIFIC_RELEASE, SCIENTIFIC_SCHEMA
from core.crown_shapes import DEFAULT_CANOPY_SHAPE, normalize_canopy_shape


FORMAT_VERSION = 3

TREE_COLUMNS = [
    "X",
    "Y",
    "Altura (m)",
    "Densidad_copa (0-1)",
    "Radio_copa (m)",
    "Especie",
    "Forma_copa",
]

STRUCTURE_COLUMNS = [
    "Tipo",
    "X_inicial",
    "Y_inicial",
    "X_final",
    "Y_final",
    "Altura (m)",
    "Opacidad (0-1)",
    "Material",
]

PARAM_COLUMNS = ["Parametro", "Valor", "Unidad", "Descripcion"]

# nombre en Excel -> clave interna de vars
PARAM_TO_VAR = {
    "T_amb_base_K": "T_amb_base",
    "I_sol_base_W_m2": "I_sol_base",
    "T_min_K": "T_min",
    "T_max_K": "T_max",
    "dia_del_ano": "dia",
    "latitud": "lat",
    "longitud": "lon",
    "hora_local": "hora",
    "humedad_relativa_pct": "humedad",
    "viento": "viento",
    "timezone": "timezone",
    "nubosidad": "nubosidad",
}

PARAM_METADATA = {
    "formato_version": ("", "Versión del esquema del archivo"),
    "scientific_release": ("", "Versión científica del modelo"),
    "scientific_schema": ("", "Esquema metodológico del proyecto"),
    "origen": ("", "Módulo que generó el archivo"),
    "modo_calculo": ("", "Modo requerido para reproducir el cálculo"),
    "modo_ui_origen": ("", "Modo de interfaz visible al guardar"),
    "surface_model_mode": ("", "Modelo térmico de superficie: standard/advanced/advanced_vegetation"),
    "ground_vegetation_fraction": ("0-1", "Fracción global de suelo vegetado en modelo v2"),
    "vegetation_water_availability": ("0-1", "Disponibilidad hídrica efectiva del suelo vegetado"),
    "canopy_water_availability": ("0-1", "Disponibilidad hídrica efectiva de las copas"),
    "radiation_source_mode": ("", "Fuente radiativa: clear_sky/manual_measured/manual_scenario/observed_series"),
    "radiation_source_label": ("", "Descripción legible de la fuente radiativa"),
    "radiation_quality": ("", "Calidad/procedencia del dato radiativo"),
    "meteorology_csv": ("", "Nombre/ruta de la serie meteorológica asociada"),
    "ghi_wm2": ("W/m²", "GHI usado en el último cálculo"),
    "dni_wm2": ("W/m²", "DNI usado en el último cálculo"),
    "dhi_wm2": ("W/m²", "DHI usado en el último cálculo"),
    "T_amb_base_K": ("K", "Temperatura de aire base del instante"),
    "I_sol_base_W_m2": ("W/m²", "Irradiancia base usada por el modelo"),
    "T_min_K": ("K", "Temperatura mínima diaria"),
    "T_max_K": ("K", "Temperatura máxima diaria"),
    "dia_del_ano": ("1-366", "Día del año"),
    "latitud": ("°", "Latitud geográfica"),
    "longitud": ("°", "Longitud geográfica"),
    "hora_local": ("h", "Hora local decimal"),
    "humedad_relativa_pct": ("%", "Humedad relativa"),
    "viento": ("", "Categoría o velocidad de viento"),
    "timezone": ("IANA", "Zona horaria IANA"),
    "nubosidad": ("", "Categoría de nubosidad del escenario"),
    "simple_temp_air_c": ("°C", "Temperatura de aire visible en modo simple"),
    "simple_rh_pct": ("%", "Humedad relativa visible en modo simple"),
    "simple_country": ("", "País seleccionado en modo simple"),
    "simple_city": ("", "Ciudad seleccionada en modo simple"),
}


@dataclass
class SceneWorkbook:
    arboles: pd.DataFrame
    estructuras: pd.DataFrame
    parametros: dict[str, Any]


def _value(value: Any) -> Any:
    """Obtiene el valor de una Tk Variable o devuelve el objeto tal cual."""
    if hasattr(value, "get"):
        try:
            return value.get()
        except Exception:
            return value
    return value


def _safe_scalar(value: Any) -> Any:
    """Convierte escalares numpy/pandas y NaN a valores serializables."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _norm(text: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().lower()


def _find_sheet(sheet_names: list[str], *candidates: str) -> str | None:
    normalized = {_norm(name): name for name in sheet_names}
    for candidate in candidates:
        if _norm(candidate) in normalized:
            return normalized[_norm(candidate)]
    return None


def _empty_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _read_sheet_or_empty(xls: pd.ExcelFile, columns: list[str], *names: str) -> pd.DataFrame:
    sheet = _find_sheet(xls.sheet_names, *names)
    if sheet is None:
        return _empty_df(columns)
    df = pd.read_excel(xls, sheet_name=sheet)
    # Versiones previas escribían una hoja completamente vacía cuando la
    # lista de objetos era vacía. read_excel devuelve entonces 0 columnas.
    if df.empty and len(df.columns) == 0:
        return _empty_df(columns)
    return df


def _drop_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.dropna(how="all").copy()


def _prepare_trees(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_blank_rows(df)
    if df.empty:
        return _empty_df(TREE_COLUMNS)

    required = ["X", "Y", "Altura (m)", "Densidad_copa (0-1)", "Radio_copa (m)"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("La hoja Árboles no contiene las columnas requeridas: " + ", ".join(missing))

    if "Especie" not in df.columns:
        df["Especie"] = ""
    df["Especie"] = df["Especie"].fillna("").astype(str)
    if "Forma_copa" not in df.columns:
        df["Forma_copa"] = DEFAULT_CANOPY_SHAPE
    df["Forma_copa"] = df["Forma_copa"].apply(normalize_canopy_shape)

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Filas sin coordenadas/altura no describen un árbol válido.
    df = df.dropna(subset=required)
    return df.reindex(columns=TREE_COLUMNS)


def _prepare_structures(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_blank_rows(df)
    if df.empty:
        return _empty_df(STRUCTURE_COLUMNS)

    numeric = ["X_inicial", "Y_inicial", "X_final", "Y_final", "Altura (m)", "Opacidad (0-1)"]
    missing = [c for c in numeric[:4] if c not in df.columns]
    if missing:
        raise ValueError("La hoja Estructuras no contiene las columnas requeridas: " + ", ".join(missing))

    # Compatibilidad razonable con archivos antiguos incompletos.
    if "Tipo" not in df.columns:
        df["Tipo"] = "Pared"
    if "Altura (m)" not in df.columns:
        df["Altura (m)"] = 0.0
    if "Opacidad (0-1)" not in df.columns:
        df["Opacidad (0-1)"] = 1.0
    if "Material" not in df.columns:
        df["Material"] = "suelo"

    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Altura (m)"] = df["Altura (m)"].fillna(0.0)
    df["Opacidad (0-1)"] = df["Opacidad (0-1)"].fillna(1.0).clip(0.0, 1.0)
    df = df.dropna(subset=numeric[:4])
    return df.reindex(columns=STRUCTURE_COLUMNS)


def _read_parameters(xls: pd.ExcelFile) -> dict[str, Any]:
    sheet = _find_sheet(xls.sheet_names, "Parametros", "Parámetros", "Parameters")
    if sheet is None:
        return {}
    df = pd.read_excel(xls, sheet_name=sheet)
    if df.empty:
        return {}

    # Formato actual: Parametro | Valor | Unidad | Descripcion
    param_col = next((c for c in df.columns if _norm(c) in {"parametro", "parameter", "clave"}), None)
    value_col = next((c for c in df.columns if _norm(c) in {"valor", "value"}), None)
    if param_col is not None and value_col is not None:
        out: dict[str, Any] = {}
        for _, row in df.iterrows():
            key = str(row[param_col]).strip() if not pd.isna(row[param_col]) else ""
            if key:
                out[key] = _safe_scalar(row[value_col])
        return out

    # Tolerancia a un formato horizontal sencillo de una sola fila.
    if len(df) >= 1:
        row = df.iloc[0]
        return {str(col): _safe_scalar(row[col]) for col in df.columns if not pd.isna(row[col])}
    return {}


def load_scene_excel(filepath: str | Path) -> SceneWorkbook:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(path)
    with pd.ExcelFile(path) as xls:
        trees = _prepare_trees(_read_sheet_or_empty(xls, TREE_COLUMNS, "Árboles", "Arboles", "Trees"))
        structures = _prepare_structures(_read_sheet_or_empty(xls, STRUCTURE_COLUMNS, "Estructuras", "Structures"))
        params = _read_parameters(xls)
    return SceneWorkbook(trees, structures, params)


def extract_parameters(
    vars_dict: Mapping[str, Any],
    *,
    calculation_mode: str = "advanced",
    origin: str = "modelo",
    app: Any = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "formato_version": FORMAT_VERSION,
        "scientific_release": SCIENTIFIC_RELEASE,
        "scientific_schema": SCIENTIFIC_SCHEMA,
        "origen": origin,
        "modo_calculo": calculation_mode,
    }
    reverse = {v: k for k, v in PARAM_TO_VAR.items()}
    for var_key, excel_key in reverse.items():
        if var_key in vars_dict:
            params[excel_key] = _safe_scalar(_value(vars_dict[var_key]))

    if app is not None:
        for attr, key in (
            ("simple_cloudiness", "nubosidad"),
            ("simple_temp_air_c", "simple_temp_air_c"),
            ("simple_rh", "simple_rh_pct"),
            ("simple_country", "simple_country"),
            ("simple_city", "simple_city"),
        ):
            # En modo detallado nubosidad pertenece a vars_dict; no debe ser
            # sobrescrita por el selector del modo simple que puede estar oculto.
            if attr == "simple_cloudiness" and str(calculation_mode).lower() != "simple":
                continue
            if hasattr(app, attr):
                params[key] = _safe_scalar(_value(getattr(app, attr)))

    if extra:
        params.update({str(k): _safe_scalar(v) for k, v in extra.items()})
    return params


def _rows_from_parameters(params: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    preferred_order = [
        "formato_version", "scientific_release", "scientific_schema", "origen", "modo_calculo", "modo_ui_origen", "surface_model_mode",
        "ground_vegetation_fraction", "vegetation_water_availability", "canopy_water_availability",
        "T_amb_base_K", "I_sol_base_W_m2", "T_min_K", "T_max_K",
        "dia_del_ano", "latitud", "longitud", "hora_local",
        "humedad_relativa_pct", "viento", "timezone", "nubosidad",
        "simple_temp_air_c", "simple_rh_pct", "simple_country", "simple_city",
    ]
    keys = [k for k in preferred_order if k in params]
    keys += [k for k in params if k not in keys]
    for key in keys:
        unit, desc = PARAM_METADATA.get(key, ("", ""))
        rows.append({
            "Parametro": key,
            "Valor": _safe_scalar(params[key]),
            "Unidad": unit,
            "Descripcion": desc,
        })
    return rows


def save_scene_excel(
    filepath: str | Path,
    arboles: list[Any],
    estructuras: list[Any],
    vars_dict: Mapping[str, Any],
    *,
    calculation_mode: str = "advanced",
    origin: str = "modelo",
    app: Any = None,
    extra_parameters: Mapping[str, Any] | None = None,
) -> str:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    tree_rows = []
    for a in arboles or []:
        tree_rows.append({
            "X": float(getattr(a, "x", 0.0)),
            "Y": float(getattr(a, "y", 0.0)),
            "Altura (m)": float(getattr(a, "h", getattr(a, "altura", 0.0))),
            "Densidad_copa (0-1)": float(getattr(a, "rho_copa", 0.0)),
            "Radio_copa (m)": float(getattr(a, "radio_copa", 0.0)),
            "Especie": str(getattr(a, "especie", "") or ""),
            "Forma_copa": normalize_canopy_shape(getattr(a, "forma_copa", DEFAULT_CANOPY_SHAPE)),
        })
    df_arboles = pd.DataFrame(tree_rows, columns=TREE_COLUMNS)

    structure_rows = []
    for e in estructuras or []:
        structure_rows.append({
            "Tipo": str(getattr(e, "tipo", "Pared") or "Pared"),
            "X_inicial": float(getattr(e, "x1", 0.0)),
            "Y_inicial": float(getattr(e, "y1", 0.0)),
            "X_final": float(getattr(e, "x2", 0.0)),
            "Y_final": float(getattr(e, "y2", 0.0)),
            "Altura (m)": float(getattr(e, "altura", 0.0)),
            "Opacidad (0-1)": float(getattr(e, "opacidad", 1.0)),
            "Material": str(getattr(e, "material", "suelo") or "suelo"),
        })
    df_estructuras = pd.DataFrame(structure_rows, columns=STRUCTURE_COLUMNS)

    params = extract_parameters(
        vars_dict,
        calculation_mode=calculation_mode,
        origin=origin,
        app=app,
        extra=extra_parameters,
    )
    df_params = pd.DataFrame(_rows_from_parameters(params), columns=PARAM_COLUMNS)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_arboles.to_excel(writer, sheet_name="Árboles", index=False)
        df_estructuras.to_excel(writer, sheet_name="Estructuras", index=False)
        df_params.to_excel(writer, sheet_name="Parametros", index=False)

    return str(path)


def _coerce_for_var(current: Any, value: Any) -> Any:
    if value == "" or value is None:
        return value
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "si", "sí", "yes"}
        return bool(value)
    if isinstance(current, int) and not isinstance(current, bool):
        return int(round(float(value)))
    if isinstance(current, float):
        return float(value)
    return str(value) if isinstance(current, str) else value


def apply_parameters_to_vars(vars_dict: Mapping[str, Any], params: Mapping[str, Any]) -> None:
    """Aplica parámetros conocidos sin tocar objetos de escena ni metadatos."""
    for excel_key, var_key in PARAM_TO_VAR.items():
        if excel_key not in params or var_key not in vars_dict:
            continue
        target = vars_dict[var_key]
        value = params[excel_key]
        if hasattr(target, "set"):
            try:
                current = target.get()
                target.set(_coerce_for_var(current, value))
            except Exception:
                target.set(value)
        else:
            try:
                vars_dict[var_key] = value  # type: ignore[index]
            except Exception:
                pass


def numeric_parameter(params: Mapping[str, Any], key: str, default: float | None = None) -> float | None:
    value = params.get(key, default)
    if value in (None, ""):
        return default
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default
