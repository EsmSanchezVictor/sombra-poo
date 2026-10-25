"""Balance energético avanzado de superficies exteriores (v1).

El núcleo resuelve, para cada celda, un balance estacionario no lineal:

    alpha K_down + epsilon L_down
      - epsilon sigma Ts^4
      - h_c (Ts - Ta)
      - h_g (Ts - Tsub)
      - LE = 0

En esta etapa ``LE`` se deja en cero salvo que el llamador provea un flujo
latente explícito. La vegetación/evapotranspiración se incorporará en la etapa
siguiente. El término h_g=k/d representa el acoplamiento conductivo con un
sustrato a temperatura Tsub y evita confundir este modelo con una superficie
adiabática. El modelo estándar/legacy no usa este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

SIGMA = 5.670374419e-8


@dataclass(frozen=True)
class SurfaceEnergyConfig:
    sky_emissivity_model: str = "brutsaert"
    max_iterations: int = 30
    tolerance_k: float = 1e-4
    residual_tolerance_wm2: float = 0.05
    min_surface_k: float = 180.0
    max_surface_k: float = 380.0

    def validated(self) -> "SurfaceEnergyConfig":
        if self.sky_emissivity_model not in {"brutsaert", "blackbody"}:
            raise ValueError("sky_emissivity_model no reconocido")
        for name in ('max_iterations', 'tolerance_k', 'residual_tolerance_wm2', 'min_surface_k', 'max_surface_k'):
            if not math.isfinite(float(getattr(self, name))):
                raise ValueError(f'{name} debe ser finito')
        if int(self.max_iterations) != self.max_iterations:
            raise ValueError('max_iterations debe ser entero')
        if self.max_iterations < 1:
            raise ValueError("max_iterations debe ser >= 1")
        if self.tolerance_k <= 0:
            raise ValueError("tolerance_k debe ser > 0")
        if self.residual_tolerance_wm2 <= 0:
            raise ValueError("residual_tolerance_wm2 debe ser > 0")
        if self.min_surface_k <= 0 or self.max_surface_k <= self.min_surface_k:
            raise ValueError("límites de temperatura inválidos")
        return self


def saturation_vapor_pressure_hpa(temp_c: float) -> float:
    """Presión de vapor de saturación (Tetens), hPa."""
    t = float(temp_c)
    return 6.112 * math.exp((17.67 * t) / (t + 243.5))


def clear_sky_emissivity_brutsaert(air_temp_k: float, rh_pct: float) -> float:
    """Emisividad efectiva de cielo despejado según Brutsaert.

    Usa presión de vapor real en hPa y temperatura del aire en K. Se acota a
    [0.35, 1] para robustez numérica fuera del rango meteorológico habitual.
    """
    ta_k = max(1.0, float(air_temp_k))
    ta_c = ta_k - 273.15
    rh = min(100.0, max(0.0, float(rh_pct))) / 100.0
    e_hpa = max(0.01, rh * saturation_vapor_pressure_hpa(ta_c))
    eps = 1.24 * (e_hpa / ta_k) ** (1.0 / 7.0)
    return float(min(1.0, max(0.35, eps)))


def cloud_fraction_from_label(value: Any) -> float:
    """Convierte la nubosidad disponible en la UI a fracción [0,1]."""
    if isinstance(value, (int, float, np.number)):
        v = float(value)
        return min(1.0, max(0.0, v / 100.0 if v > 1.0 else v))
    text = str(value or "").strip().lower()
    if "nubl" in text or "cubiert" in text or "overcast" in text:
        return 1.0
    if "parcial" in text or "partly" in text:
        return 0.5
    return 0.0


def all_sky_emissivity(air_temp_k: float, rh_pct: float, cloud_fraction: float = 0.0) -> float:
    """Emisividad efectiva de cielo con corrección simple de nubosidad.

    Se interpola entre Brutsaert despejado y cuerpo negro para cielo cubierto.
    La fuente de incertidumbre queda explícita en los diagnósticos.
    """
    eps_clear = clear_sky_emissivity_brutsaert(air_temp_k, rh_pct)
    cf = min(1.0, max(0.0, float(cloud_fraction)))
    return float(eps_clear + cf * (1.0 - eps_clear))


def downwelling_longwave(
    air_temp_k: float,
    rh_pct: float,
    cloud_fraction: float = 0.0,
    *,
    model: str = "brutsaert",
) -> tuple[float, float]:
    """Devuelve (L_down W/m², emisividad_cielo)."""
    ta = max(1.0, float(air_temp_k))
    if model == "blackbody":
        eps = 1.0
    else:
        eps = all_sky_emissivity(ta, rh_pct, cloud_fraction)
    return float(eps * SIGMA * ta**4), float(eps)


def solve_surface_energy_balance(
    *,
    air_temp_k: float,
    incident_shortwave_wm2: Any,
    solar_absorptance: Any,
    longwave_emissivity: Any,
    convective_coefficient_wm2k: float,
    thermal_conductivity_wmk: Any,
    coupling_depth_m: Any,
    rh_pct: float = 50.0,
    cloud_fraction: float = 0.0,
    substrate_temp_k: Any | None = None,
    latent_heat_flux_wm2: Any = 0.0,
    longwave_down_override_wm2: Any | None = None,
    config: SurfaceEnergyConfig | None = None,
) -> dict[str, Any]:
    """Resuelve el balance no lineal de temperatura superficial.

    Todos los parámetros de material aceptan escalares o matrices compatibles.
    El resultado incluye cada flujo, permitiendo auditar el cierre energético.
    """
    cfg = (config or SurfaceEnergyConfig()).validated()
    ta = float(air_temp_k)
    if not math.isfinite(ta) or ta <= 0:
        raise ValueError("air_temp_k debe ser Kelvin positivo y finito")
    for name, item in (("incident_shortwave_wm2", incident_shortwave_wm2),
                       ("solar_absorptance", solar_absorptance), ("longwave_emissivity", longwave_emissivity),
                       ("convective_coefficient_wm2k", convective_coefficient_wm2k),
                       ("thermal_conductivity_wmk", thermal_conductivity_wmk), ("coupling_depth_m", coupling_depth_m),
                       ("rh_pct", rh_pct), ("cloud_fraction", cloud_fraction), ("latent_heat_flux_wm2", latent_heat_flux_wm2),
                       ("substrate_temp_k", substrate_temp_k), ("longwave_down_override_wm2", longwave_down_override_wm2)):
        if item is not None and not np.all(np.isfinite(np.asarray(item, dtype=float))):
            raise ValueError(f"{name} debe contener valores finitos")
    if not 0 <= float(rh_pct) <= 100 or not 0 <= float(cloud_fraction) <= 1:
        raise ValueError("Humedad o fracción de nubes fuera de rango")
    for name, item, lower, upper, strict_lower in (
        ('incident_shortwave_wm2', incident_shortwave_wm2, 0, None, False),
        ('solar_absorptance', solar_absorptance, 0, 1, False),
        ('longwave_emissivity', longwave_emissivity, 0, 1, True),
        ('thermal_conductivity_wmk', thermal_conductivity_wmk, 0, None, True),
        ('coupling_depth_m', coupling_depth_m, 0, None, True),
        ('latent_heat_flux_wm2', latent_heat_flux_wm2, 0, None, False),
        ('substrate_temp_k', substrate_temp_k, 0, None, True),
        ('longwave_down_override_wm2', longwave_down_override_wm2, 0, None, False)):
        if item is None:
            continue
        arr = np.asarray(item, dtype=float)
        if np.any(arr <= lower if strict_lower else arr < lower) or (upper is not None and np.any(arr > upper)):
            raise ValueError(f'{name} fuera del dominio físico')
    hc = float(convective_coefficient_wm2k)
    if hc < 0:
        raise ValueError("El coeficiente convectivo no puede ser negativo")

    sw = np.maximum(0.0, np.asarray(incident_shortwave_wm2, dtype=float))
    alpha = np.clip(np.asarray(solar_absorptance, dtype=float), 0.0, 1.0)
    eps = np.clip(np.asarray(longwave_emissivity, dtype=float), 0.01, 1.0)
    k = np.maximum(1e-6, np.asarray(thermal_conductivity_wmk, dtype=float))
    depth = np.maximum(1e-4, np.asarray(coupling_depth_m, dtype=float))
    h_ground = k / depth
    tsub = ta if substrate_temp_k is None else np.asarray(substrate_temp_k, dtype=float)
    le = np.maximum(0.0, np.asarray(latent_heat_flux_wm2, dtype=float))

    l_down_base, eps_sky = downwelling_longwave(
        ta, rh_pct, cloud_fraction, model=cfg.sky_emissivity_model
    )
    if longwave_down_override_wm2 is None:
        l_down = np.asarray(l_down_base, dtype=float)
    else:
        l_down = np.maximum(0.0, np.asarray(longwave_down_override_wm2, dtype=float))
    q_sw_abs = alpha * sw
    q_lw_in = eps * l_down

    # Inicialización linealizada alrededor de Ta; luego Newton usa Ts^4 exacto.
    h_rad_ta = 4.0 * eps * SIGMA * ta**3
    denom = np.maximum(1e-9, hc + h_ground + h_rad_ta)
    # El cielo no es cuerpo negro: incluimos el déficit LW inicial.
    q_lw_net_ta = q_lw_in - eps * SIGMA * ta**4
    ts = ta + (q_sw_abs + q_lw_net_ta - le) / denom
    ts = np.clip(ts, cfg.min_surface_k, cfg.max_surface_k)

    converged = False
    iterations = 0
    for iterations in range(1, cfg.max_iterations + 1):
        residual = (
            q_sw_abs
            + q_lw_in
            - eps * SIGMA * ts**4
            - hc * (ts - ta)
            - h_ground * (ts - tsub)
            - le
        )
        deriv = -(4.0 * eps * SIGMA * ts**3 + hc + h_ground)
        step = residual / np.where(np.abs(deriv) < 1e-12, -1e-12, deriv)
        new_ts = np.clip(ts - step, cfg.min_surface_k, cfg.max_surface_k)
        new_residual = (
            q_sw_abs
            + q_lw_in
            - eps * SIGMA * new_ts**4
            - hc * (new_ts - ta)
            - h_ground * (new_ts - tsub)
            - le
        )
        delta_max = float(np.nanmax(np.abs(new_ts - ts)))
        residual_max = float(np.nanmax(np.abs(new_residual)))
        ts = new_ts
        # Importante: el clipping en un límite puede dejar Ts sin cambios
        # aunque el balance NO esté cerrado. Por eso no declaramos
        # convergencia solo por ΔT; exigimos también cierre energético.
        if delta_max <= cfg.tolerance_k and residual_max <= cfg.residual_tolerance_wm2:
            converged = True
            break

    q_lw_emit = eps * SIGMA * ts**4
    q_conv = hc * (ts - ta)
    q_ground = h_ground * (ts - tsub)
    residual = q_sw_abs + q_lw_in - q_lw_emit - q_conv - q_ground - le
    max_abs_residual = float(np.nanmax(np.abs(residual)))
    at_lower = np.isclose(ts, cfg.min_surface_k, rtol=0.0, atol=max(cfg.tolerance_k, 1e-8))
    at_upper = np.isclose(ts, cfg.max_surface_k, rtol=0.0, atol=max(cfg.tolerance_k, 1e-8))
    boundary_clipped = bool(np.any((at_lower | at_upper) & (np.abs(residual) > cfg.residual_tolerance_wm2)))

    return {
        "surface_temp_k": ts,
        "q_shortwave_absorbed": q_sw_abs,
        "q_longwave_down_absorbed": q_lw_in,
        "q_longwave_emitted": q_lw_emit,
        "q_convection": q_conv,
        "q_ground": q_ground,
        "q_latent": le,
        "residual_wm2": residual,
        "max_abs_residual_wm2": max_abs_residual,
        "boundary_clipped": boundary_clipped,
        "sky_emissivity": eps_sky,
        "longwave_down_wm2": float(np.mean(l_down)),
        "longwave_down_field_wm2": l_down,
        "ground_conductance_wm2k": h_ground,
        "iterations": iterations,
        "converged": converged,
        "model": "surface_energy_advanced_v1",
    }


def surface_diagnostics_summary(diagnostics):
    """Estado del solver para UI, animación y persistencia; sin matrices."""
    if not diagnostics or "converged" not in diagnostics:
        return {"status": "not_applicable", "converged": None, "boundary_clipped": None,
                "iterations": None, "max_abs_residual_wm2": None, "warnings": []}
    converged = bool(diagnostics["converged"])
    clipped = bool(diagnostics.get("boundary_clipped", False))
    warnings = []
    if not converged:
        warnings.append("El balance superficial no convergió; interpretar con cautela")
    if clipped:
        warnings.append("La temperatura superficial alcanzó un límite del solver")
    return {"status": "ok" if converged and not clipped else "warning", "converged": converged,
            "boundary_clipped": clipped, "iterations": int(diagnostics.get("iterations", 0)),
            "max_abs_residual_wm2": float(diagnostics.get("max_abs_residual_wm2", 0.0)),
            "warnings": warnings}
