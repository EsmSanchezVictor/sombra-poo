import math

import numpy as np
import pytest

from core.materials import (
    get_surface_material,
    effective_structure_transmittance,
)
from core.surface_energy import (
    all_sky_emissivity,
    clear_sky_emissivity_brutsaert,
    solve_surface_energy_balance,
)
from modelo_con_excel import (
    Estructura,
    calcular_campo_termico_superficie,
    transmitancia_estructuras_avanzada,
)


def test_advanced_material_optical_closure():
    for name in ["suelo", "asfalto", "Vidrio templado", "policarbonato", "ETFE"]:
        mat = get_surface_material(name)
        assert mat.optical_closure == pytest.approx(1.0, abs=1e-10)
        assert 0 <= mat.solar_transmittance <= 1
        assert 0 < mat.longwave_emissivity <= 1


def test_transparent_structure_transmits_more_than_opaque():
    glass = effective_structure_transmittance("Vidrio templado", 1.0)
    asphalt = effective_structure_transmittance("asfalto", 1.0)
    assert glass == pytest.approx(0.84)
    assert asphalt == pytest.approx(0.0)
    assert glass > asphalt
    # 50 % de ocupación geométrica deja abierta la otra mitad.
    assert effective_structure_transmittance("Vidrio templado", 0.5) == pytest.approx(0.92)


def test_brutsaert_emissivity_increases_with_humidity():
    dry = clear_sky_emissivity_brutsaert(298.15, 20.0)
    humid = clear_sky_emissivity_brutsaert(298.15, 80.0)
    assert 0 < dry < humid <= 1


def test_clouds_increase_effective_sky_emissivity():
    clear = all_sky_emissivity(298.15, 50.0, 0.0)
    partial = all_sky_emissivity(298.15, 50.0, 0.5)
    overcast = all_sky_emissivity(298.15, 50.0, 1.0)
    assert clear < partial < overcast
    assert overcast == pytest.approx(1.0)


def test_surface_energy_closes_and_solar_heats_surface():
    common = dict(
        air_temp_k=298.15,
        solar_absorptance=0.90,
        longwave_emissivity=0.95,
        convective_coefficient_wm2k=13.3,
        thermal_conductivity_wmk=0.75,
        coupling_depth_m=0.15,
        rh_pct=45.0,
        cloud_fraction=0.0,
    )
    night = solve_surface_energy_balance(incident_shortwave_wm2=0.0, **common)
    sun = solve_surface_energy_balance(incident_shortwave_wm2=850.0, **common)
    assert float(sun["surface_temp_k"]) > float(night["surface_temp_k"])
    assert np.max(np.abs(sun["residual_wm2"])) < 1e-4
    assert sun["converged"]


def test_clear_sky_can_cool_surface_below_air_without_sun():
    r = solve_surface_energy_balance(
        air_temp_k=298.15,
        incident_shortwave_wm2=0.0,
        solar_absorptance=0.7,
        longwave_emissivity=0.95,
        convective_coefficient_wm2k=8.0,
        thermal_conductivity_wmk=0.8,
        coupling_depth_m=0.25,
        rh_pct=40,
        cloud_fraction=0.0,
    )
    assert float(r["surface_temp_k"]) < 298.15


def test_advanced_structure_map_uses_material_transmittance():
    axis = np.linspace(-5, 15, 101)
    X, Y = np.meshgrid(axis, axis)
    theta = math.radians(60)
    az = math.radians(180)
    glass = Estructura("Galeria", 0, 0, 10, 10, altura=0, opacidad=1, material="Vidrio templado")
    opaque = Estructura("Galeria", 0, 0, 10, 10, altura=0, opacidad=1, material="asfalto")
    tg = transmitancia_estructuras_avanzada(X, Y, [glass], theta, az)
    to = transmitancia_estructuras_avanzada(X, Y, [opaque], theta, az)
    inside = (X > 1) & (X < 9) & (Y > 1) & (Y < 9)
    assert np.nanmedian(tg[inside]) == pytest.approx(0.84, abs=0.01)
    assert np.nanmedian(to[inside]) == pytest.approx(0.0, abs=0.01)


def test_standard_surface_core_preserves_legacy_formula():
    X, Y = np.meshgrid(np.linspace(0, 10, 5), np.linspace(0, 10, 5))
    vars_ = {
        "_surface_model_mode": "standard",
        "arboles": [],
        "estructuras": [],
        "viento": 2.0,
        "humedad": 50.0,
        "nubosidad": "Despejado",
    }
    ta = 298.15
    I = 800.0
    r = calcular_campo_termico_superficie(vars_, X, Y, math.radians(60), 0.0, I, ta)
    # Suelo legacy: alpha=.4, epsilon=.9; sin sombra tau=1.
    hc = 5.7 + 3.8 * 2.0
    hr = 4 * 0.9 * 5.67e-8 * ta**3
    expected = ta + 0.4 * I / (hc + hr)
    assert np.allclose(r["T"], expected)
    assert r["model"] == "standard"


def test_advanced_surface_core_is_distinct_and_finite():
    X, Y = np.meshgrid(np.linspace(0, 10, 5), np.linspace(0, 10, 5))
    vars_ = {
        "_surface_model_mode": "advanced",
        "arboles": [],
        "estructuras": [],
        "viento": 2.0,
        "humedad": 45.0,
        "nubosidad": "Despejado",
    }
    r = calcular_campo_termico_superficie(
        vars_, X, Y, math.radians(60), 0.0, 800.0, 298.15
    )
    assert np.all(np.isfinite(r["T"]))
    assert r["model"] == "advanced"
    assert np.max(np.abs(r["diagnostics"]["residual_wm2"])) < 1e-4


def test_opaque_gallery_replaces_clear_sky_longwave_and_avoids_excess_cooling():
    X, Y = np.meshgrid(np.linspace(0, 10, 21), np.linspace(0, 10, 21))
    roof = Estructura("Galeria", 0, 0, 10, 10, altura=0, opacidad=1, material="asfalto")
    vars_ = {
        "_surface_model_mode": "advanced",
        "arboles": [],
        "estructuras": [roof],
        "viento": 2.0,
        "humedad": 45.0,
        "nubosidad": "Despejado",
    }
    r = calcular_campo_termico_superficie(vars_, X, Y, math.radians(60), 0.0, 850.0, 298.15)
    center_c = float(r["T"][10, 10] - 273.15)
    # Sin SW bajo cubierta, el modelo no debe tratar el punto como cielo abierto
    # y enfriarlo varios grados por radiación hacia un cielo despejado.
    assert 22.0 < center_c < 27.0
