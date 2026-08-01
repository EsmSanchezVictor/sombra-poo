import math
import warnings

import numpy as np
import pytest

from modelo_con_excel import (
    Arbol, Estructura, MATERIALES_LOWER, asignar_materiales_grilla,
    calcular_coeficiente_conveccion, calcular_sombra_arboles, materiales,
    sombra_estructuras, temperatura_ambiente,
)
from motor_solar import MotorSolar


def test_material_lookup_is_case_insensitive():
    X, Y = np.meshgrid(np.arange(3.0), np.arange(3.0))
    estructura = Estructura("Galeria", 0, 0, 2, 2, material="Hormigón")
    alpha, epsilon = asignar_materiales_grilla(X, Y, [estructura])
    assert np.all(alpha == materiales["Hormigón"].alpha)
    assert np.all(epsilon == materiales["Hormigón"].epsilon)
    assert materiales["Hormigón"].alpha != materiales["suelo"].alpha


def test_material_properties_are_physical():
    assert MATERIALES_LOWER["composite madera-plástico"].alpha == 0.7
    for material in materiales.values():
        assert 0 < material.alpha <= 1
        assert 0 < material.epsilon <= 1


def test_temperature_extrema_are_shifted():
    assert temperatura_ambiente(6, 280, 310) == pytest.approx(280)
    assert temperatura_ambiente(15, 280, 310) == pytest.approx(310)


def test_convection_increases_with_wind():
    valores = [calcular_coeficiente_conveccion(v) for v in (0, 2, 4, 10)]
    assert valores == sorted(valores)
    assert len(set(valores)) == len(valores)


def test_tree_shadow_elongates_at_low_sun():
    axis = np.linspace(-30, 30, 601)
    X, Y = np.meshgrid(axis, axis)
    arbol = Arbol(0, 0, 5, 1, 2)
    high = np.count_nonzero(calcular_sombra_arboles(X, Y, [arbol], math.radians(90), 0) == 0)
    low = np.count_nonzero(calcular_sombra_arboles(X, Y, [arbol], math.radians(20), 0) == 0)
    assert low > high
    assert high * (axis[1] - axis[0]) ** 2 == pytest.approx(math.pi * 4, rel=0.04)


def test_wall_shadow_is_smaller_than_old_bounding_box():
    axis = np.linspace(-15, 15, 301)
    X, Y = np.meshgrid(axis, axis)
    pared = Estructura("Pared", 0, 0, 8, 2, altura=5)
    theta, azimuth = math.radians(35), math.radians(45)
    actual = sombra_estructuras(X, Y, [pared], theta, azimuth) > 0
    length = pared.altura / math.tan(theta)
    dx, dy = -length * math.sin(azimuth), -length * math.cos(azimuth)
    old = ((X >= min(0, 8, dx, 8 + dx)) & (X <= max(0, 8, dx, 8 + dx))
           & (Y >= min(0, 2, dy, 2 + dy)) & (Y <= max(0, 2, dy, 2 + dy)))
    assert actual.sum() <= old.sum()
    assert not np.any(actual & ~old)


@pytest.mark.parametrize("fecha,lat,lon,elevacion,azimut", [
    ("2024-03-20 12:00", 0, 0, 88.03, 91.92),
    ("2024-06-21 12:00", 40, 0, 73.45, 178.75),
    ("2024-12-21 12:00", -35, 0, 78.42, 358.05),
])
def test_solar_fallback_golden_values(fecha, lat, lon, elevacion, azimut):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        motor = MotorSolar(lat, lon, "UTC")
        motor.location = None  # fuerza el fallback para fijar sus regresiones
        result = motor.obtener_posicion_y_radiacion(fecha)
    assert result["elevacion"] == pytest.approx(elevacion, abs=0.3)
    assert result["azimut"] == pytest.approx(azimut, abs=1.0)

@pytest.mark.parametrize("fecha,lat,lon", [
    ("2024-03-20 12:00", 0, 0),
    ("2024-06-21 12:00", 40, -3),
    ("2024-12-21 15:00", -32, -60),
])
def test_motor_matches_pvlib(fecha, lat, lon):
    pvlib = pytest.importorskip("pvlib")
    import pandas as pd
    instant = pd.DatetimeIndex([pd.Timestamp(fecha, tz="UTC")])
    expected = pvlib.location.Location(lat, lon, tz="UTC").get_solarposition(instant).iloc[0]
    actual = MotorSolar(lat, lon, "UTC").obtener_posicion_y_radiacion(fecha)
    assert actual["elevacion"] == pytest.approx(expected["elevation"], abs=0.01)
    assert actual["azimut"] == pytest.approx(expected["azimuth"], abs=0.01)