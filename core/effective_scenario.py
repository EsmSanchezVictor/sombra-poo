"""Configuración efectiva, independiente de Tk y serializable por resultado."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
import calendar
import math
from core.climate_profile import viento_categoria_a_ms, velocidad_viento
from core.local_time import local_instant, resolve_local_datetime, instant_metadata

SCENARIO_SCHEMA = 2

def value(item):
    return item.get() if hasattr(item, "get") else item

def scenario_date(variables):
    """El día visible manda; ISO aporta el año cuando no existe _year."""
    iso = value(variables.get("_date_iso"))
    parsed = date.fromisoformat(str(iso)) if iso else None
    year = int(value(variables.get("_year", parsed.year if parsed else datetime.now().year)))
    day = int(float(value(variables.get("dia", parsed.timetuple().tm_yday if parsed else 1))))
    if not 1 <= day <= (366 if calendar.isleap(year) else 365):
        raise ValueError(f"Día del año inválido para {year}: {day}")
    return date(year, 1, 1) + timedelta(days=day - 1)

def effective_model(input_mode, selected_model, *, surface=False):
    if str(input_mode).lower() == "simple":
        return "standard"
    allowed = {"standard", "advanced", "advanced_vegetation"} if surface else {"standard", "advanced"}
    if selected_model not in allowed:
        raise ValueError("Modelo científico desconocido")
    return selected_model

@dataclass(frozen=True)
class EffectiveScenarioConfig:
    input_mode: str
    date_iso: str
    hour_local: float
    latitude: float
    longitude: float
    timezone: str
    tmrt_model: str
    air_temp_c: float
    rh_pct: float
    wind_ref_10m_m_s: float
    k_factor: float
    ghi: float
    dni: float
    dhi: float
    solar_elevation: float
    solar_azimuth: float
    source_mode: str
    source_label: str
    quality: str
    source_detail: str
    derived_components: tuple = ()
    warnings: tuple = ()
    weather_sources: tuple = ()
    schema_version: int = SCENARIO_SCHEMA
    instant_local_iso: str = ""
    instant_utc_iso: str = ""
    utc_offset_hours: float | None = None
    time_fold: int = 0
    time_policy: str = ""

    @classmethod
    def from_resolved(cls, *, input_mode, selected_model, fecha, hour, lat, lon,
                      timezone, ta, rh, wind, k_factor, solar):
        mode = effective_model(input_mode, selected_model)
        measured = solar.get("source_mode") == "observed_series"
        weather = []
        for key, original in (("ta_c", ta), ("rh_pct", rh), ("wind_m_s", wind)):
            observed = solar.get(key) if measured else None
            weather.append((key, "observed_series" if observed is not None else "user_input"))
        ta = solar.get("ta_c") if measured and solar.get("ta_c") is not None else ta
        rh = solar.get("rh_pct") if measured and solar.get("rh_pct") is not None else rh
        wind = solar.get("wind_m_s") if measured and solar.get("wind_m_s") is not None else wind
        numbers = [float(x) for x in (hour, lat, lon, ta, rh, k_factor)]
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError("Las entradas del escenario deben ser finitas")
        if not 0 <= numbers[0] <= 24 or not -90 <= numbers[1] <= 90 or not -180 <= numbers[2] <= 180:
            raise ValueError("Hora o coordenadas fuera de rango")
        if numbers[3] <= -273.15 or not 0 <= numbers[4] <= 100 or numbers[5] < 0:
            raise ValueError("Temperatura, humedad o k_factor fuera de rango")
        rad = [float(solar[key]) for key in ("ghi", "dni", "dhi", "elevation", "azimuth")]
        if not all(math.isfinite(x) for x in rad) or min(rad[:3]) < 0:
            raise ValueError("Radiación o geometría solar inválida")
        if numbers[0] == 24:
            fecha += timedelta(days=1)
            numbers[0] = 0.0
        if solar.get("instant_local_iso"):
            instant = resolve_local_datetime(datetime.fromisoformat(solar["instant_local_iso"]), timezone)
            requested = datetime.combine(fecha, datetime.min.time()) + timedelta(hours=numbers[0])
            if instant.replace(tzinfo=None) != requested:
                raise ValueError("El instante solar no coincide con la fecha/hora del escenario.")
        else:
            instant = local_instant(fecha, numbers[0], timezone)
        return cls(str(input_mode), fecha.isoformat(), *numbers[:3], str(timezone), mode,
                   numbers[3], numbers[4], viento_categoria_a_ms(wind), numbers[5], *rad,
                   str(solar.get("source_mode", "clear_sky")), str(solar.get("source_label", "Cielo claro")),
                   str(solar.get("quality", "modeled_clear_sky")), str(solar.get("source_detail", "fallback")),
                   tuple(solar.get("derived_components", ())), tuple(solar.get("warnings", ())), tuple(weather), **instant_metadata(instant))

    def to_dict(self):
        return asdict(self)

    @property
    def wind_2m_m_s(self):
        # Perfil neutro operativo sobre césped; no representa viento bajo copa.
        return velocidad_viento(2.0, self.wind_ref_10m_m_s, z_ref=10.0, z0=0.03)

    def calculator(self):
        from shadow_temp import Temperatura
        if self.instant_local_iso:
            # El offset capturado forma parte del resultado: reproducirlo no
            # debe reinterpretar sus reglas IANA tras una actualización.
            instant = datetime.fromisoformat(self.instant_local_iso)
            if instant.utcoffset() is None:
                raise ValueError("El instante capturado necesita un offset explícito.")
            if self.instant_utc_iso and instant != datetime.fromisoformat(self.instant_utc_iso):
                raise ValueError("Los instantes local y UTC capturados no coinciden.")
            captured_offset = instant.utcoffset().total_seconds() / 3600.0
            if self.utc_offset_hours is not None and self.utc_offset_hours != captured_offset:
                raise ValueError("El offset capturado no coincide con el instante local.")
            requested = datetime.combine(date.fromisoformat(self.date_iso), datetime.min.time()) + timedelta(hours=self.hour_local)
            if requested != instant.replace(tzinfo=None):
                raise ValueError("El instante capturado no coincide con la fecha/hora del escenario.")
        else:
            instant = local_instant(date.fromisoformat(self.date_iso), self.hour_local, self.timezone)
        offset = instant.utcoffset().total_seconds() / 3600.0
        return Temperatura(self.latitude, self.longitude, k_factor=self.k_factor,
                           tz_offset_hours=offset, model_mode=self.tmrt_model)

    def calculation_kwargs(self):
        return dict(date_value=date.fromisoformat(self.date_iso), time_value=self.hour_local,
                    radiation_override=self.ghi, solar_altitude_override=self.solar_elevation,
                    dni_override=self.dni, dhi_override=self.dhi)
