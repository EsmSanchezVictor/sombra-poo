"""Etapa 4 · f_p dependiente de la elevación solar (modelo advanced_radiative_v2).

Desde esta etapa el modo predeterminado es ``"elevation"`` (Jendritzky et al.
1990). El modelo v1 (f_p fijo = 0.28) sigue disponible con
``AdvancedTmrtConfig(projected_area_mode="fixed")`` y se fija con valores de
regresión obtenidos en v35.6-etapa3.2 para poder reproducir resultados viejos.
"""
import pytest

from core.model_registry import TMRT_MODELS
from core.radiative_tmrt import (
    AdvancedTmrtConfig,
    calculate_radiative_tmrt,
    projected_area_factor_standing,
)
from core.uncertainty import OperationalUncertaintyConfig, estimate_tmrt_uncertainty

# Caso de verano al mediodía (Ta 34 °C, elevación 82°, cielo despejado)
CASO = dict(ghi=1050.0, solar_elevation_deg=82.0, dni=850.0, dhi=130.0)
LEGADO = AdvancedTmrtConfig(projected_area_mode="fixed")


def test_default_is_elevation_model_v2():
    cfg = AdvancedTmrtConfig()
    assert cfg.projected_area_mode == "elevation"
    r = calculate_radiative_tmrt(34.0, 1.0, **CASO)
    assert r["model"] == "advanced_radiative_v2"
    assert r["projected_area_factor_used"] == pytest.approx(
        projected_area_factor_standing(82.0)
    )
    assert TMRT_MODELS["advanced"]["version"] == "advanced_radiative_v2"


def test_legacy_fixed_mode_reproduces_v1_exactly():
    sol = calculate_radiative_tmrt(34.0, 1.0, config=LEGADO, **CASO)
    sombra = calculate_radiative_tmrt(34.0, 0.3, config=LEGADO, **CASO)
    # Valores de v35.6-etapa3.2 (antes del cambio).
    assert sol["tmrt_c"] == pytest.approx(71.3972227153435, abs=1e-9)
    assert sombra["tmrt_c"] == pytest.approx(46.63792888787964, abs=1e-9)
    assert sol["projected_area_factor_used"] == pytest.approx(0.28)
    assert sol["model"] == "advanced_radiative_v1"


def test_standing_fp_reference_points_and_monotonic():
    assert projected_area_factor_standing(0.0) == pytest.approx(0.308, abs=1e-9)
    assert projected_area_factor_standing(82.0) == pytest.approx(0.101, abs=0.002)
    valores = [projected_area_factor_standing(a) for a in range(0, 91, 5)]
    assert all(b < a for a, b in zip(valores, valores[1:]))
    # Fuera de rango se acota en vez de extrapolar.
    assert projected_area_factor_standing(-20) == projected_area_factor_standing(0)
    assert projected_area_factor_standing(120) == projected_area_factor_standing(90)


def test_v1_overestimates_noon_summer_tmrt_but_not_low_sun():
    v2 = calculate_radiative_tmrt(34.0, 1.0, **CASO)["tmrt_c"]
    v1 = calculate_radiative_tmrt(34.0, 1.0, config=LEGADO, **CASO)["tmrt_c"]
    assert v1 - v2 > 8.0  # sobreestimación del modo fijo con sol alto
    bajo = dict(ghi=450.0, solar_elevation_deg=25.0, dni=700.0, dhi=70.0)
    v2b = calculate_radiative_tmrt(34.0, 1.0, **bajo)["tmrt_c"]
    v1b = calculate_radiative_tmrt(34.0, 1.0, config=LEGADO, **bajo)["tmrt_c"]
    assert abs(v1b - v2b) < 1.5  # con sol bajo ambos modos casi coinciden


def test_default_keeps_physical_invariants():
    noche = calculate_radiative_tmrt(25.0, 1.0, 0.0, -2.0)
    assert noche["tmrt_c"] == pytest.approx(25.0, abs=1e-6)
    previo = calculate_radiative_tmrt(34.0, 1.0, **CASO)["tmrt_c"]
    assert previo > 34.0
    for tau in (0.6, 0.3, 0.15, 0.05):  # más sombra -> menos Tmrt
        t = calculate_radiative_tmrt(34.0, tau, **CASO)["tmrt_c"]
        assert t < previo
        previo = t


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        AdvancedTmrtConfig(projected_area_mode="otro").validated()


def test_uncertainty_default_and_legacy_are_reproducible_and_distinct():
    base = dict(
        air_temp_c=34.0, tau=0.3, ghi=1050.0, solar_elevation_deg=82.0,
        model_mode="advanced", dni=850.0, dhi=130.0,
        config=OperationalUncertaintyConfig(samples=200, seed=7),
    )
    a = estimate_tmrt_uncertainty(**base)
    assert a == estimate_tmrt_uncertainty(**base)
    legado = estimate_tmrt_uncertainty(advanced_config=LEGADO, **base)
    assert legado != a  # el modo fijo da otra distribución con sol alto
