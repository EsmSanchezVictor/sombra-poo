"""Validación del modelo contra mediciones de campo.

Importa una planilla CSV con mediciones (temperatura de globo o Tmrt
medida, temperatura de aire, radiación, viento, opcional hora) y
compara contra la predicción del modelo con métricas estándar:

- RMSE (error cuadrático medio), MAE (error absoluto medio), bias y
  R² (coeficiente de determinación, OLS).

Convención de columnas (acepta variantes):
    tg / globo / temp_globo   -> temperatura de globo (°C)
    ta / temp_aire / aire     -> temperatura del aire (°C)
    tmrt / tmrt_medido        -> Tmrt ya medida (°C, si no hay globo)
    rad / radiacion / ghi     -> radiación efectiva (W/m²)
    v / viento / vel          -> velocidad del viento (m/s)
"""
from __future__ import annotations

import math
import os

import numpy as np

import pandas as pd

from core.thermal_comfort import globo_negro_a_tmrt

COLUMNAS = {
    "tg": ["tg", "globo", "temp_globo", "t_globo"],
    "ta": ["ta", "temp_aire", "aire", "t_aire", "temperatura_aire"],
    "tmrt": ["tmrt", "tmrt_medido", "tmrt_obs"],
    "rad": ["rad", "radiacion", "ghi", "radiacion_wm2", "i_global"],
    "v": ["v", "viento", "vel", "velocidad", "v_ms"],
    "hora": ["hora", "h", "hour"],
}


def _buscar_columna(columnas, rol):
    for candidato in COLUMNAS[rol]:
        if candidato in columnas:
            return candidato
    return None


def leer_csv_mediciones(path: str) -> list[dict]:
    """Lee el CSV y devuelve una lista de mediciones normalizadas:
    {tg, ta, v, rad, tmrt_medido, hora}. Si no viene tmrt_medido pero
    viene tg, se convierte con globo_negro_a_tmrt()."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo: {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    col = {rol: _buscar_columna(df.columns, rol) for rol in COLUMNAS}
    if col["tg"] is None and col["tmrt"] is None:
        raise ValueError("El CSV debe tener 'tg' (temperatura de globo) o 'tmrt' (medida).")
    if col["ta"] is None:
        raise ValueError("El CSV debe tener 'ta' (temperatura del aire).")
    if col["rad"] is None:
        raise ValueError("El CSV debe tener 'rad' (radiación W/m²).")

    filas = []
    for _, row in df.iterrows():
        ta = float(row[col["ta"]])
        rad = float(row[col["rad"]])
        v = float(row[col["v"]]) if col["v"] else 0.5
        if col["tmrt"] is not None and not pd.isna(row[col["tmrt"]]):
            tmrt = float(row[col["tmrt"]])
            tg = None
        elif col["tg"] is not None and not pd.isna(row[col["tg"]]):
            tg = float(row[col["tg"]])
            tmrt = globo_negro_a_tmrt(tg, ta, v)
        else:
            continue
        hora = float(row[col["hora"]]) if col["hora"] and not pd.isna(row[col["hora"]]) else None
        filas.append({"tg": tg, "ta": ta, "v": v, "rad": rad,
                      "tmrt_medido": tmrt, "hora": hora})
    if not filas:
        raise ValueError("El CSV no tiene filas con datos utilizables.")
    return filas


def metricas(observado, predicho) -> dict:
    """Métricas de validación. observado/predicho: secuencias del mismo
    largo con al menos 2 puntos."""
    obs = np.asarray(observado, dtype=float)
    pred = np.asarray(predicho, dtype=float)
    if obs.shape != pred.shape or obs.size < 2:
        raise ValueError("Se necesitan al menos 2 pares observado/predicho.")
    n = obs.size
    rmse = float(np.sqrt(np.mean((obs - pred) ** 2)))
    mae = float(np.mean(np.abs(obs - pred)))
    bias = float(np.mean(pred - obs))
    ss_res = float(np.sum((obs - pred) ** 2))
    ss_tot = float(np.sum((obs - np.mean(obs)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return {"n": n, "rmse": round(rmse, 3), "mae": round(mae, 3),
            "bias": round(bias, 3), "r2": round(r2, 3)}


def k_factor_desde_mediciones(filas: list[dict]) -> dict:
    """Ajusta k_factor por mínimos cuadrados forzado por el origen
    (físicamente: ΔT = 0 cuando rad = 0):

        k = Σ(ΔT_i · rad_i) / Σ(rad_i²)

    Devuelve k, R² (de la regresión ΔT vs k·rad) y RMSE en °C."""
    if not filas:
        raise ValueError("No hay mediciones para calibrar.")
    dts = np.array([f["tmrt_medido"] - f["ta"] for f in filas], dtype=float)
    rads = np.array([f["rad"] for f in filas], dtype=float)
    if np.any(rads <= 0):
        raise ValueError("Todas las mediciones necesitan radiación > 0 W/m².")
    k = float(np.sum(dts * rads) / np.sum(rads ** 2))
    pred = k * rads
    ss_res = float(np.sum((dts - pred) ** 2))
    ss_tot = float(np.sum((dts - np.mean(dts)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    rmse = float(np.sqrt(np.mean((dts - pred) ** 2)))
    return {"k_factor": round(k, 6), "r2": round(r2, 3),
            "rmse": round(rmse, 3), "n": len(filas),
            "k_individuales": [round(float(dt / r), 6) for dt, r in zip(dts, rads)]}