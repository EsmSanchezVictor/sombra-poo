"""Fuente única de posición solar y radiación de cielo despejado."""

from __future__ import annotations

import math
import warnings
from datetime import datetime

try:
    import pvlib
    import pandas as pd
except ImportError:  # pragma: no cover - depende del entorno de despliegue
    pvlib = None
    pd = None


class MotorSolar:
    """Calcula geometría solar con pvlib y un fallback NOAA documentado."""

    def __init__(self, lat, lon, tz="America/Argentina/Buenos_Aires"):
        self.lat = float(lat)
        self.lon = float(lon)
        self.tz = tz
        self.location = pvlib.location.Location(self.lat, self.lon, tz=tz) if pvlib else None

    def obtener_posicion_y_radiacion(self, fecha_hora):
        if pd is not None:
            fecha = pd.Timestamp(fecha_hora)
            fecha = fecha.tz_localize(self.tz) if fecha.tzinfo is None else fecha.tz_convert(self.tz)
        else:
            from zoneinfo import ZoneInfo
            fecha = (datetime.fromisoformat(fecha_hora) if isinstance(fecha_hora, str)
                     else fecha_hora)
            fecha = fecha.replace(tzinfo=ZoneInfo(self.tz)) if fecha.tzinfo is None else fecha.astimezone(ZoneInfo(self.tz))
        if self.location is not None:
            indice = pd.DatetimeIndex([fecha])
            sol = self.location.get_solarposition(indice)
            rad = self.location.get_clearsky(indice)
            return {
                "azimut": float(sol["azimuth"].iloc[0]),
                "elevacion": float(sol["elevation"].iloc[0]),
                "ghi": float(rad["ghi"].iloc[0]),
            }

        warnings.warn(
            "pvlib no está disponible; se usa la aproximación solar NOAA y "
            "radiación simplificada.", RuntimeWarning, stacklevel=2
        )
        return self._fallback_noaa(fecha)

    def _fallback_noaa(self, fecha):
        """Aproximación NOAA: ecuación del tiempo, declinación y hora solar."""
        n = fecha.dayofyear if hasattr(fecha, "dayofyear") else fecha.timetuple().tm_yday
        hora = fecha.hour + fecha.minute / 60 + fecha.second / 3600
        gamma = 2 * math.pi / 365 * (n - 1 + (hora - 12) / 24)
        eot = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                        - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(2 * gamma)
                        - 0.040849 * math.sin(2 * gamma))
        decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
                - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
                - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
        offset_h = fecha.utcoffset().total_seconds() / 3600
        minutos_solares = hora * 60 + eot + 4 * self.lon - 60 * offset_h
        angulo_horario = math.radians(minutos_solares / 4 - 180)
        lat = math.radians(self.lat)
        cos_cenit = max(-1.0, min(1.0, math.sin(lat) * math.sin(decl)
                                  + math.cos(lat) * math.cos(decl) * math.cos(angulo_horario)))
        elevacion = math.degrees(math.asin(cos_cenit))
        azimut = (math.degrees(math.atan2(math.sin(angulo_horario),
                   math.cos(angulo_horario) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180) % 360
        # 1367 W/m² es la constante solar media; 0,75 es sólo el fallback
        # atmosférico cuando el modelo Ineichen de pvlib no está instalado.
        ghi = max(0.0, 1367 * 0.75 * math.sin(math.radians(elevacion)))
        return {"azimut": azimut, "elevacion": elevacion, "ghi": ghi}