import math

import numpy as np
import pytest

from modelo_con_excel import (
    Arbol, Estructura, MATERIALES_LOWER, asignar_materiales_grilla,
    angulo_solar, azimut_solar, calcular_coeficiente_conveccion,
    calcular_sombra_arboles, ecuacion_del_tiempo, materiales,
    sombra_estructuras, temperatura_ambiente, _meridiano_estandar,
)
from services.solar_engine import SolarEngine
from shadow_temp import Temperatura


# ---------------------------------------------------------------- materiales

def test_material_lookup_is_case_insensitive():
    X, Y = np.meshgrid(np.arange(3.0), np.arange(3.0))
    estructura = Estructura("Sendero", 0, 0, 2, 2, material="Hormigón")
    alpha, epsilon = asignar_materiales_grilla(X, Y, [estructura])
    assert np.all(alpha == materiales["Hormigón"].alpha)
    assert np.all(epsilon == materiales["Hormigón"].epsilon)
    assert materiales["Hormigón"].alpha != materiales["suelo"].alpha


def test_unknown_material_falls_back_to_suelo_without_crashing():
    X, Y = np.meshgrid(np.arange(3.0), np.arange(3.0))
    estructura = Estructura("Sendero", 0, 0, 2, 2, material="MaterialInexistente")
    alpha, epsilon = asignar_materiales_grilla(X, Y, [estructura])
    assert np.all(alpha == materiales["suelo"].alpha)


def test_material_properties_are_physical():
    assert MATERIALES_LOWER["composite madera-plástico"].alpha == 0.7
    for material in materiales.values():
        assert 0 < material.alpha <= 1
        assert 0 < material.epsilon <= 1


# ---------------------------------------------------------------- T_aire

def test_temperature_extrema_are_shifted():
    assert temperatura_ambiente(6, 280, 310) == pytest.approx(280)
    assert temperatura_ambiente(15, 280, 310) == pytest.approx(310)


def test_temperature_does_not_reapproach_max_at_midnight():
    """Regresión del bug (v4): la sinusoide de período fijo 18h, sin
    recortar fuera de [hora_min, hora_max], volvía a acercarse a T_max
    cerca de medianoche. Con T_min=18/T_max=30 el bug daba 27°C a las
    0h — casi el máximo del día en el peor momento posible. Ahora debe
    quedar acotada en [T_min, T_max] y bien cerca de T_min a esa hora.
    """
    valor = temperatura_ambiente(0, 18.0, 30.0)
    assert 18.0 <= valor <= 30.0
    assert valor < 25.0  # el bug original daba 27.0


def test_convection_increases_with_wind():
    valores = [calcular_coeficiente_conveccion(v) for v in (0, 2, 4, 10)]
    assert valores == sorted(valores)
    assert len(set(valores)) == len(valores)
    # McAdams: h = 5.7 + 3.8·v
    assert calcular_coeficiente_conveccion(0) == pytest.approx(5.7)
    assert calcular_coeficiente_conveccion("moderado") == pytest.approx(5.7 + 3.8 * 4)


# ---------------------------------------------------------------- sombras

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


# ------------------------------------------------------- geometría solar

def test_meridiano_estandar_heuristica_y_explicito():
    # Buenos Aires: lon -58.38 => heurística round(-3.9) = -4 h => -60°;
    # el huso real es -3 h => -45° (el error de la heurística es la razón
    # por la que conviene pasarlo explícito cuando se conoce).
    assert _meridiano_estandar(-58.38) == pytest.approx(-60.0)
    assert _meridiano_estandar(-58.38, huso_horas=-3) == pytest.approx(-45.0)
    assert _meridiano_estandar(0.0) == 0.0


def test_ecuacion_del_tiempo_es_pequena_y_simetrica():
    # EoT en grados: acotada a ±4° y ~0 cerca de mediados de abril y junio.
    assert abs(ecuacion_del_tiempo(80)) < 4
    assert abs(ecuacion_del_tiempo(105)) < 1
    # Febrero: EoT ~ -14 min ≈ -3.5°
    assert ecuacion_del_tiempo(44) == pytest.approx(-3.5, abs=0.5)


def test_solar_noon_local_coincide_con_mediodia_solar():
    # Equinoccio (día 80) en Buenos Aires: el mediodía solar local ocurre
    # cuando el sol cruza el meridiano (H=0). Con lon -58.38 y huso -3 el
    # sol llega al meridiano ~0.89 h después del mediodía del reloj (BsAs
    # está al este del meridiano -45°), así que la elevación máxima del
    # día debe darse a ~13:02 local y valer 90 − |lat − δ|.
    calc = Temperatura(latitude=-34.6037, longitude=-58.3816, tz_offset_hours=-3)
    horas = np.linspace(6, 18, 2401)
    elevs = np.array([calc.solar_altitude(80, h) for h in horas])
    idx = int(np.argmax(elevs))
    decl = calc.solar_declination(80)
    assert elevs[idx] == pytest.approx(90 - abs(-34.6037 - decl), abs=0.3)
    # H=0 => hora_solar = 12 => local = 12 − (lon − meridiano)/15 − EoT/15
    local_solar_noon = 12 - (-58.3816 + 45.0) / 15 - ecuacion_del_tiempo(80) / 15
    assert horas[idx] == pytest.approx(local_solar_noon, abs=0.05)


