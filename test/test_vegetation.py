import math

import numpy as np
import pytest

from core.vegetation import (
    phenology_factor,
    hourly_fao56_reference_et0_mm_h,
    ground_latent_heat_flux_wm2,
)
from core.species import propiedades_especie, validar_especie
from modelo_con_excel import (
    Arbol,
    Estructura,
    calcular_campo_termico_superficie,
    calcular_sombra_arboles_fenologica,
)


def test_deciduous_phenology_follows_hemisphere():
    # Hemisferio sur: enero ~ verano, julio ~ invierno.
    assert phenology_factor(20, -32.0, True) > phenology_factor(200, -32.0, True)
    # Hemisferio norte: relación inversa.
    assert phenology_factor(200, 40.0, True) > phenology_factor(20, 40.0, True)
    assert phenology_factor(200, -32.0, False) == pytest.approx(1.0)


def test_fao56_hourly_et0_responds_to_radiation():
    low = float(hourly_fao56_reference_et0_mm_h(
        air_temp_c=25, rh_pct=50, wind_speed_2m_mps=2,
        net_radiation_wm2=100,
    ))
    high = float(hourly_fao56_reference_et0_mm_h(
        air_temp_c=25, rh_pct=50, wind_speed_2m_mps=2,
        net_radiation_wm2=500,
    ))
    assert high > low >= 0


def test_ground_latent_flux_zero_without_water_or_vegetation():
    base = dict(
        air_temp_k=298.15, rh_pct=45, wind=2.0,
        incident_shortwave_wm2=800.0, longwave_down_wm2=400.0,
    )
    dry = ground_latent_heat_flux_wm2(
        **base, vegetation_fraction=1.0, water_availability=0.0,
    )
    bare = ground_latent_heat_flux_wm2(
        **base, vegetation_fraction=0.0, water_availability=1.0,
    )
    assert float(dry["latent_heat_flux_wm2"]) == pytest.approx(0.0)
    assert float(bare["latent_heat_flux_wm2"]) == pytest.approx(0.0)


def test_species_have_v13_vegetation_defaults_and_validation():
    p = propiedades_especie("Plátano (Platanus × acerifolia)")
    assert 0.1 <= p["lai_tipico"] <= 10
    assert 0.1 <= p["kc_et"] <= 2
    assert 0 <= p["transmitancia_sin_hojas"] <= 1

    base = dict(p)
    base["ref"] = "test"
    ok, err = validar_especie("Prueba", dict(base, lai_tipico=11))
    assert not ok and "lai_tipico" in err
    ok, err = validar_especie("Prueba", dict(base, kc_et=0))
    assert not ok and "kc_et" in err


def test_advanced_vegetation_cools_vegetated_surface_and_closes_balance():
    X, Y = np.meshgrid(np.linspace(0, 10, 21), np.linspace(0, 10, 21))
    common = {
        "arboles": [], "estructuras": [], "viento": 2.0,
        "humedad": 45.0, "nubosidad": "Despejado",
        "dia": 20, "lat": -32.0,
    }
    dry_vars = dict(common, _surface_model_mode="advanced")
    veg_vars = dict(
        common,
        _surface_model_mode="advanced_vegetation",
        _ground_vegetation_fraction=1.0,
        _vegetation_water_availability=1.0,
        _canopy_water_availability=1.0,
    )
    dry = calcular_campo_termico_superficie(
        dry_vars, X, Y, math.radians(60), 0.0, 850.0, 298.15
    )
    veg = calcular_campo_termico_superficie(
        veg_vars, X, Y, math.radians(60), 0.0, 850.0, 298.15
    )
    assert veg["model"] == "advanced_vegetation"
    assert np.mean(veg["T"]) < np.mean(dry["T"])
    assert np.mean(veg["diagnostics"]["q_latent"]) > 0
    assert np.max(np.abs(veg["diagnostics"]["residual_wm2"])) < 1e-4


def test_advanced_vegetation_without_water_matches_dry_when_no_trees():
    X, Y = np.meshgrid(np.linspace(0, 10, 11), np.linspace(0, 10, 11))
    common = {
        "arboles": [], "estructuras": [], "viento": 2.0,
        "humedad": 45.0, "nubosidad": "Despejado", "dia": 20, "lat": -32.0,
    }
    dry = calcular_campo_termico_superficie(
        dict(common, _surface_model_mode="advanced"),
        X, Y, math.radians(60), 0.0, 850.0, 298.15,
    )
    veg = calcular_campo_termico_superficie(
        dict(common, _surface_model_mode="advanced_vegetation",
             _ground_vegetation_fraction=1.0,
             _vegetation_water_availability=0.0),
        X, Y, math.radians(60), 0.0, 850.0, 298.15,
    )
    assert np.allclose(veg["T"], dry["T"], atol=1e-8)


def test_sendero_has_no_ground_et():
    X, Y = np.meshgrid(np.linspace(0, 10, 21), np.linspace(0, 10, 21))
    path = Estructura("Sendero", 4, 0, 6, 10, material="asfalto")
    vars_ = {
        "_surface_model_mode": "advanced_vegetation",
        "_ground_vegetation_fraction": 1.0,
        "_vegetation_water_availability": 1.0,
        "arboles": [], "estructuras": [path], "viento": 2.0,
        "humedad": 45.0, "nubosidad": "Despejado", "dia": 20, "lat": -32.0,
    }
    r = calcular_campo_termico_superficie(
        vars_, X, Y, math.radians(60), 0.0, 850.0, 298.15
    )
    le = np.asarray(r["diagnostics"]["q_latent"])
    inside = (X >= 4) & (X <= 6)
    outside = ~inside
    assert np.max(le[inside]) == pytest.approx(0.0)
    assert np.mean(le[outside]) > 0


def test_deciduous_tree_transmits_more_in_winter_southern_hemisphere():
    X, Y = np.meshgrid(np.linspace(-20, 20, 81), np.linspace(-20, 20, 81))
    tree = Arbol(0, 0, 8, 0.75, 4)
    tree.especie = "Plátano (Platanus × acerifolia)"
    theta = math.radians(60)
    summer, _ = calcular_sombra_arboles_fenologica(X, Y, [tree], theta, 0.0, 20, -32)
    winter, _ = calcular_sombra_arboles_fenologica(X, Y, [tree], theta, 0.0, 200, -32)
    # En la región afectada por sombra, mayor tau = más radiación transmitida.
    assert np.min(winter) > np.min(summer)
