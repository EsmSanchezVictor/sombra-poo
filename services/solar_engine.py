"""Motor solar opcional con pvlib y fallback interno.

CAMBIO respecto a la versión original: el azimut de respaldo (cuando
pvlib no está disponible) ya no se calcula con la aproximación lineal
`(180 + (hora-12)*15) % 360` — eso ignora latitud, longitud y época
del año, y puede desviarse fácilmente 10-20° del azimut real fuera del
equinoccio. Ahora usa `Temperatura.solar_azimuth()`, la misma fuente
que ya se usaba para la elevación, evitando tener dos aproximaciones
distintas conviviendo en el mismo módulo.
"""
from __future__ import annotations

from datetime import datetime
import math

from shadow_temp import Temperatura

try:
    import pandas as pd
    import pvlib  # type: ignore
except ImportError:  # pragma: no cover
    pvlib = None
    pd = None


class SolarEngine:
    def __init__(self, use_pvlib: bool = False, tz: str = "America/Argentina/Buenos_Aires"):
        self.use_pvlib = bool(use_pvlib and pvlib is not None and pd is not None)
        self.tz = tz

    def get_solar_position(self, lat: float, lon: float, dt: datetime) -> tuple[float, float]:
        if self.use_pvlib:
            location = pvlib.location.Location(lat, lon, tz=self.tz)
            ts = pd.DatetimeIndex([pd.to_datetime(dt)]).tz_localize(self.tz, nonexistent="shift_forward", ambiguous="NaT")
            sol = location.get_solarposition(ts)
            return float(sol["azimuth"].iloc[0]), float(sol["elevation"].iloc[0])

        calc = Temperatura(latitude=lat, longitude=lon)
        day = dt.timetuple().tm_yday
        hour = dt.hour + dt.minute / 60
        elev = calc.solar_altitude(day, hour)
        azim = calc.solar_azimuth(day, hour)
        return azim, float(elev)

    def get_radiation(self, lat: float, lon: float, dt: datetime) -> dict:
        if self.use_pvlib:
            location = pvlib.location.Location(lat, lon, tz=self.tz)
            ts = pd.DatetimeIndex([pd.to_datetime(dt)]).tz_localize(self.tz, nonexistent="shift_forward", ambiguous="NaT")
            rad = location.get_clearsky(ts)
            return {
                "ghi": float(rad["ghi"].iloc[0]),
                "dni": float(rad["dni"].iloc[0]),
                "dhi": float(rad["dhi"].iloc[0]),
                "source": "pvlib",
            }

        calc = Temperatura(latitude=lat, longitude=lon)
        day = dt.timetuple().tm_yday
        hour = dt.hour + dt.minute / 60
        elev = max(0.0, calc.solar_altitude(day, hour))
        ghi = calc.clear_sky_radiation(elev)
        dni = ghi / max(math.sin(math.radians(max(0.1, elev))), 1e-6) if elev > 0 else 0.0
        dhi = max(0.0, ghi * 0.2)
        return {"ghi": float(ghi), "dni": float(dni), "dhi": float(dhi), "source": "fallback"}