def test_angulo_solar_y_shadow_temp_consistentes():
    # Ambos módulos deben dar la misma elevación para los mismos datos.
    lat, lon, dia, hora, huso = -34.6037, -58.3816, 80, 12.0, -3
    modelo_elev = angulo_solar(lat, lon, dia, hora, huso)
    temp_elev = math.radians(Temperatura(lat, lon, tz_offset_hours=huso).solar_altitude(dia, hora))
    assert modelo_elev == pytest.approx(temp_elev, abs=1e-9)


# ---------------------------------------------------------- Tmrt (modelo)

def test_shadow_transmittance_semantica_cobertura():
    calc = Temperatura()
    # 0 % de sombra = pleno sol, nunca debe enfriar por sí solo.
    assert calc.shadow_transmittance(0, "tree") == pytest.approx(1.0)
    assert calc.shadow_transmittance(0, "structure") == pytest.approx(1.0)
    assert calc.shadow_transmittance(100, "tree") == pytest.approx(0.15)
    assert calc.shadow_transmittance(100, "structure") == pytest.approx(0.05)
    assert calc.shadow_transmittance(50, "tree") == pytest.approx(0.575)
    assert calc.shadow_transmittance(50, "structure") == pytest.approx(0.525)
    assert calc.shadow_transmittance(150, "tree") == pytest.approx(0.15)
    assert calc.shadow_transmittance(-10, "tree") == pytest.approx(1.0)


def test_local_air_estimate_zero_shadow_equals_reference():
    calc = Temperatura()
    assert calc.estimate_local_air_temperature(25.0, 0.0, 883.0, "tree") == pytest.approx(25.0)


def test_local_air_estimate_tree_is_moderate_and_bounded():
    calc = Temperatura()
    # Con 100 % de sombra y GHI=800 W/m², tau árbol=0.15:
    # radiación evitada=680 W/m²; ΔTa=0.0025*680=1.70 °C.
    result = calc.estimate_local_air_temperature(30.0, 100.0, 800.0, "tree")
    assert result == pytest.approx(28.30, abs=0.01)
    # Incluso con irradiancia extrema el descenso por defecto no supera 2.5 °C.
    result_extreme = calc.estimate_local_air_temperature(30.0, 100.0, 5000.0, "tree")
    assert result_extreme == pytest.approx(27.50, abs=0.01)


def test_local_air_estimate_map_increases_cooling_with_shadow():
    calc = Temperatura()
    shade = np.array([[0.0, 50.0, 100.0]], dtype=float)
    local = calc.estimate_local_air_temperature_map(25.0, shade, 900.0, "tree")
    assert local.shape == shade.shape
    assert local[0, 0] == pytest.approx(25.0)
    assert local[0, 0] > local[0, 1] > local[0, 2]
    assert local[0, 2] >= 22.5


def test_shadow_zero_percent_no_changes_tmrt():
    calc = Temperatura(-34.6, -58.4, k_factor=0.04, tz_offset_hours=-3)
    r = calc.calculate_tmrt(30.0, 0.0, date_value=__import__("datetime").date(2026, 1, 15), time_value=12)
    assert r["Tmrt_sombra"] == pytest.approx(r["Tmrt_sol"], abs=0.01)
    assert r["Delta_Tmrt"] == pytest.approx(0.0, abs=0.01)


def test_clear_sky_radiation_fisica():
    calc = Temperatura()
    assert calc.clear_sky_radiation(90) == pytest.approx(1367 * 0.75)
    assert calc.clear_sky_radiation(0) == 0.0
    assert calc.clear_sky_radiation(-5) == 0.0
    assert calc.clear_sky_radiation(45) == pytest.approx(1367 * 0.75 * math.sin(math.radians(45)))


def test_calibrate_k_factor():
    calc = Temperatura()
    k = calc.calibrate_k_factor(tmrt_medido=45.2, air_temp=30.0, radiation=750.0)
    assert k == pytest.approx((45.2 - 30.0) / 750.0)
    with pytest.raises(ValueError):
        calc.calibrate_k_factor(tmrt_medido=30.0, air_temp=30.0, radiation=0.0)


def test_calculate_tmrt_sombra_mas_fria_que_sol():
    calc = Temperatura(latitude=-34.6037, longitude=-58.3816, tz_offset_hours=-3)
    resultado = calc.calculate_tmrt(30.0, 60.0, date_value=__import__("datetime").date(2026, 2, 7), time_value=12)
    assert resultado["Tmrt_sombra"] < resultado["Tmrt_sol"]
    assert resultado["Delta_Tmrt"] > 0
    assert resultado["Transmitancia_tau"] < 1.0


# ------------------------------------------------ fallback solar vs pvlib

