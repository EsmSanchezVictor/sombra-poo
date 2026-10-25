"""Vegetación y evapotranspiración para el modelo avanzado de superficies v2.

Objetivos de esta etapa
-----------------------
- Mantener intactos los modelos ``standard`` y ``advanced`` (seco v1).
- Añadir un tercer modo ``advanced_vegetation`` que incorpora un término
  latente ``LE`` físicamente explícito para suelo vegetado.
- Calcular por separado una estimación de evapotranspiración de copas para
  diagnóstico microclimático, sin confundirla con el flujo del suelo.
- Hacer explícitas las aproximaciones y los valores por defecto.

El potencial de evapotranspiración se basa en la forma horaria de FAO-56
Penman-Monteith para cultivo de referencia. La vegetación real se representa
mediante Kc, LAI/actividad foliar, fenología y disponibilidad hídrica. Es una
aproximación comparativa y debe calibrarse con datos locales cuando se quiera
usar con fines predictivos absolutos.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

SIGMA = 5.670374419e-8


@dataclass(frozen=True)
class VegetationConfig:
    """Parámetros globales del módulo de vegetación.

    ``ground_vegetation_fraction`` representa qué fracción de las celdas de
    suelo (no sendero) funciona como superficie vegetal activa. Hasta que el
    editor tenga polígonos específicos de césped/canteros, es deliberadamente
    un parámetro global y queda registrado en los metadatos.
    """

    ground_vegetation_fraction: float = 0.50
    water_availability: float = 0.75
    canopy_water_availability: float = 0.75
    reference_albedo: float = 0.23
    reference_emissivity: float = 0.98
    max_ground_latent_wm2: float = 350.0
    max_canopy_latent_wm2: float = 450.0
    leaf_off_fraction: float = 0.15
    leaf_off_transmittance_default: float = 0.75

    def validated(self) -> "VegetationConfig":
        for name in (
            "ground_vegetation_fraction",
            "water_availability",
            "canopy_water_availability",
            "reference_albedo",
            "reference_emissivity",
            "leaf_off_fraction",
            "leaf_off_transmittance_default",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} debe estar entre 0 y 1")
        if self.max_ground_latent_wm2 <= 0 or self.max_canopy_latent_wm2 <= 0:
            raise ValueError("los límites de flujo latente deben ser positivos")
        return self


def _clip01(value: Any) -> float:
    return float(min(1.0, max(0.0, float(value))))


def wind_speed_mps(value: Any) -> float:
    """Parser compartido; las funciones ET reciben viento a 2 m.

    La conversión desde una referencia a 10 m se hace en el llamador.
    """
    from core.climate_profile import viento_categoria_a_ms
    return viento_categoria_a_ms(value)


def saturation_vapor_pressure_kpa(temp_c: Any) -> np.ndarray:
    t = np.asarray(temp_c, dtype=float)
    return 0.6108 * np.exp((17.27 * t) / (t + 237.3))


def slope_vapor_pressure_curve_kpa_c(temp_c: Any) -> np.ndarray:
    t = np.asarray(temp_c, dtype=float)
    es = saturation_vapor_pressure_kpa(t)
    return 4098.0 * es / np.square(t + 237.3)


def atmospheric_pressure_kpa(elevation_m: float = 0.0) -> float:
    z = float(elevation_m)
    return float(101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26)


def psychrometric_constant_kpa_c(elevation_m: float = 0.0) -> float:
    return 0.000665 * atmospheric_pressure_kpa(elevation_m)


def phenology_factor(
    day_of_year: int | float,
    latitude_deg: float,
    deciduous: bool,
    *,
    leaf_off_fraction: float = 0.15,
) -> float:
    """Factor foliar estacional [0,1] para caducifolias.

    Es un *proxy fenológico suave*, no un calendario botánico específico por
    especie. Mantiene perennes en 1.0 y reduce gradualmente la actividad de
    caducifolias hacia el invierno del hemisferio correspondiente. En latitudes
    tropicales (<15°) no se fuerza una estacionalidad térmica.
    """
    if not deciduous or abs(float(latitude_deg)) < 15.0:
        return 1.0
    doy = ((float(day_of_year) - 1.0) % 365.0) + 1.0
    # Pico foliar aproximado un mes después del solsticio de verano.
    peak = 205.0 if float(latitude_deg) >= 0 else 20.0
    seasonal = 0.5 * (1.0 + math.cos(2.0 * math.pi * (doy - peak) / 365.0))
    minimum = _clip01(leaf_off_fraction)
    return float(minimum + (1.0 - minimum) * seasonal)


def lai_activity_factor(lai: Any, reference_lai: float = 3.0) -> np.ndarray:
    """Actividad de dosel basada en interceptación tipo Beer-Lambert.

    Se normaliza a 1 para LAI=3, evitando que LAI actúe como multiplicador
    lineal ilimitado de ET. Se acota a 1.25 para robustez/calibración.
    """
    lai_arr = np.maximum(0.0, np.asarray(lai, dtype=float))
    ref = max(0.1, float(reference_lai))
    denom = 1.0 - math.exp(-0.5 * ref)
    activity = (1.0 - np.exp(-0.5 * lai_arr)) / max(denom, 1e-9)
    return np.clip(activity, 0.0, 1.25)


def hourly_fao56_reference_et0_mm_h(
    *,
    air_temp_c: float,
    rh_pct: float,
    wind_speed_2m_mps: float,
    net_radiation_wm2: Any,
    elevation_m: float = 0.0,
) -> np.ndarray:
    """ET0 horaria [mm/h] con FAO-56 Penman-Monteith.

    Se usa la forma horaria con coeficiente 37. El flujo de calor del suelo se
    aproxima como 0.1 Rn durante periodos de Rn positivo y 0.5 Rn cuando Rn es
    negativo, siguiendo el esquema horario de referencia. Los resultados
    negativos se truncan a cero porque aquí se modela evapotranspiración, no
    condensación/rocío.
    """
    t = float(air_temp_c)
    rh = min(100.0, max(0.0, float(rh_pct)))
    u2 = max(0.0, float(wind_speed_2m_mps))
    rn_w = np.asarray(net_radiation_wm2, dtype=float)
    rn_mj = rn_w * 0.0036  # W/m² -> MJ/m²/h
    g_mj = np.where(rn_mj >= 0.0, 0.10 * rn_mj, 0.50 * rn_mj)

    es = float(saturation_vapor_pressure_kpa(t))
    ea = es * rh / 100.0
    delta = float(slope_vapor_pressure_curve_kpa_c(t))
    gamma = psychrometric_constant_kpa_c(elevation_m)

    numerator = (
        0.408 * delta * (rn_mj - g_mj)
        + gamma * (37.0 / (t + 273.0)) * u2 * (es - ea)
    )
    denominator = delta + gamma * (1.0 + 0.34 * u2)
    et0 = numerator / max(denominator, 1e-12)
    return np.maximum(0.0, et0)


def latent_heat_vaporization_mj_kg(temp_c: float) -> float:
    return float(max(2.35, 2.501 - 0.002361 * float(temp_c)))


def et_mm_h_to_latent_wm2(et_mm_h: Any, temp_c: float) -> np.ndarray:
    et = np.maximum(0.0, np.asarray(et_mm_h, dtype=float))
    lam = latent_heat_vaporization_mj_kg(temp_c)
    return et * lam * 1e6 / 3600.0


def reference_net_radiation_wm2(
    *,
    incident_shortwave_wm2: Any,
    longwave_down_wm2: Any,
    air_temp_k: float,
    albedo: float = 0.23,
    emissivity: float = 0.98,
) -> np.ndarray:
    """Rn aproximada de una cubierta vegetal de referencia a T≈Ta."""
    sw = np.maximum(0.0, np.asarray(incident_shortwave_wm2, dtype=float))
    lw = np.maximum(0.0, np.asarray(longwave_down_wm2, dtype=float))
    alpha = 1.0 - _clip01(albedo)
    eps = min(1.0, max(0.01, float(emissivity)))
    ta = max(1.0, float(air_temp_k))
    return alpha * sw + eps * lw - eps * SIGMA * ta**4


def ground_latent_heat_flux_wm2(
    *,
    air_temp_k: float,
    rh_pct: float,
    wind: Any,
    incident_shortwave_wm2: Any,
    longwave_down_wm2: Any,
    vegetation_fraction: Any,
    water_availability: float,
    kc: float = 1.0,
    lai: float = 3.0,
    elevation_m: float = 0.0,
    config: VegetationConfig | None = None,
) -> dict[str, Any]:
    cfg = (config or VegetationConfig()).validated()
    ta_c = float(air_temp_k) - 273.15
    veg = np.clip(np.asarray(vegetation_fraction, dtype=float), 0.0, 1.0)
    water = _clip01(water_availability)
    rn = reference_net_radiation_wm2(
        incident_shortwave_wm2=incident_shortwave_wm2,
        longwave_down_wm2=longwave_down_wm2,
        air_temp_k=air_temp_k,
        albedo=cfg.reference_albedo,
        emissivity=cfg.reference_emissivity,
    )
    et0 = hourly_fao56_reference_et0_mm_h(
        air_temp_c=ta_c,
        rh_pct=rh_pct,
        wind_speed_2m_mps=wind_speed_mps(wind),
        net_radiation_wm2=rn,
        elevation_m=elevation_m,
    )
    activity = float(lai_activity_factor(lai))
    et = et0 * max(0.0, float(kc)) * activity * water * veg
    le = np.minimum(cfg.max_ground_latent_wm2, et_mm_h_to_latent_wm2(et, ta_c))
    return {
        "latent_heat_flux_wm2": le,
        "et0_mm_h": et0,
        "et_actual_mm_h": et,
        "reference_net_radiation_wm2": rn,
        "water_availability": water,
        "vegetation_fraction": veg,
        "lai_activity": activity,
        "model": "fao56_pm_hourly_ground_v1",
    }


def species_canopy_latent_flux_wm2(
    *,
    air_temp_k: float,
    rh_pct: float,
    wind: Any,
    ghi_wm2: float,
    longwave_down_wm2: float,
    lai: float,
    kc: float,
    phenology: float,
    water_availability: float,
    elevation_m: float = 0.0,
    config: VegetationConfig | None = None,
) -> dict[str, float]:
    """Flujo latente potencial de una copa, usado como diagnóstico separado.

    No se resta directamente del balance energético del suelo: la copa es una
    superficie diferente. Esto evita atribuir al suelo toda la energía usada
    por transpiración foliar.
    """
    cfg = (config or VegetationConfig()).validated()
    ta_c = float(air_temp_k) - 273.15
    rn = float(reference_net_radiation_wm2(
        incident_shortwave_wm2=max(0.0, float(ghi_wm2)),
        longwave_down_wm2=max(0.0, float(longwave_down_wm2)),
        air_temp_k=air_temp_k,
        albedo=0.20,
        emissivity=0.97,
    ))
    et0 = float(hourly_fao56_reference_et0_mm_h(
        air_temp_c=ta_c,
        rh_pct=rh_pct,
        wind_speed_2m_mps=wind_speed_mps(wind),
        net_radiation_wm2=rn,
        elevation_m=elevation_m,
    ))
    lai_eff = max(0.0, float(lai)) * _clip01(phenology)
    activity = float(lai_activity_factor(lai_eff))
    et = et0 * max(0.0, float(kc)) * activity * _clip01(water_availability)
    le = float(min(cfg.max_canopy_latent_wm2, float(et_mm_h_to_latent_wm2(et, ta_c))))
    return {
        "latent_heat_flux_wm2": le,
        "et0_mm_h": et0,
        "et_actual_mm_h": et,
        "reference_net_radiation_wm2": rn,
        "lai_effective": lai_eff,
        "lai_activity": activity,
        "phenology_factor": _clip01(phenology),
        "water_availability": _clip01(water_availability),
        "model": "fao56_pm_hourly_canopy_v1",
    }
