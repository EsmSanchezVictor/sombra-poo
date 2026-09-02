"""Calibración y validación científica de los modelos térmicos.

La aplicación mantiene dos familias de Tmrt:

* Estándar: ``Tmrt = Ta + k * GHI * tau``.
* Avanzado v1: balance radiativo humano simplificado (GHI/DNI/DHI).

Este módulo permite comparar ambos modelos contra mediciones de campo sin
mezclar calibración y validación. Si el CSV contiene una columna ``conjunto``
(calibracion / validacion), se respeta esa partición. Si no existe, se genera
un *holdout* interno reproducible; se etiqueta explícitamente como validación
interna, porque no reemplaza una validación independiente de campaña.

Formato flexible de entrada
----------------------------
Obligatorios:
    ta + (tmrt o tg) + ghi/rad

Recomendados:
    sombra_pct, hora, fecha, lat, lon, timezone, viento, dni, dhi,
    elevacion_solar, ta_local, tipo_sombra, tau_sombra_total, conjunto.

Si no existe ``tmrt`` pero sí ``tg``, se convierte temperatura de globo a
Tmrt mediante la ecuación disponible en ``core.thermal_comfort``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time
import math
import os
import unicodedata
import zoneinfo
from typing import Any

import numpy as np
import pandas as pd

from core.radiative_tmrt import calculate_radiative_tmrt
from core.thermal_comfort import globo_negro_a_tmrt


# ---------------------------------------------------------------------------
# Esquema y aliases

COLUMNAS = {
    "tg": ["tg", "globo", "temp_globo", "t_globo", "temperatura_globo"],
    "globe_diameter_m": ["globe_diameter_m", "diametro_globo_m", "diametro_globo", "globe_diameter", "diametro_m"],
    "globe_emissivity": ["globe_emissivity", "emisividad_globo", "epsilon_globo", "emissivity_globe"],
    "ta": ["ta", "temp_aire", "aire", "t_aire", "temperatura_aire", "ta_ref"],
    "tmrt": ["tmrt", "tmrt_medido", "tmrt_obs", "tmrt_observada"],
    "rad": ["rad", "radiacion", "ghi", "radiacion_wm2", "i_global", "ghi_wm2"],
    "dni": ["dni", "dni_wm2", "radiacion_directa_normal"],
    "dhi": ["dhi", "dhi_wm2", "radiacion_difusa_horizontal"],
    "v": ["v", "viento", "vel", "velocidad", "v_ms", "viento_ms"],
    "rh": ["rh", "hr", "humedad", "humedad_relativa", "humedad_pct"],
    "hora": ["hora", "h", "hour", "hora_local"],
    "fecha": ["fecha", "date", "dia_fecha"],
    "lat": ["lat", "latitud", "latitude"],
    "lon": ["lon", "long", "longitud", "longitude"],
    "timezone": ["timezone", "tz", "zona_horaria", "huso_nombre"],
    "tz_offset": ["tz_offset", "utc_offset", "huso", "huso_horas"],
    "elevacion": ["elevacion_solar", "solar_elevation", "elevation", "altura_solar"],
    "sombra_pct": [
        "sombra_pct", "sombra", "porcentaje_sombra", "cobertura_sombra",
        "indice_sombra", "shadow_pct",
    ],
    "tau": ["tau", "transmitancia_efectiva", "tau_efectiva"],
    "tau_sombra_total": [
        "tau_sombra_total", "transmitancia_sombra", "transmitancia_copa",
        "full_shadow_tau",
    ],
    "tipo_sombra": ["tipo_sombra", "shadow_type", "tipo"],
    "ta_local": [
        "ta_local", "ta_bajo_sombra", "temp_aire_local", "temperatura_aire_local",
        "ta_copa", "ta_sombra",
    ],
    "conjunto": ["conjunto", "subset", "grupo", "set", "particion"],
    "id": ["id", "muestra", "sample", "codigo", "identificador"],
    "especie": ["especie", "species", "arbol", "especie_arbol"],
    "surface_temp": ["surface_temp", "surface_temp_c", "ts", "temp_superficie", "temperatura_superficie"],
    "surface_type": ["surface_type", "tipo_superficie", "superficie", "material_superficie"],
    "soil_water": ["soil_water", "soil_water_fraction", "humedad_suelo", "disponibilidad_hidrica", "water_availability"],
}

PLANTILLA_COLUMNAS = [
    "id", "conjunto", "fecha", "hora", "lat", "lon", "timezone",
    "ta", "rh", "viento", "ghi", "dni", "dhi", "elevacion_solar",
    "sombra_pct", "tipo_sombra", "tau_sombra_total", "tmrt", "tg",
    "globe_diameter_m", "globe_emissivity", "ta_local", "especie",
    "surface_temp_c", "surface_type", "soil_water_fraction",
]


@dataclass
class DatasetSplit:
    calibracion: list[dict]
    validacion: list[dict]
    fuente: str
    advertencia: str | None = None


def _normalizar_nombre(value: Any) -> str:
    txt = str(value).strip().lower()
    txt = "".join(
        ch for ch in unicodedata.normalize("NFKD", txt)
        if not unicodedata.combining(ch)
    )
    for old in (" ", "-", "/", "(", ")", "%", "."):
        txt = txt.replace(old, "_")
    while "__" in txt:
        txt = txt.replace("__", "_")
    return txt.strip("_")


def _buscar_columna(columnas, rol):
    normalizadas = {_normalizar_nombre(c): c for c in columnas}
    for candidato in COLUMNAS[rol]:
        key = _normalizar_nombre(candidato)
        if key in normalizadas:
            return normalizadas[key]
    return None


def _float_or_none(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _string_or_none(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    txt = str(value).strip()
    return txt or None


def _parse_fecha(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    txt = str(value).strip()
    if not txt:
        return None
    try:
        # dayfirst=True cubre el uso habitual argentino; ISO sigue siendo inequívoco.
        parsed = pd.to_datetime(txt, dayfirst=True, errors="raise")
        return parsed.date()
    except Exception:
        return None


def _parse_hora(value) -> float | None:
    val = _float_or_none(value)
    if val is not None:
        return val if 0.0 <= val < 24.0 else None
    if value is None or pd.isna(value):
        return None
    txt = str(value).strip()
    if not txt:
        return None
    try:
        parts = txt.split(":")
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        ss = int(parts[2]) if len(parts) > 2 else 0
        out = hh + mm / 60.0 + ss / 3600.0
        return out if 0.0 <= out < 24.0 else None
    except Exception:
        return None


def _normalizar_conjunto(value: str | None) -> str | None:
    if not value:
        return None
    v = _normalizar_nombre(value)
    if v in {"cal", "calibracion", "calibration", "train", "entrenamiento", "ajuste"}:
        return "calibracion"
    if v in {"val", "validacion", "validation", "test", "prueba", "holdout"}:
        return "validacion"
    return None


def _normalizar_tipo_sombra(value: str | None) -> str:
    v = _normalizar_nombre(value or "tree")
    if v in {"estructura", "structure", "techo", "galeria", "pared"}:
        return "structure"
    return "tree"


def guardar_plantilla_csv(path: str) -> str:
    """Crea una plantilla de campaña con encabezados y sin datos inventados."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pd.DataFrame(columns=PLANTILLA_COLUMNAS).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def leer_csv_mediciones(path: str) -> list[dict]:
    """Lee y normaliza mediciones de campo.

    La función conserva las claves históricas ``tg, ta, v, rad,
    tmrt_medido, hora`` y agrega metadatos necesarios para la validación v10.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo: {path}")

    try:
        # sep=None permite CSV con coma o punto y coma. Los decimales con coma
        # se convierten después por _float_or_none.
        df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1")

    if df.empty:
        raise ValueError("El CSV está vacío.")

    col = {rol: _buscar_columna(df.columns, rol) for rol in COLUMNAS}
    if col["tg"] is None and col["tmrt"] is None:
        raise ValueError("El CSV debe tener 'tg' (temperatura de globo) o 'tmrt' observada.")
    if col["ta"] is None:
        raise ValueError("El CSV debe tener 'ta' (temperatura del aire de referencia).")
    if col["rad"] is None:
        raise ValueError("El CSV debe tener 'ghi' o 'rad' (radiación global W/m²).")

    filas: list[dict] = []
    for idx, row in df.iterrows():
        ta = _float_or_none(row[col["ta"]])
        rad = _float_or_none(row[col["rad"]])
        if ta is None or rad is None or rad < 0:
            continue

        v = _float_or_none(row[col["v"]]) if col["v"] else None
        v_usado = 0.5 if v is None else max(0.0, v)
        tmrt_directa = _float_or_none(row[col["tmrt"]]) if col["tmrt"] else None
        tg = _float_or_none(row[col["tg"]]) if col["tg"] else None
        globe_diameter = (
            _float_or_none(row[col["globe_diameter_m"]])
            if col.get("globe_diameter_m") else None
        )
        globe_emissivity = (
            _float_or_none(row[col["globe_emissivity"]])
            if col.get("globe_emissivity") else None
        )
        diameter_used = 0.15 if globe_diameter is None else globe_diameter
        emissivity_used = 0.97 if globe_emissivity is None else globe_emissivity
        if diameter_used <= 0 or not (0.0 < emissivity_used <= 1.0):
            continue

        if tmrt_directa is not None:
            tmrt = tmrt_directa
            fuente_tmrt = "tmrt_observada"
        elif tg is not None:
            tmrt = float(globo_negro_a_tmrt(
                tg, ta, v_usado, diametro=diameter_used, emisividad=emissivity_used
            ))
            fuente_tmrt = "globo_convertido"
        else:
            continue

        sombra_pct = _float_or_none(row[col["sombra_pct"]]) if col["sombra_pct"] else None
        tau = _float_or_none(row[col["tau"]]) if col["tau"] else None
        tau_total = (
            _float_or_none(row[col["tau_sombra_total"]])
            if col["tau_sombra_total"] else None
        )
        tipo = _normalizar_tipo_sombra(
            _string_or_none(row[col["tipo_sombra"]]) if col["tipo_sombra"] else None
        )

        fila = {
            "row_index": int(idx),
            "id": _string_or_none(row[col["id"]]) if col["id"] else str(idx + 1),
            "tg": tg,
            "globe_diameter_m": float(diameter_used),
            "globe_emissivity": float(emissivity_used),
            "globe_geometry_default": bool(globe_diameter is None or globe_emissivity is None),
            "ta": float(ta),
            "v": float(v_usado),
            "v_fue_default": v is None,
            "rh": _float_or_none(row[col["rh"]]) if col["rh"] else None,
            "rad": float(rad),
            "dni": _float_or_none(row[col["dni"]]) if col["dni"] else None,
            "dhi": _float_or_none(row[col["dhi"]]) if col["dhi"] else None,
            "tmrt_medido": float(tmrt),
            "fuente_tmrt": fuente_tmrt,
            "hora": _parse_hora(row[col["hora"]]) if col["hora"] else None,
            "fecha": _parse_fecha(row[col["fecha"]]) if col["fecha"] else None,
            "lat": _float_or_none(row[col["lat"]]) if col["lat"] else None,
            "lon": _float_or_none(row[col["lon"]]) if col["lon"] else None,
            "timezone": _string_or_none(row[col["timezone"]]) if col["timezone"] else None,
            "tz_offset": _float_or_none(row[col["tz_offset"]]) if col["tz_offset"] else None,
            "elevacion": _float_or_none(row[col["elevacion"]]) if col["elevacion"] else None,
            "sombra_pct": sombra_pct,
            "tau": tau,
            "tau_sombra_total": tau_total,
            "tipo_sombra": tipo,
            "ta_local": _float_or_none(row[col["ta_local"]]) if col["ta_local"] else None,
            "conjunto": _normalizar_conjunto(
                _string_or_none(row[col["conjunto"]]) if col["conjunto"] else None
            ),
            "especie": _string_or_none(row[col["especie"]]) if col["especie"] else None,
            "surface_temp_c": _float_or_none(row[col["surface_temp"]]) if col.get("surface_temp") else None,
            "surface_type": _string_or_none(row[col["surface_type"]]) if col.get("surface_type") else None,
            "soil_water_fraction": _float_or_none(row[col["soil_water"]]) if col.get("soil_water") else None,
        }
        filas.append(fila)

    if not filas:
        raise ValueError("El CSV no tiene filas con datos utilizables.")
    return filas


# ---------------------------------------------------------------------------
# Métricas y partición


def metricas(observado, predicho) -> dict:
    """MAE, RMSE, sesgo y R²; ignora pares no finitos."""
    obs = np.asarray(observado, dtype=float)
    pred = np.asarray(predicho, dtype=float)
    if obs.shape != pred.shape:
        raise ValueError("observado y predicho deben tener la misma forma.")
    mask = np.isfinite(obs) & np.isfinite(pred)
    obs = obs[mask]
    pred = pred[mask]
    if obs.size < 2:
        raise ValueError("Se necesitan al menos 2 pares observado/predicho válidos.")
    n = int(obs.size)
    error = pred - obs
    rmse = float(np.sqrt(np.mean(error ** 2)))
    mae = float(np.mean(np.abs(error)))
    bias = float(np.mean(error))
    ss_res = float(np.sum(error ** 2))
    ss_tot = float(np.sum((obs - np.mean(obs)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return {
        "n": n,
        "rmse": round(rmse, 3),
        "mae": round(mae, 3),
        "bias": round(bias, 3),
        "r2": round(r2, 3),
    }


def particionar_mediciones(
    filas: list[dict],
    validation_fraction: float = 0.30,
    seed: int = 42,
) -> DatasetSplit:
    """Separa calibración y validación sin mezclar resultados.

    Prioridad:
    1. Si el CSV contiene ambos grupos explícitos, se respetan.
    2. Con >=5 filas se crea un holdout interno reproducible.
    3. Con menos datos se usan todas las filas en ambos grupos y se advierte
       que NO existe validación independiente.
    """
    if not filas:
        raise ValueError("No hay mediciones para particionar.")

    cal_exp = [f for f in filas if f.get("conjunto") == "calibracion"]
    val_exp = [f for f in filas if f.get("conjunto") == "validacion"]
    if len(cal_exp) >= 2 and len(val_exp) >= 2:
        return DatasetSplit(
            calibracion=cal_exp,
            validacion=val_exp,
            fuente="partición explícita del CSV",
            advertencia=None,
        )

    n = len(filas)
    frac = float(np.clip(validation_fraction, 0.10, 0.50))
    if n >= 5:
        rng = np.random.default_rng(int(seed))
        indices = rng.permutation(n)
        n_val = max(2, int(round(n * frac)))
        n_val = min(n_val, n - 2)
        val_idx = set(int(i) for i in indices[:n_val])
        calibracion = [f for i, f in enumerate(filas) if i not in val_idx]
        validacion = [f for i, f in enumerate(filas) if i in val_idx]
        return DatasetSplit(
            calibracion=calibracion,
            validacion=validacion,
            fuente=f"holdout interno reproducible ({len(calibracion)}/{len(validacion)}, seed={int(seed)})",
            advertencia=(
                "La validación es interna al mismo CSV. Para evidencia científica fuerte, "
                "use una campaña o subconjunto independiente etiquetado como 'validacion'."
            ),
        )

    return DatasetSplit(
        calibracion=list(filas),
        validacion=list(filas),
        fuente="sin partición independiente (n pequeño)",
        advertencia=(
            "Hay menos de 5 mediciones: calibración y evaluación usan los mismos datos. "
            "Las métricas son diagnósticas, no una validación independiente."
        ),
    )


# ---------------------------------------------------------------------------
# Predictores y calibración


def _tau_efectiva(fila: dict) -> float:
    tau = fila.get("tau")
    if tau is not None and math.isfinite(float(tau)):
        return float(np.clip(float(tau), 0.0, 1.0))
    tipo = _normalizar_tipo_sombra(fila.get("tipo_sombra"))
    tau_total = fila.get("tau_sombra_total")
    if tau_total is None:
        tau_total = 0.15 if tipo == "tree" else 0.05
    tau_total = float(np.clip(float(tau_total), 0.0, 1.0))
    sombra = fila.get("sombra_pct")
    s = 0.0 if sombra is None else float(np.clip(float(sombra) / 100.0, 0.0, 1.0))
    return 1.0 - s * (1.0 - tau_total)


def _offset_timezone(fila: dict, fecha_local: date | None, hora: float | None) -> float | None:
    explicit = fila.get("tz_offset")
    if explicit is not None:
        return float(explicit)
    tz = fila.get("timezone")
    if tz and fecha_local is not None:
        try:
            hh = int(hora or 12.0)
            mm = int(round(((hora or 12.0) - hh) * 60.0))
            dt = datetime.combine(fecha_local, time(hh % 24, mm % 60))
            local = dt.replace(tzinfo=zoneinfo.ZoneInfo(str(tz)))
            off = local.utcoffset()
            if off is not None:
                return float(off.total_seconds() / 3600.0)
        except Exception:
            pass
    lon = fila.get("lon")
    if lon is not None:
        # Último recurso; se marca como aproximación en el reporte.
        return float(np.clip(np.round(float(lon) / 15.0), -12, 14))
    return None


def _elevacion_solar(fila: dict, defaults: dict | None = None) -> tuple[float | None, str]:
    elev = fila.get("elevacion")
    if elev is not None:
        return float(elev), "observada/provista"

    defaults = defaults or {}
    fecha_local = fila.get("fecha") or defaults.get("fecha")
    hora = fila.get("hora")
    if hora is None:
        hora = defaults.get("hora")
    lat = fila.get("lat")
    lon = fila.get("lon")
    if lat is None:
        lat = defaults.get("lat")
    if lon is None:
        lon = defaults.get("lon")
    if fecha_local is None or hora is None or lat is None or lon is None:
        return None, "faltante"

    aux = dict(fila)
    if not aux.get("timezone") and defaults.get("timezone"):
        aux["timezone"] = defaults.get("timezone")
    if aux.get("tz_offset") is None and defaults.get("tz_offset") is not None:
        aux["tz_offset"] = defaults.get("tz_offset")
    offset = _offset_timezone(aux, fecha_local, float(hora))
    try:
        # Import local para evitar acoplamiento circular en el arranque.
        from shadow_temp import Temperatura

        calc = Temperatura(
            latitude=float(lat), longitude=float(lon), tz_offset_hours=offset,
        )
        day = fecha_local.timetuple().tm_yday
        return float(calc.solar_altitude(day, float(hora))), "calculada"
    except Exception:
        return None, "faltante"


def predecir_estandar(fila: dict, k_factor: float) -> float:
    tau = _tau_efectiva(fila)
    return float(fila["ta"] + float(k_factor) * float(fila["rad"]) * tau)


def predecir_avanzado(fila: dict, defaults: dict | None = None) -> tuple[float, dict]:
    elev, fuente_elev = _elevacion_solar(fila, defaults)
    if elev is None:
        return float("nan"), {
            "estado": "sin elevación solar",
            "fuente_elevacion": fuente_elev,
            "componentes": "no calculado",
        }
    tau = _tau_efectiva(fila)
    dni = fila.get("dni")
    dhi = fila.get("dhi")
    result = calculate_radiative_tmrt(
        float(fila["ta"]), tau, float(fila["rad"]), float(elev),
        dni=dni, dhi=dhi,
    )
    comp = "observados" if dni is not None and dhi is not None else "estimados por cierre radiativo"
    return float(result["tmrt_c"]), {
        "estado": "ok",
        "fuente_elevacion": fuente_elev,
        "componentes": comp,
        "elevacion": float(elev),
        "dni_usado": float(result["dni"]),
        "dhi_usado": float(result["dhi"]),
    }


def calibrar_modelo_estandar(filas: list[dict]) -> dict:
    """Ajusta k con radiación efectiva ``GHI*tau`` y agrega diagnóstico OLS.

    El parámetro que puede aplicarse al modelo sigue siendo el ajuste físico
    forzado por el origen. También se informa una regresión libre
    ``ΔTmrt = b + k*x`` como diagnóstico de sesgo estructural; no se aplica
    automáticamente al modelo estándar.
    """
    xs, ys = [], []
    for f in filas:
        x = float(f["rad"]) * _tau_efectiva(f)
        y = float(f["tmrt_medido"] - f["ta"])
        if math.isfinite(x) and math.isfinite(y) and x > 1e-9:
            xs.append(x)
            ys.append(y)
    if len(xs) < 2:
        raise ValueError("Se necesitan al menos 2 mediciones con radiación efectiva > 0 para calibrar k.")
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    denom = float(np.sum(x ** 2))
    if denom <= 1e-12:
        raise ValueError("La radiación efectiva no tiene variación suficiente para calibrar.")
    k0 = float(np.sum(x * y) / denom)
    pred0 = k0 * x
    met0 = metricas(y, pred0)

    A = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    intercepto = float(beta[0])
    k_libre = float(beta[1])
    pred_libre = intercepto + k_libre * x
    met_libre = metricas(y, pred_libre)
    return {
        "k_factor": round(k0, 8),
        "n": len(x),
        "metricas_forzado": met0,
        "diagnostico_intercepto_c": round(intercepto, 4),
        "diagnostico_k_libre": round(k_libre, 8),
        "metricas_libre": met_libre,
        "aplicable": bool(math.isfinite(k0) and k0 > 0.0),
    }


def k_factor_desde_mediciones(filas: list[dict]) -> dict:
    """Compatibilidad con el calibrador histórico.

    Desde v10 respeta sombra/transmitancia cuando están disponibles. Para CSV
    antiguos sin esos campos, ``tau=1`` y reproduce el comportamiento previo.
    """
    ajuste = calibrar_modelo_estandar(filas)
    # Mantener claves esperadas por diálogos/tests previos.
    return {
        "k_factor": round(float(ajuste["k_factor"]), 6),
        "r2": ajuste["metricas_forzado"]["r2"],
        "rmse": ajuste["metricas_forzado"]["rmse"],
        "n": ajuste["n"],
        "k_individuales": [
            round(
                float((f["tmrt_medido"] - f["ta"]) / (f["rad"] * _tau_efectiva(f))),
                6,
            )
            for f in filas
            if f.get("rad", 0) > 0 and f["rad"] * _tau_efectiva(f) > 0
        ],
    }


def _ajustar_coeficiente_aire_tipo(
    filas: list[dict],
    tipo: str,
    max_cooling: float,
) -> dict | None:
    xs, obs = [], []
    for f in filas:
        if _normalizar_tipo_sombra(f.get("tipo_sombra")) != tipo:
            continue
        ta_local = f.get("ta_local")
        if ta_local is None:
            continue
        x = float(f["rad"]) * max(0.0, 1.0 - _tau_efectiva(f))
        if x <= 1e-9:
            continue
        xs.append(x)
        obs.append(float(f["ta"] - ta_local))
    if len(xs) < 3:
        return None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(obs, dtype=float)
    # 0..0.02 K/(W/m²) cubre desde ausencia de enfriamiento hasta una
    # respuesta deliberadamente muy superior a los defaults actuales.
    grid = np.linspace(0.0, 0.02, 4001)
    # vectorización: filas x candidatos
    pred = np.minimum(float(max_cooling), x[:, None] * grid[None, :])
    rmse = np.sqrt(np.mean((pred - y[:, None]) ** 2, axis=0))
    best = int(np.argmin(rmse))
    coefficient = float(grid[best])
    pred_best = np.minimum(float(max_cooling), coefficient * x)
    met = metricas(y, pred_best)
    return {
        "tipo": tipo,
        "coefficient": round(coefficient, 8),
        "max_cooling": float(max_cooling),
        "n": len(x),
        "metricas": met,
        "aplicable": coefficient >= 0.0,
    }


def calibrar_aire_local_por_tipo(filas: list[dict]) -> dict[str, dict]:
    """Calibra el coeficiente de Ta local con el tope térmico actual fijo."""
    resultados = {}
    tree = _ajustar_coeficiente_aire_tipo(filas, "tree", 2.5)
    structure = _ajustar_coeficiente_aire_tipo(filas, "structure", 1.2)
    if tree:
        resultados["tree"] = tree
    if structure:
        resultados["structure"] = structure
    return resultados


def _predecir_aire_local(fila: dict, coefficient: float, max_cooling: float) -> float:
    avoided = float(fila["rad"]) * max(0.0, 1.0 - _tau_efectiva(fila))
    delta = min(float(max_cooling), max(0.0, float(coefficient)) * avoided)
    return float(fila["ta"] - delta)


# ---------------------------------------------------------------------------
# Evaluación integral


def evaluar_modelos(
    filas: list[dict],
    *,
    k_actual: float = 0.04,
    validation_fraction: float = 0.30,
    seed: int = 42,
    defaults: dict | None = None,
) -> dict:
    """Calibra en un subconjunto y evalúa en otro.

    Devuelve métricas comparables del estándar actual, estándar calibrado y
    avanzado v1. El avanzado puede tener ``n`` menor si faltan datos para
    obtener elevación solar; esa limitación se reporta explícitamente.
    """
    split = particionar_mediciones(filas, validation_fraction, seed)
    ajuste_k = calibrar_modelo_estandar(split.calibracion)
    k_cal = float(ajuste_k["k_factor"])
    aire_cal = calibrar_aire_local_por_tipo(split.calibracion)

    resultados_fila = []
    for grupo, grupo_filas in (("calibracion", split.calibracion), ("validacion", split.validacion)):
        for f in grupo_filas:
            pred_actual = predecir_estandar(f, k_actual)
            pred_cal = predecir_estandar(f, k_cal)
            pred_adv, meta_adv = predecir_avanzado(f, defaults=defaults)
            tipo = _normalizar_tipo_sombra(f.get("tipo_sombra"))
            aire_fit = aire_cal.get(tipo)
            ta_local_pred = None
            if aire_fit is not None:
                ta_local_pred = _predecir_aire_local(
                    f, aire_fit["coefficient"], aire_fit["max_cooling"]
                )
            resultados_fila.append({
                **f,
                "grupo_evaluacion": grupo,
                "tau_efectiva": _tau_efectiva(f),
                "pred_estandar_actual": pred_actual,
                "pred_estandar_calibrado": pred_cal,
                "pred_avanzado_v1": pred_adv,
                "advanced_meta": meta_adv,
                "pred_ta_local_calibrada": ta_local_pred,
            })

    valid_rows = [r for r in resultados_fila if r["grupo_evaluacion"] == "validacion"]
    obs = np.asarray([r["tmrt_medido"] for r in valid_rows], dtype=float)

    def _met_for(key: str):
        pred = np.asarray([r[key] for r in valid_rows], dtype=float)
        try:
            return metricas(obs, pred)
        except ValueError:
            return None

    metricas_modelos = {
        "Estándar actual": _met_for("pred_estandar_actual"),
        "Estándar calibrado": _met_for("pred_estandar_calibrado"),
        "Avanzado v1": _met_for("pred_avanzado_v1"),
    }

    metricas_aire = {}
    for tipo, fit in aire_cal.items():
        pares = [
            r for r in valid_rows
            if _normalizar_tipo_sombra(r.get("tipo_sombra")) == tipo
            and r.get("ta_local") is not None
            and r.get("pred_ta_local_calibrada") is not None
        ]
        if len(pares) >= 2:
            metricas_aire[tipo] = metricas(
                [r["ta_local"] for r in pares],
                [r["pred_ta_local_calibrada"] for r in pares],
            )
        else:
            metricas_aire[tipo] = None

    advertencias: list[str] = []
    if split.advertencia:
        advertencias.append(split.advertencia)
    if any(f.get("sombra_pct") is None and f.get("tau") is None for f in filas):
        advertencias.append(
            "Hay filas sin sombra/tau: se asumió pleno sol (tau=1) en esas observaciones."
        )
    if any(f.get("v_fue_default") and f.get("fuente_tmrt") == "globo_convertido" for f in filas):
        advertencias.append(
            "Algunas conversiones de globo usaron viento por defecto 0.5 m/s por faltar la medición."
        )
    if any(f.get("globe_geometry_default") and f.get("fuente_tmrt") == "globo_convertido" for f in filas):
        advertencias.append(
            "Algunas conversiones de globo usaron diámetro 0.15 m y/o emisividad 0.97 por defecto. "
            "Para validación metrológica cargue las especificaciones reales del instrumento."
        )
    adv_no_calc = sum(not math.isfinite(float(r["pred_avanzado_v1"])) for r in valid_rows)
    if adv_no_calc:
        advertencias.append(
            f"El modelo Avanzado no pudo evaluarse en {adv_no_calc} filas de validación por faltar "
            "elevación solar o fecha/hora/ubicación suficientes."
        )
    componentes_estimados = sum(
        r["advanced_meta"].get("componentes") == "estimados por cierre radiativo"
        for r in valid_rows
        if math.isfinite(float(r["pred_avanzado_v1"]))
    )
    if componentes_estimados:
        advertencias.append(
            f"En {componentes_estimados} filas del Avanzado faltó DNI y/o DHI; se estimaron componentes "
            "a partir de GHI."
        )

    return {
        "split": split,
        "ajuste_k": ajuste_k,
        "ajuste_aire_local": aire_cal,
        "metricas_modelos": metricas_modelos,
        "metricas_aire_local": metricas_aire,
        "filas": resultados_fila,
        "advertencias": advertencias,
        "k_actual": float(k_actual),
        "k_calibrado": k_cal,
        "defaults": defaults or {},
    }


def dataframe_resultados(reporte: dict) -> pd.DataFrame:
    """Tabla plana para auditoría/exportación."""
    rows = []
    for r in reporte["filas"]:
        meta = r.get("advanced_meta") or {}
        rows.append({
            "id": r.get("id"),
            "conjunto": r.get("grupo_evaluacion"),
            "fecha": r.get("fecha"),
            "hora": r.get("hora"),
            "ta_c": r.get("ta"),
            "tmrt_observada_c": r.get("tmrt_medido"),
            "fuente_tmrt": r.get("fuente_tmrt"),
            "globe_diameter_m": r.get("globe_diameter_m"),
            "globe_emissivity": r.get("globe_emissivity"),
            "ghi_wm2": r.get("rad"),
            "dni_wm2": r.get("dni"),
            "dhi_wm2": r.get("dhi"),
            "sombra_pct": r.get("sombra_pct"),
            "tau_efectiva": r.get("tau_efectiva"),
            "tmrt_estandar_actual_c": r.get("pred_estandar_actual"),
            "tmrt_estandar_calibrado_c": r.get("pred_estandar_calibrado"),
            "tmrt_avanzado_v1_c": r.get("pred_avanzado_v1"),
            "elevacion_solar_usada_deg": meta.get("elevacion"),
            "fuente_elevacion": meta.get("fuente_elevacion"),
            "componentes_avanzado": meta.get("componentes"),
            "ta_local_observada_c": r.get("ta_local"),
            "ta_local_modelada_c": r.get("pred_ta_local_calibrada"),
            "tipo_sombra": r.get("tipo_sombra"),
            "especie": r.get("especie"),
            "surface_temp_observada_c": r.get("surface_temp_c"),
            "surface_type": r.get("surface_type"),
            "soil_water_fraction": r.get("soil_water_fraction"),
        })
    return pd.DataFrame(rows)


def exportar_reporte_validacion(path: str, reporte: dict) -> str:
    """Exporta resultados, métricas, calibración y trazabilidad a XLSX."""
    df_resultados = dataframe_resultados(reporte)
    metric_rows = []
    for model, met in reporte["metricas_modelos"].items():
        metric_rows.append({"modelo": model, **(met or {"n": 0, "rmse": np.nan, "mae": np.nan, "bias": np.nan, "r2": np.nan})})
    df_metricas = pd.DataFrame(metric_rows)

    k = reporte["ajuste_k"]
    cal_rows = [
        {"parametro": "k_actual", "valor": reporte["k_actual"], "nota": "valor usado antes de calibrar"},
        {"parametro": "k_sugerido", "valor": reporte["k_calibrado"], "nota": "ajuste forzado por el origen en conjunto de calibración"},
        {"parametro": "intercepto_diagnostico_c", "valor": k["diagnostico_intercepto_c"], "nota": "solo diagnóstico; no se aplica al estándar"},
        {"parametro": "k_diagnostico_libre", "valor": k["diagnostico_k_libre"], "nota": "pendiente libre de la regresión diagnóstica"},
    ]
    for tipo, fit in reporte["ajuste_aire_local"].items():
        cal_rows += [
            {"parametro": f"ta_local_{tipo}_coefficient", "valor": fit["coefficient"], "nota": "K/(W/m²), calibrado"},
            {"parametro": f"ta_local_{tipo}_max_cooling", "valor": fit["max_cooling"], "nota": "°C, tope fijo durante calibración"},
        ]
    df_cal = pd.DataFrame(cal_rows)

    split = reporte["split"]
    meta_rows = [
        {"campo": "fecha_exportacion", "valor": datetime.now().isoformat(timespec="seconds")},
        {"campo": "particion", "valor": split.fuente},
        {"campo": "n_calibracion", "valor": len(split.calibracion)},
        {"campo": "n_validacion", "valor": len(split.validacion)},
    ]
    for i, warning in enumerate(reporte.get("advertencias", []), start=1):
        meta_rows.append({"campo": f"advertencia_{i}", "valor": warning})
    df_meta = pd.DataFrame(meta_rows)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_resultados.to_excel(writer, index=False, sheet_name="Resultados")
        df_metricas.to_excel(writer, index=False, sheet_name="Metricas")
        df_cal.to_excel(writer, index=False, sheet_name="Calibracion")
        df_meta.to_excel(writer, index=False, sheet_name="Metadatos")
    return path