@pytest.mark.parametrize("fecha,lat,lon,elevacion,azimut", [
    # Valores de regresión del fallback (verificado contra pvlib en el
    # test siguiente; el caso 10:00 evita el mediodía ecuatorial, donde
    # el azimut está mal condicionado porque el sol pasa por el cenit).
    ("2024-03-20 10:00", 0, 0, 58.037, 90.763),
    ("2024-06-21 12:00", 40, 0, 73.444, 178.666),
    ("2024-12-21 12:00", -35, 0, 78.443, 358.955),
])
def test_solar_fallback_golden_values(fecha, lat, lon, elevacion, azimut):
    motor = SolarEngine(use_pvlib=False, tz="UTC")
    azim, elev = motor.get_solar_position(lat, lon, __import__("datetime").datetime.strptime(fecha, "%Y-%m-%d %H:%M"))
    assert elev == pytest.approx(elevacion, abs=0.05)
    assert azim == pytest.approx(azimut, abs=0.05)


@pytest.mark.parametrize("fecha,lat,lon,tz", [
    ("2024-03-20 10:00", 0, 0, "UTC"),
    ("2024-06-21 12:00", 40, -3, "UTC"),
    ("2024-12-21 15:00", -32, -60, "UTC"),
    ("2026-02-07 12:00", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    ("2026-08-16 09:30", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
])
def test_solar_fallback_matches_pvlib(fecha, lat, lon, tz):
    pvlib = pytest.importorskip("pvlib")
    import pandas as pd
    from datetime import datetime
    instant = pd.DatetimeIndex([pd.Timestamp(fecha, tz=tz)])
    expected = pvlib.location.Location(lat, lon, tz=tz).get_solarposition(instant).iloc[0]
    motor = SolarEngine(use_pvlib=False, tz=tz)
    azim, elev = motor.get_solar_position(lat, lon, datetime.strptime(fecha, "%Y-%m-%d %H:%M"))
    # Tolerancias holgadas de forma deliberada: el fallback usa declinación
    # y EoT analíticas con el día truncado a entero, pvlib usa fracciones
    # de día; la diferencia máxima observada es ~0.5° en elevación.
    assert elev == pytest.approx(float(expected["elevation"]), abs=0.6)
    assert azim == pytest.approx(float(expected["azimuth"]), abs=2.0)

def test_pared_diagonal_conserva_endpoints():
    pared = Estructura("Pared", 0, 10, 10, 0, altura=3)
    assert (pared.x1, pared.y1, pared.x2, pared.y2) == (0.0, 10.0, 10.0, 0.0)


def test_galeria_proyecta_sombra_con_altura():
    axis = np.linspace(-20, 20, 401)
    X, Y = np.meshgrid(axis, axis)
    gal = Estructura("Galeria", -2, -2, 2, 2, altura=4, opacidad=1)
    theta = math.radians(45)
    az = math.radians(90)
    m = sombra_estructuras(X, Y, [gal], theta, az) > 0
    # Con azimut 90° la sombra se desplaza hacia X negativa; el centro
    # sombreado no puede quedar en x=0 como en la versión antigua.
    xs = X[m]
    assert xs.size > 0
    assert float(xs.mean()) < -2.0


def test_fallback_radiation_conserva_ghi():
    from datetime import datetime
    motor = SolarEngine(use_pvlib=False, tz="America/Argentina/Buenos_Aires")
    dt = datetime(2026, 1, 15, 12, 0)
    rad = motor.get_radiation(-34.6037, -58.3816, dt)
    _, elev = motor.get_solar_position(-34.6037, -58.3816, dt)
    recomposed = rad["dni"] * math.sin(math.radians(elev)) + rad["dhi"]
    assert recomposed == pytest.approx(rad["ghi"], rel=1e-6)


def test_tmrt_map_accepts_photometric_transmittance_override():
    from shadow_temp import Temperatura
    calc = Temperatura(-34.6, -58.4, k_factor=0.04)
    shadow_map = np.array([[0.0, 100.0]], dtype=np.float32)
    tau = np.array([[1.0, 0.5]], dtype=np.float32)
    result = calc.calculate_tmrt_map(
        25.0,
        shadow_map,
        radiation_override=800.0,
        solar_altitude_override=45.0,
        transmittance_map_override=tau,
    )
    values = result["Tmrt_map"]
    assert values[0, 0] == pytest.approx(57.0, abs=1e-5)
    assert values[0, 1] == pytest.approx(41.0, abs=1e-5)


def test_local_air_map_uses_photometric_transmittance_override():
    from shadow_temp import Temperatura
    calc = Temperatura(-34.6, -58.4)
    shadow_map = np.array([[0.0, 100.0]], dtype=np.float32)
    tau = np.array([[1.0, 0.5]], dtype=np.float32)
    result = calc.estimate_local_air_temperature_map(
        25.0,
        shadow_map,
        800.0,
        transmittance_map_override=tau,
        cooling_coefficient=0.0025,
        max_cooling=2.5,
    )
    assert result[0, 0] == pytest.approx(25.0, abs=1e-6)
    assert result[0, 1] == pytest.approx(24.0, abs=1e-6)
