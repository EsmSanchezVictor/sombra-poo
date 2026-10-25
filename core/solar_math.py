"""Geometría solar analítica compartida.

Este módulo concentra el fallback geométrico del proyecto.  Antes existían
implementaciones paralelas en ``shadow_temp.py`` y ``modelo_con_excel.py``;
aunque usaban la misma aproximación, mantener dos copias permitía que una
corrección futura dejara resultados distintos entre Panel 1/2 y Panel 4.

Convenciones
------------
* latitud/longitud en grados, este positivo y oeste negativo;
* ``tz_offset_hours`` es UTC offset del instante local (Argentina = -3);
* azimut: 0° = norte, 90° = este, sentido horario;
* elevación: grados sobre el horizonte.

Es un fallback analítico. Cuando pvlib está habilitado, ``SolarEngine`` usa
pvlib para la posición y radiación de cielo despejado.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import calendar
import math


def equation_of_time_minutes(day_of_year: int | float) -> float:
    """Ecuación del tiempo aproximada [min]."""
    b = 360.0 * (float(day_of_year) - 81.0) / 365.0
    return (
        9.87 * math.sin(math.radians(2.0 * b))
        - 7.53 * math.cos(math.radians(b))
        - 1.5 * math.sin(math.radians(b))
    )


def equation_of_time_degrees(day_of_year: int | float) -> float:
    """Corrección equivalente de la ecuación del tiempo [grados horarios]."""
    return equation_of_time_minutes(day_of_year) / 4.0


def standard_meridian_deg(longitude_deg: float, tz_offset_hours: float | None = None) -> float:
    """Meridiano estándar [°] del huso.

    Si no se conoce el huso, se conserva el fallback histórico por longitud.
    En cálculos de producción debe preferirse siempre un offset obtenido de
    una zona IANA para la fecha analizada.
    """
    if tz_offset_hours is None:
        tz_offset_hours = min(14.0, max(-12.0, round(float(longitude_deg) / 15.0)))
    return float(tz_offset_hours) * 15.0


def timezone_offset_hours(
    timezone_name: str | None,
    day_of_year: int,
    hour_local: float = 12.0,
    *,
    year: int | None = None,
) -> float | None:
    """UTC offset [h] de una zona IANA para el instante local indicado."""
    if not timezone_name:
        return None
    from core.local_time import local_instant
    year = int(year if year is not None else datetime.now().year)
    day = float(day_of_year)
    if not math.isfinite(day) or not day.is_integer() or not 1 <= day <= (366 if calendar.isleap(year) else 365):
        raise ValueError(f"Día del año inválido para {year}: {day_of_year}")
    fecha = datetime(year, 1, 1).date() + timedelta(days=int(day) - 1)
    return local_instant(fecha, hour_local, timezone_name).utcoffset().total_seconds() / 3600.0


def solar_declination_deg(day_of_year: int | float) -> float:
    return 23.45 * math.sin(
        math.radians((360.0 / 365.0) * (float(day_of_year) - 81.0))
    )


def solar_hour_angle_deg(
    longitude_deg: float,
    day_of_year: int | float,
    hour_local: float,
    tz_offset_hours: float | None = None,
) -> float:
    """Ángulo horario solar [°] con corrección de longitud y EoT."""
    meridian = standard_meridian_deg(longitude_deg, tz_offset_hours)
    return (
        15.0 * (float(hour_local) - 12.0)
        + (float(longitude_deg) - meridian)
        + equation_of_time_degrees(day_of_year)
    )


def solar_elevation_deg(
    latitude_deg: float,
    longitude_deg: float,
    day_of_year: int | float,
    hour_local: float,
    tz_offset_hours: float | None = None,
) -> float:
    phi = math.radians(float(latitude_deg))
    delta = math.radians(solar_declination_deg(day_of_year))
    h = math.radians(
        solar_hour_angle_deg(longitude_deg, day_of_year, hour_local, tz_offset_hours)
    )
    arg = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(h)
    return math.degrees(math.asin(max(-1.0, min(1.0, arg))))


def solar_azimuth_deg(
    latitude_deg: float,
    longitude_deg: float,
    day_of_year: int | float,
    hour_local: float,
    tz_offset_hours: float | None = None,
    *,
    elevation_deg: float | None = None,
) -> float:
    """Azimut solar 0..360° desde norte, sentido horario."""
    phi = math.radians(float(latitude_deg))
    delta = math.radians(solar_declination_deg(day_of_year))
    h = math.radians(
        solar_hour_angle_deg(longitude_deg, day_of_year, hour_local, tz_offset_hours)
    )
    elev = solar_elevation_deg(
        latitude_deg, longitude_deg, day_of_year, hour_local, tz_offset_hours
    ) if elevation_deg is None else float(elevation_deg)
    theta = math.radians(elev)

    cos_theta = math.cos(theta)
    cos_phi = math.cos(phi)
    if abs(cos_theta) < 1e-12 or abs(cos_phi) < 1e-12:
        return 0.0
    sin_az = -math.sin(h) * math.cos(delta) / cos_theta
    cos_az = (math.sin(delta) - math.sin(theta) * math.sin(phi)) / (cos_theta * cos_phi)
    return math.degrees(math.atan2(sin_az, cos_az)) % 360.0


def solar_position_deg(
    latitude_deg: float,
    longitude_deg: float,
    day_of_year: int | float,
    hour_local: float,
    tz_offset_hours: float | None = None,
) -> tuple[float, float]:
    """Devuelve ``(azimut, elevación)`` en grados."""
    elev = solar_elevation_deg(
        latitude_deg, longitude_deg, day_of_year, hour_local, tz_offset_hours
    )
    az = solar_azimuth_deg(
        latitude_deg,
        longitude_deg,
        day_of_year,
        hour_local,
        tz_offset_hours,
        elevation_deg=elev,
    )
    return az, elev
