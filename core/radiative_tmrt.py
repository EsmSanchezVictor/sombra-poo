"""Modelo avanzado de Tmrt por balance radiativo humano simplificado.

Este módulo implementa una alternativa físicamente explícita al modelo
empírico ``Tmrt = Ta + k * GHI``.  Sigue la estructura usada en métodos de
biometeorología exterior (p. ej. Weihs/Höppe/SOLWEIG): la Tmrt se obtiene a
partir de la suma de radiación de onda corta y larga absorbida por una persona.

IMPORTANTE
----------
Es un *modelo avanzado v1*, no un reemplazo de SOLWEIG/ENVI-met.  Con los datos
que hoy dispone la aplicación se hacen estas aproximaciones deliberadas:

* persona de pie, con factor de área proyectada fijo ``f_p = 0.28``;
* absorptividad solar humana ``alpha_sw = 0.70``;
* emisividad/absorptividad de onda larga ``epsilon_lw = 0.97``;
* factor angular hemisférico ``f_a = 0.50``;
* reflexión de onda corta desde el suelo = ``albedo_ground * GHI``;
* la onda larga del cielo y del suelo se aproxima, por defecto, mediante una
  temperatura radiativa equivalente igual a la temperatura del aire.  Esta
  elección garantiza que, sin radiación solar, Tmrt = Ta;
* con la información actual de sombra, la misma transmitancia efectiva se
  aplica a directo, difuso y reflejado.  En etapas posteriores puede separarse
  mediante SVF/LAI y propiedades ópticas de copa.

La ventaja frente al modelo empírico es que los coeficientes tienen significado
físico y se usan DNI/DHI/GHI por separado.  La precisión absoluta todavía debe
validarse con mediciones de globo/radiómetro en el contexto de uso.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

SIGMA = 5.670374419e-8  # W m-2 K-4


@dataclass(frozen=True)
class AdvancedTmrtConfig:
    """Parámetros del balance radiativo humano simplificado."""

    shortwave_absorptivity: float = 0.70
    longwave_emissivity: float = 0.97
    projected_area_factor: float = 0.28
    angular_factor: float = 0.50
    ground_albedo: float = 0.20

    def validated(self) -> "AdvancedTmrtConfig":
        vals = {
            "shortwave_absorptivity": self.shortwave_absorptivity,
            "longwave_emissivity": self.longwave_emissivity,
            "projected_area_factor": self.projected_area_factor,
            "angular_factor": self.angular_factor,
            "ground_albedo": self.ground_albedo,
        }
        for name, value in vals.items():
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} debe ser finito.")
        if not 0.0 <= self.shortwave_absorptivity <= 1.0:
            raise ValueError("shortwave_absorptivity debe estar entre 0 y 1.")
        if not 0.01 <= self.longwave_emissivity <= 1.0:
            raise ValueError("longwave_emissivity debe estar entre 0 y 1.")
        if not 0.0 <= self.projected_area_factor <= 1.0:
            raise ValueError("projected_area_factor debe estar entre 0 y 1.")
        if not 0.0 <= self.angular_factor <= 1.0:
            raise ValueError("angular_factor debe estar entre 0 y 1.")
        if not 0.0 <= self.ground_albedo <= 1.0:
            raise ValueError("ground_albedo debe estar entre 0 y 1.")
        return self


def resolve_shortwave_components(
    ghi: float,
    solar_elevation_deg: float,
    dni: float | None = None,
    dhi: float | None = None,
) -> tuple[float, float, float]:
    """Devuelve GHI/DNI/DHI físicamente consistentes y no negativos.

    Si DNI/DHI no están disponibles, se usa un fallback sencillo con 20 % de
    difusa y se reconstruye DNI para conservar ``GHI = DNI*sin(elev) + DHI``.
    """
    ghi = max(0.0, float(ghi))
    elev = float(solar_elevation_deg)
    sin_elev = max(0.0, math.sin(math.radians(elev)))

    if ghi <= 0.0 or sin_elev <= 1e-9:
        return 0.0, 0.0, 0.0

    if dni is None and dhi is None:
        dhi = 0.20 * ghi
        dni = max(0.0, (ghi - dhi) / sin_elev)
    elif dhi is None:
        dni = max(0.0, float(dni))
        dhi = max(0.0, ghi - dni * sin_elev)
    elif dni is None:
        dhi = min(max(0.0, float(dhi)), ghi)
        dni = max(0.0, (ghi - dhi) / sin_elev)
    else:
        dni = max(0.0, float(dni))
        dhi = max(0.0, float(dhi))
        # Las fuentes externas pueden traer pequeños errores de cierre. No se
        # renormaliza si son razonables; la Tmrt usa los componentes medidos.

    return ghi, float(dni), float(dhi)


def calculate_radiative_tmrt(
    air_temp_c: float,
    transmittance: Any,
    ghi: float,
    solar_elevation_deg: float,
    *,
    dni: float | None = None,
    dhi: float | None = None,
    config: AdvancedTmrtConfig | None = None,
    sky_radiative_temp_c: float | None = None,
    ground_radiative_temp_c: float | None = None,
) -> dict[str, Any]:
    """Calcula Tmrt mediante balance de flujos radiativos simplificado.

    La forma utilizada es equivalente a::

        Tmrt = [ ((alpha_sw/epsilon_lw) * K + L) / sigma ]**0.25 - 273.15

    con::

        K = tau * (f_p*DNI + f_a*DHI + f_a*albedo*GHI)
        L = f_a * (L_down + L_up)

    ``tau`` puede ser escalar o una matriz y representa la transmitancia
    efectiva asociada a la sombra local.
    """
    cfg = (config or AdvancedTmrtConfig()).validated()
    ta_c = float(air_temp_c)
    if not math.isfinite(ta_c):
        raise ValueError("La temperatura del aire debe ser finita.")

    ghi, dni, dhi = resolve_shortwave_components(
        ghi, solar_elevation_deg, dni=dni, dhi=dhi
    )
    tau = np.asarray(transmittance, dtype=float)
    tau = np.clip(tau, 0.0, 1.0)

    # Onda corta incidente ponderada por geometría corporal.
    reflected_sw = cfg.ground_albedo * ghi
    directional_sw = (
        cfg.projected_area_factor * dni
        + cfg.angular_factor * dhi
        + cfg.angular_factor * reflected_sw
    )
    shortwave_effective = tau * directional_sw

    # Onda larga: aproximación de primera etapa. Separar cielo/suelo permite
    # sustituir más adelante Ta por temperaturas radiativas observadas/modeladas
    # sin cambiar la API.
    sky_c = ta_c if sky_radiative_temp_c is None else float(sky_radiative_temp_c)
    ground_c = ta_c if ground_radiative_temp_c is None else float(ground_radiative_temp_c)
    sky_k = max(1.0, sky_c + 273.15)
    ground_k = max(1.0, ground_c + 273.15)
    lw_down = SIGMA * sky_k**4
    lw_up = SIGMA * ground_k**4
    longwave_equivalent = cfg.angular_factor * (lw_down + lw_up)

    # La razón alpha_sw/epsilon_lw transforma la contribución de onda corta
    # a flujo equivalente de onda larga para la definición de Tmrt.
    equivalent_flux = (
        (cfg.shortwave_absorptivity / cfg.longwave_emissivity) * shortwave_effective
        + longwave_equivalent
    )
    equivalent_flux = np.maximum(equivalent_flux, 0.0)
    tmrt_k = np.power(equivalent_flux / SIGMA, 0.25)
    tmrt_c = tmrt_k - 273.15

    if np.ndim(tmrt_c) == 0:
        tmrt_value: Any = float(tmrt_c)
        sw_value: Any = float(shortwave_effective)
    else:
        tmrt_value = tmrt_c.astype(np.float32, copy=False)
        sw_value = np.asarray(shortwave_effective, dtype=np.float32)

    return {
        "tmrt_c": tmrt_value,
        "ghi": float(ghi),
        "dni": float(dni),
        "dhi": float(dhi),
        "shortwave_effective": sw_value,
        "longwave_equivalent": float(longwave_equivalent),
        "reflected_shortwave": float(reflected_sw),
        "model": "advanced_radiative_v1",
    }
