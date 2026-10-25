"""Importación y armonización de meteorología observada.

Etapa 6 / v14. Este módulo separa claramente los datos OBSERVADOS de las
estimaciones/modelos. No modifica silenciosamente una medición: los valores
faltantes pueden interpolarse o derivarse y esa procedencia queda marcada.

Formato CSV recomendado (nombres alternativos en español/inglés aceptados):
    timestamp, ghi, dni, dhi, ta_c, rh_pct, wind_m_s

También se acepta fecha + hora en columnas separadas. Los timestamps sin zona
horaria se interpretan en la zona IANA indicada al cargar el archivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import math
import unicodedata

import numpy as np
import pandas as pd
from core.local_time import resolve_local_datetime, LocalTimeError, TIME_POLICY


ALIASES = {
    "timestamp": {"timestamp", "datetime", "fecha_hora", "fechahora", "date_time", "instante"},
    "date": {"fecha", "date", "dia", "day"},
    "time": {"hora", "time", "hour"},
    "ghi": {"ghi", "radiacion", "radiacion_global", "radiacion_global_horizontal", "global_horizontal", "global_horizontal_irradiance"},
    "dni": {"dni", "radiacion_directa_normal", "direct_normal", "direct_normal_irradiance"},
    "dhi": {"dhi", "radiacion_difusa_horizontal", "diffuse_horizontal", "diffuse_horizontal_irradiance"},
    "ta_c": {"ta_c", "ta", "temp_c", "temperatura_c", "temperatura_aire", "temperatura_aire_c", "air_temperature", "air_temp"},
    "rh_pct": {"rh_pct", "rh", "hr", "humedad", "humedad_relativa", "relative_humidity"},
    "wind_m_s": {"wind_m_s", "wind", "viento", "viento_ms", "velocidad_viento", "wind_speed"},
    "cloud_fraction": {"cloud_fraction", "cloud_cover", "nubosidad", "fraccion_nubosidad", "cloudiness", "cloud_pct", "nubosidad_pct"},
}


def _norm(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().lower()
    for char in (" ", "-", "/", "(", ")", "[", "]", "%", "°"):
        text = text.replace(char, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = {_norm(col): col for col in df.columns}
    rename: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases | {canonical}:
            key = _norm(alias)
            if key in normalized:
                rename[normalized[key]] = canonical
                break
    return df.rename(columns=rename)


def _parse_timestamp(df: pd.DataFrame, timezone: str) -> pd.Series:
    if "timestamp" in df.columns:
        raw = df["timestamp"]
    elif "date" in df.columns:
        if "time" in df.columns:
            raw = df["date"].astype(str).str.strip() + " " + df["time"].astype(str).str.strip()
        else:
            raw = df["date"]
    else:
        raise ValueError(
            "La serie meteorológica necesita una columna timestamp/datetime o columnas fecha + hora."
        )

    # Parsear individualmente preserva los offsets distintos de una hora
    # repetida. Convertir primero toda la columna a UTC inventaría una zona
    # para las filas naive. No se mezclan esas dos convenciones en un CSV.
    parsed = []
    for text in raw:
        try:
            ts = pd.Timestamp(text)
        except (ValueError, TypeError):
            ts = pd.NaT
        parsed.append(ts)
    if all(pd.isna(ts) for ts in parsed):
        raise ValueError("No se pudo interpretar ninguna fecha/hora de la serie meteorológica.")
    conventions = {ts.tzinfo is not None for ts in parsed if not pd.isna(ts)}
    if len(conventions) > 1:
        raise ValueError("El CSV mezcla horas con y sin offset. Use una única convención temporal en todas las filas.")
    localized = []
    for row, ts in enumerate(parsed, start=2):
        if pd.isna(ts):
            localized.append(pd.NaT)
            continue
        try:
            localized.append(resolve_local_datetime(ts, timezone))
        except LocalTimeError as exc:
            raise ValueError(f"Fila {row} del CSV: {exc}") from exc
    return pd.Series(pd.DatetimeIndex(localized), index=df.index)


def _numeric_clean(series: pd.Series, *, low: float | None = None, high: float | None = None) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").astype(float)
    if low is not None:
        out = out.where(out >= low)
    if high is not None:
        out = out.where(out <= high)
    return out


@dataclass
class MeteorologicalSample:
    timestamp: pd.Timestamp
    values: dict[str, float | None]
    status: str
    source: str = "observed_series"
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str, default=None):
        value = self.values.get(key, default)
        return default if value is None else value


class MeteorologicalSeries:
    """Serie observada con consulta temporal reproducible.

    La interpolación solo se realiza ENTRE dos observaciones y nunca fuera de
    la cobertura temporal del archivo. ``max_gap_minutes`` impide interpolar
    huecos grandes como si fueran datos continuos.
    """

    VALUE_COLUMNS = ("ghi", "dni", "dhi", "ta_c", "rh_pct", "wind_m_s", "cloud_fraction")

    def __init__(self, data: pd.DataFrame, *, timezone: str, path: str | None = None):
        self.timezone = str(timezone)
        self.path = path
        self.data = data.sort_index()
        if self.data.index.has_duplicates:
            # Promediar duplicados numéricos es explícito y reproducible.
            self.data = self.data.groupby(level=0).mean(numeric_only=True)
        if self.data.empty:
            raise ValueError("La serie meteorológica no contiene observaciones válidas.")

    @classmethod
    def from_csv(cls, path: str | Path, *, timezone: str) -> "MeteorologicalSeries":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, sep=None, engine="python")
        df = _canonical_columns(df)
        timestamp = _parse_timestamp(df, timezone)
        out = pd.DataFrame(index=pd.DatetimeIndex(timestamp))

        if "ghi" in df:
            out["ghi"] = _numeric_clean(df["ghi"], low=0.0, high=1600.0).to_numpy()
        if "dni" in df:
            out["dni"] = _numeric_clean(df["dni"], low=0.0, high=1600.0).to_numpy()
        if "dhi" in df:
            out["dhi"] = _numeric_clean(df["dhi"], low=0.0, high=1600.0).to_numpy()
        if "ta_c" in df:
            out["ta_c"] = _numeric_clean(df["ta_c"], low=-80.0, high=70.0).to_numpy()
        if "rh_pct" in df:
            out["rh_pct"] = _numeric_clean(df["rh_pct"], low=0.0, high=100.0).to_numpy()
        if "wind_m_s" in df:
            out["wind_m_s"] = _numeric_clean(df["wind_m_s"], low=0.0, high=80.0).to_numpy()
        if "cloud_fraction" in df:
            cloud = pd.to_numeric(df["cloud_fraction"], errors="coerce").astype(float)
            # Acepta tanto 0-1 como porcentaje 0-100.
            cloud = cloud.where(cloud <= 1.0, cloud / 100.0)
            out["cloud_fraction"] = cloud.where((cloud >= 0.0) & (cloud <= 1.0)).to_numpy()

        out = out[~out.index.isna()]
        if not any(col in out.columns for col in cls.VALUE_COLUMNS):
            raise ValueError("La serie no contiene columnas meteorológicas reconocidas.")
        return cls(out, timezone=timezone, path=str(path))

    @property
    def start(self) -> pd.Timestamp:
        return self.data.index.min()

    @property
    def end(self) -> pd.Timestamp:
        return self.data.index.max()

    @property
    def n(self) -> int:
        return int(len(self.data))

    @property
    def available_columns(self) -> list[str]:
        return [col for col in self.VALUE_COLUMNS if col in self.data.columns and self.data[col].notna().any()]

    def summary(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "timezone": self.timezone,
            "n": self.n,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "columns": self.available_columns,
            "time_policy": TIME_POLICY,
        }

    def _target(self, dt) -> pd.Timestamp:
        return pd.Timestamp(resolve_local_datetime(pd.Timestamp(dt), self.timezone))

    def sample_at(self, dt, *, max_gap_minutes: float = 90.0) -> MeteorologicalSample | None:
        target = self._target(dt)
        if pd.isna(target) or target < self.start or target > self.end:
            return None

        if target in self.data.index:
            row = self.data.loc[target]
            if isinstance(row, pd.DataFrame):
                row = row.mean(numeric_only=True)
            values = {c: (None if c not in row or pd.isna(row[c]) else float(row[c])) for c in self.VALUE_COLUMNS}
            return MeteorologicalSample(target, values, status="observed")

        pos = int(self.data.index.searchsorted(target))
        if pos <= 0 or pos >= len(self.data):
            return None
        t0 = self.data.index[pos - 1]
        t1 = self.data.index[pos]
        total_minutes = (t1 - t0).total_seconds() / 60.0
        if total_minutes <= 0 or total_minutes > float(max_gap_minutes):
            return None
        f = (target - t0).total_seconds() / (t1 - t0).total_seconds()
        r0 = self.data.iloc[pos - 1]
        r1 = self.data.iloc[pos]
        values: dict[str, float | None] = {}
        warnings: list[str] = []
        for col in self.VALUE_COLUMNS:
            if col not in self.data.columns or pd.isna(r0.get(col)) or pd.isna(r1.get(col)):
                values[col] = None
            else:
                values[col] = float(r0[col] + f * (r1[col] - r0[col]))
        warnings.append(
            f"Valores interpolados linealmente entre {t0.isoformat()} y {t1.isoformat()} ({total_minutes:.0f} min)."
        )
        return MeteorologicalSample(target, values, status="interpolated", warnings=warnings)


def extraterrestrial_normal_wm2(day_of_year: int) -> float:
    n = int(day_of_year)
    return 1367.0 * (1.0 + 0.033 * math.cos(2.0 * math.pi * n / 365.0))


def complete_radiation_components(
    *,
    ghi: float | None,
    dni: float | None,
    dhi: float | None,
    elevation_deg: float,
    day_of_year: int,
) -> dict[str, Any]:
    """Completa GHI/DNI/DHI sin ocultar qué componentes fueron derivadas.

    Si solo hay GHI, se usa la correlación de Erbs para estimar la fracción
    difusa. Si hay dos componentes se deriva la tercera por la identidad
    GHI = DNI*sin(elev) + DHI. Las mediciones suministradas no se reescriben.
    """
    vals = {
        "ghi": None if ghi is None else max(0.0, float(ghi)),
        "dni": None if dni is None else max(0.0, float(dni)),
        "dhi": None if dhi is None else max(0.0, float(dhi)),
    }
    derived: list[str] = []
    warnings: list[str] = []
    s = max(0.0, math.sin(math.radians(float(elevation_deg))))

    supplied = {k for k, v in vals.items() if v is not None}
    if len(supplied) == 3:
        recomposed = vals["dni"] * s + vals["dhi"]
        tol = max(40.0, 0.08 * max(vals["ghi"], 1.0))
        if abs(recomposed - vals["ghi"]) > tol:
            warnings.append(
                f"GHI/DNI/DHI observados no cierran en el plano horizontal: GHI={vals['ghi']:.1f}, "
                f"DNI·sin(elev)+DHI={recomposed:.1f} W/m². Se conservan los valores observados."
            )
    elif vals["ghi"] is not None and vals["dhi"] is not None and vals["dni"] is None:
        vals["dni"] = max(0.0, (vals["ghi"] - vals["dhi"]) / s) if s > 1e-6 else 0.0
        derived.append("dni_identity")
    elif vals["ghi"] is not None and vals["dni"] is not None and vals["dhi"] is None:
        vals["dhi"] = max(0.0, vals["ghi"] - vals["dni"] * s)
        derived.append("dhi_identity")
    elif vals["dni"] is not None and vals["dhi"] is not None and vals["ghi"] is None:
        vals["ghi"] = max(0.0, vals["dni"] * s + vals["dhi"])
        derived.append("ghi_identity")
    elif vals["ghi"] is not None:
        if vals["ghi"] <= 0.0 or s <= 1e-6:
            vals["dhi"] = max(0.0, vals["ghi"])
            vals["dni"] = 0.0
        else:
            i0h = extraterrestrial_normal_wm2(day_of_year) * s
            kt = min(2.0, max(0.0, vals["ghi"] / max(i0h, 1e-6)))
            if kt <= 0.22:
                kd = 1.0 - 0.09 * kt
            elif kt <= 0.80:
                kd = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
            else:
                kd = 0.165
            kd = min(1.0, max(0.0, kd))
            vals["dhi"] = vals["ghi"] * kd
            vals["dni"] = max(0.0, (vals["ghi"] - vals["dhi"]) / s)
        derived.extend(["dni_erbs", "dhi_erbs"])
    else:
        raise ValueError("Se necesita al menos GHI o una pareja DNI+DHI para definir la radiación.")

    return {**vals, "derived": derived, "warnings": warnings}
