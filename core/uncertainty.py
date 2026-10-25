"""Análisis operativo de incertidumbre/sensibilidad para Tmrt (v15).

No pretende convertir supuestos en "intervalos de confianza" instrumentales.
Es una propagación Monte Carlo de incertidumbres configuradas/operativas que
sirve para mostrar cuánto pueden mover el resultado las entradas y parámetros.
El reporte la etiqueta explícitamente como *intervalo operativo*.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Any

import numpy as np

from core.radiative_tmrt import (
    AdvancedTmrtConfig,
    calculate_radiative_tmrt,
    projected_area_factor_standing,
)


@dataclass(frozen=True)
class OperationalUncertaintyConfig:
    air_temp_sigma_c: float = 0.5
    tau_sigma_abs: float = 0.05
    k_relative_sigma: float = 0.15
    modeled_radiation_relative_sigma: float = 0.12
    observed_radiation_relative_sigma: float = 0.04
    interpolated_radiation_relative_sigma: float = 0.06
    scenario_radiation_relative_sigma: float = 0.10
    advanced_absorptivity_sigma: float = 0.03
    advanced_projected_factor_sigma: float = 0.03
    advanced_ground_albedo_sigma: float = 0.05
    samples: int = 800
    seed: int = 20260830

    def validated(self) -> "OperationalUncertaintyConfig":
        if int(self.samples) < 100:
            raise ValueError("samples debe ser >= 100.")
        for name, val in asdict(self).items():
            if name in {"samples", "seed"}:
                continue
            if not math.isfinite(float(val)) or float(val) < 0:
                raise ValueError(f"{name} debe ser finito y no negativo.")
        return self


def radiation_relative_sigma(quality: str | None, cfg: OperationalUncertaintyConfig) -> float:
    q = str(quality or "").lower()
    if "interpolated" in q:
        return cfg.interpolated_radiation_relative_sigma
    if "measured" in q or q == "observed":
        return cfg.observed_radiation_relative_sigma
    if "scenario" in q or "prescribed" in q:
        return cfg.scenario_radiation_relative_sigma
    return cfg.modeled_radiation_relative_sigma


def _summary(values: np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"p05": math.nan, "p50": math.nan, "p95": math.nan, "std": math.nan}
    return {
        "p05": float(np.percentile(arr, 5)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
    }


def _corr(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def estimate_tmrt_uncertainty(
    *,
    air_temp_c: float,
    tau: float,
    ghi: float,
    solar_elevation_deg: float,
    model_mode: str,
    k_factor: float = 0.04,
    dni: float | None = None,
    dhi: float | None = None,
    source_quality: str | None = None,
    advanced_config: AdvancedTmrtConfig | None = None,
    config: OperationalUncertaintyConfig | None = None,
) -> dict[str, Any]:
    cfg = (config or OperationalUncertaintyConfig()).validated()
    adv_cfg = (advanced_config or AdvancedTmrtConfig()).validated()
    rng = np.random.default_rng(int(cfg.seed))
    n = int(cfg.samples)

    ta0 = float(air_temp_c)
    tau0 = min(1.0, max(0.0, float(tau)))
    ghi0 = max(0.0, float(ghi))
    rad_rel = radiation_relative_sigma(source_quality, cfg)

    ta = rng.normal(ta0, cfg.air_temp_sigma_c, n)
    rad_scale = np.maximum(0.0, rng.normal(1.0, rad_rel, n))
    ghi_s = ghi0 * rad_scale
    tau_s = np.clip(rng.normal(tau0, cfg.tau_sigma_abs, n), 0.0, 1.0)

    mode = str(model_mode or "standard").lower()
    if mode == "advanced":
        tmrt_sun = np.empty(n, dtype=float)
        tmrt_shade = np.empty(n, dtype=float)
        alpha = np.clip(rng.normal(adv_cfg.shortwave_absorptivity, cfg.advanced_absorptivity_sigma, n), 0.0, 1.0)
        fp_base = (
            projected_area_factor_standing(solar_elevation_deg)
            if adv_cfg.projected_area_mode == "elevation"
            else adv_cfg.projected_area_factor
        )
        projected = np.clip(rng.normal(fp_base, cfg.advanced_projected_factor_sigma, n), 0.0, 1.0)
        albedo = np.clip(rng.normal(adv_cfg.ground_albedo, cfg.advanced_ground_albedo_sigma, n), 0.0, 1.0)
        dni0 = None if dni is None else max(0.0, float(dni))
        dhi0 = None if dhi is None else max(0.0, float(dhi))
        for i in range(n):
            local_cfg = AdvancedTmrtConfig(
                shortwave_absorptivity=float(alpha[i]),
                longwave_emissivity=adv_cfg.longwave_emissivity,
                projected_area_factor=float(projected[i]),
                angular_factor=adv_cfg.angular_factor,
                ground_albedo=float(albedo[i]),
                # f_p muestreado (centrado en f_p(elevación) si el modo es
                # "elevation"): se aplica como valor fijo en cada muestra.
                projected_area_mode="fixed",
            )
            dni_i = None if dni0 is None else dni0 * rad_scale[i]
            dhi_i = None if dhi0 is None else dhi0 * rad_scale[i]
            tmrt_sun[i] = calculate_radiative_tmrt(
                ta[i], 1.0, ghi_s[i], solar_elevation_deg,
                dni=dni_i, dhi=dhi_i, config=local_cfg,
            )["tmrt_c"]
            tmrt_shade[i] = calculate_radiative_tmrt(
                ta[i], tau_s[i], ghi_s[i], solar_elevation_deg,
                dni=dni_i, dhi=dhi_i, config=local_cfg,
            )["tmrt_c"]
        drivers = {
            "T aire": ta,
            "radiación": rad_scale,
            "transmitancia": tau_s,
            "absorptividad humana": alpha,
            "factor proyectado": projected,
            "albedo suelo": albedo,
        }
    else:
        k = np.maximum(0.0, rng.normal(float(k_factor), abs(float(k_factor)) * cfg.k_relative_sigma, n))
        tmrt_sun = ta + k * ghi_s
        tmrt_shade = ta + k * ghi_s * tau_s
        drivers = {
            "T aire": ta,
            "radiación": rad_scale,
            "transmitancia": tau_s,
            "k_factor": k,
        }

    delta = tmrt_sun - tmrt_shade
    sensitivity = sorted(
        (
            {"driver": name, "correlation": _corr(values, tmrt_shade)}
            for name, values in drivers.items()
        ),
        key=lambda d: abs(d["correlation"]),
        reverse=True,
    )
    return {
        "method": "operational_monte_carlo_v1",
        "model_mode": mode,
        "samples": n,
        "source_quality": source_quality,
        "radiation_relative_sigma": float(rad_rel),
        "tmrt_sun": _summary(tmrt_sun),
        "tmrt_shade": _summary(tmrt_shade),
        "delta_tmrt": _summary(delta),
        "sensitivity": sensitivity,
        "assumptions": asdict(cfg),
        "interpretation": (
            "Intervalo operativo de sensibilidad (P05-P95) basado en supuestos de incertidumbre; "
            "no es un intervalo de confianza validado ni sustituye especificaciones instrumentales."
        ),
    }
