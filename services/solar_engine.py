"""Motor solar único con pvlib opcional y fallback analítico.

La clase devuelve posición solar y radiación usando la MISMA zona horaria y
el MISMO instante. Si pvlib no está disponible usa el núcleo analítico compartido
``core.solar_math``, manteniendo la identidad GHI = DNI*sin(elev) + DHI.
"""
from __future__ import annotations

from datetime import datetime
import math

from core.solar_math import solar_position_deg
from core.local_time import resolve_local_datetime, instant_metadata, iana_zone

try:
    import pandas as pd
    import pvlib  # type: ignore
except ImportError:  # pragma: no cover
    pvlib = None
    pd = None


def _tz_offset_hours(tz: str, dt: datetime | None = None) -> float | None:
    """Offset UTC de ``tz`` para el instante indicado.

    A diferencia de la versión anterior, no fija el cálculo al 1/1/2026:
    respeta horario de verano cuando la zona lo utiliza.
    """
    local = resolve_local_datetime(dt or datetime.now(), tz)
    return float(local.utcoffset().total_seconds() / 3600.0)


def _pandas_timestamp_local(dt: datetime, tz: str):
    """Mismo instante estricto para pvlib y fallback."""
    return pd.DatetimeIndex([pd.Timestamp(resolve_local_datetime(dt, tz))])


class SolarEngine:
    def __init__(self, use_pvlib: bool = False, tz: str = "America/Argentina/Buenos_Aires"):
        self.set_timezone(tz)
        self.use_pvlib = False
        self.set_use_pvlib(use_pvlib)

    @property
    def pvlib_available(self) -> bool:
        return pvlib is not None and pd is not None

    def set_use_pvlib(self, enabled: bool) -> bool:
        """Activa pvlib solo si la dependencia está realmente disponible."""
        self.use_pvlib = bool(enabled and self.pvlib_available)
        return self.use_pvlib

    def set_timezone(self, tz: str | None) -> None:
        if not tz and hasattr(self, "tz"):
            return
        # Validar ahora para fallar temprano ante un nombre inválido.
        iana_zone(tz)
        self.tz = str(tz)

    def _fallback_position(self, lat: float, lon: float, dt: datetime) -> tuple[float, float]:
        dt = resolve_local_datetime(dt, self.tz)
        day = dt.timetuple().tm_yday
        hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        offset = _tz_offset_hours(self.tz, dt)
        return solar_position_deg(float(lat), float(lon), day, hour, offset)

    def get_solar_position(self, lat: float, lon: float, dt: datetime) -> tuple[float, float]:
        if self.use_pvlib:
            location = pvlib.location.Location(float(lat), float(lon), tz=self.tz)
            ts = _pandas_timestamp_local(dt, self.tz)
            sol = location.get_solarposition(ts)
            return float(sol["azimuth"].iloc[0]), float(sol["elevation"].iloc[0])

        azim, elev = self._fallback_position(lat, lon, dt)
        return float(azim), float(elev)

    def get_radiation(self, lat: float, lon: float, dt: datetime) -> dict:
        """GHI/DNI/DHI de cielo despejado para el instante.

        ``source='pvlib'`` usa el modelo clear-sky de la ``Location``.
        El fallback es una aproximación simple, pero conserva energía en el
        plano horizontal.
        """
        if self.use_pvlib:
            location = pvlib.location.Location(float(lat), float(lon), tz=self.tz)
            ts = _pandas_timestamp_local(dt, self.tz)
            rad = location.get_clearsky(ts)
            return {
                "ghi": max(0.0, float(rad["ghi"].iloc[0])),
                "dni": max(0.0, float(rad["dni"].iloc[0])),
                "dhi": max(0.0, float(rad["dhi"].iloc[0])),
                "source": "pvlib",
            }

        _, elev = self._fallback_position(lat, lon, dt)
        return self.fallback_radiation(elev)

    @staticmethod
    def fallback_radiation(elevation):
        """GHI analítica histórica; componentes conservan GHI = DNI·sin(elev)+DHI."""
        elev = float(elevation)
        if not math.isfinite(elev):
            raise ValueError("La elevación solar debe ser finita")
        if elev <= 0:
            return {"ghi": 0.0, "dni": 0.0, "dhi": 0.0, "source": "fallback"}
        seno = math.sin(math.radians(elev))
        ghi = 1367.0 * seno * 0.75
        dhi = 0.20 * ghi
        dni = 1367.0 * 0.75 * 0.80
        return {"ghi": ghi, "dni": dni, "dhi": dhi, "source": "fallback"}

    def get_solar_data(self, lat: float, lon: float, dt: datetime) -> dict:
        """Posición + radiación coherentes en una sola llamada lógica."""
        dt = resolve_local_datetime(dt, self.tz)
        azimuth, elevation = self.get_solar_position(lat, lon, dt)
        rad = self.get_radiation(lat, lon, dt)
        return {
            **rad,
            "azimuth": float(azimuth),
            "elevation": float(elevation),
            "timezone": self.tz,
            **instant_metadata(dt),
        }
