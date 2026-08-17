"""Tests de las herramientas de confort, escenario, validación y especies.

Convenciones de la suite: fórmulas exactas verificadas contra valores
publicados o de libro; tolerancias explícitas; casos límite cubiertos.
"""
import math
from datetime import date

import numpy as np
import pytest

from core import thermal_comfort as tc
from core.climate_profile import (atenuacion_copa, descomponer_radiacion,
                                  velocidad_viento, viento_categoria_a_ms,
                                  z0_superficie)
from core.scenario import (comparar_escenarios, escenario_horario,
                           mapa_estres, ranking_arboles,
                           resumen_escenario, temperatura_diurna)
from core.species import ESPECIES, nombres_especies
from core.validation import k_factor_desde_mediciones, leer_csv_mediciones, metricas
from modelo_con_excel import Arbol
from shadow_temp import Temperatura


# ---------------------------------------------------------------- thermal_comfort

def test_globo_negro_radiative_equilibrium():
    """Si Tg == Ta (sin calentamiento radiativo neto o viento nulo con
    radiación equilibrada) la Tmrt tiende a Ta a viento bajo."""
    tmrt = tc.globo_negro_a_tmrt(30.0, 30.0, 0.1)
    assert tmrt == pytest.approx(30.0, abs=0.15)


def test_globo_negro_viento_aumenta_transferencia():
    """ISO 7726: a más viento el globo se enfría más por convección, y
    la corrección a Tmrt es mayor — la Tmrt 'verdadera' se separa más
    del globo medido (el globo subestima la radiación cuanto más viento)."""
    tmrt_calmo = tc.globo_negro_a_tmrt(45.0, 30.0, 0.2)
    tmrt_ventoso = tc.globo_negro_a_tmrt(45.0, 30.0, 3.0)
    assert tmrt_ventoso > tmrt_calmo
    assert tmrt_calmo > 30.0


def test_indice_calor_heatwave_diario():
    """Heat Index de Rothfusz verificado contra el ejemplo del NWS:
    T=90°F, RH=60% -> HI ≈ 100°F."""
    hi_f = tc.indice_calor(32.2, 60.0) * 9 / 5 + 32
    assert hi_f == pytest.approx(100.0, abs=2.0)


def test_indice_calor_below_threshold_returns_air_temp():
    assert tc.indice_calor(20.0, 90.0) == pytest.approx(20.0)


def test_indice_calor_menor_a_ta_en_aire_seco():
    """Con aire seco y muy caluroso el ajuste del NWS baja el índice."""
    assert tc.indice_calor(38.0, 8.0) < 38.0


def test_temperatura_aparente_aumenta_con_humedad():
    at_seco = tc.temperatura_aparente(30.0, 30.0, 1.0)
    at_humedo = tc.temperatura_aparente(30.0, 85.0, 1.0)
    assert at_humedo > at_seco
    assert at_humedo > 30.0


def test_temperatura_aparente_disminuye_con_viento():
    at_calmo = tc.temperatura_aparente(30.0, 60.0, 0.5)
    at_ventoso = tc.temperatura_aparente(30.0, 60.0, 6.0)
    assert at_ventoso < at_calmo


def test_grados_hora_trapecio():
    series = [(6, 30.0), (10, 34.0), (14, 36.0), (18, 32.0)]
    gh = tc.grados_hora(series, umbral=32.0)
    # (10,34): +2 por 4h con promedio 1  -> 4
    # (14,36): +4 por 4h con promedio 3  -> 12
    # (18,32): +0 por 4h con promedio 2  -> 8
    assert gh == pytest.approx(24.0, abs=0.01)


def test_grados_hora_por_debajo():
    series = [(6, 5.0), (10, 9.0)]
    gh = tc.grados_hora(series, umbral=8.0, por_encima=False)
    # (6,5): -3 por 4h con promedio 1.5 -> 6
    assert gh == pytest.approx(6.0, abs=0.01)


def test_categorias_heat_index_nws():
    assert tc.categoria_estres(25.0, "heat") == "Sin estrés"
    assert tc.categoria_estres(30.0, "heat") == "Precaución"
    assert tc.categoria_estres(35.0, "heat") == "Mucha precaución"
    assert tc.categoria_estres(45.0, "heat") == "Peligro"
    assert tc.categoria_estres(55.0, "heat") == "Peligro extremo"


# ---------------------------------------------------------------- climate_profile

def test_perfil_logaritmico_crece_con_altura():
    u_2 = velocidad_viento(2.0, 4.0, z0=0.03)
    u_10 = velocidad_viento(10.0, 4.0, z0=0.03)
    assert 0 < u_2 < u_10 <= 4.0


def test_perfil_logaritmico_dentro_dosel_es_cero():
    assert velocidad_viento(0.01, 4.0, z0=0.03) == 0.0


def test_rugosidad_superficies_monotona():
    assert z0_superficie("cesped") < z0_superficie("parque") < z0_superficie("urbano")


def test_atenuacion_copa_densa():
    """Copa densa (~0.9) corta ~54% del viento; abierta (~0.3) ~18%."""
    assert atenuacion_copa(0.9) == pytest.approx(0.46, abs=0.01)
    assert atenuacion_copa(0.3) == pytest.approx(0.82, abs=0.01)
    assert atenuacion_copa(1.5) == pytest.approx(0.4)  # satura


def test_viento_categoria_moderado_es_4ms():
    """Coincide con el mapeo de McAdams que ya usa el modelo."""
    assert viento_categoria_a_ms("moderado") == 4.0
    assert viento_categoria_a_ms("desconocida") == 4.0


def test_descomponer_radiacion_conserva_energia():
    for nubosidad in ("Despejado", "Parcial", "Nublado"):
        r = descomponer_radiacion(800.0, 45.0, nubosidad)
        assert r["dhi"] + r["directa_horizontal"] == pytest.approx(800.0, abs=0.01)
        assert r["directa_horizontal"] > 0


def test_descomponer_radiacion_nublado_mas_difuso():
    despejado = descomponer_radiacion(800.0, 45.0, "Despejado")
    nublado = descomponer_radiacion(800.0, 45.0, "Nublado")
    assert nublado["dhi"] > despejado["dhi"]


# ---------------------------------------------------------------- scenario

def test_temperatura_diurna_extremos():
    assert temperatura_diurna(20.0, 34.0, 6) == pytest.approx(20.0)
    assert temperatura_diurna(20.0, 34.0, 15) == pytest.approx(34.0, abs=0.01)
    assert temperatura_diurna(20.0, 34.0, 2) == pytest.approx(20.0)


def test_escenario_horario_sombra_siempre_menor_o_igual():
    calc = Temperatura(-31.4, -64.2, k_factor=0.04)
    esc = escenario_horario(calc, date(2026, 1, 15), [8, 12, 16],
                            20.0, 34.0, 60.0, 4.0, sombra_pct=60.0)
    assert len(esc) == 3
    for r in esc:
        assert r["tmrt_sombra"] <= r["tmrt_sol"]
        assert r["hi_sombra"] <= r["hi_sol"]
        assert r["delta_tmrt"] == pytest.approx(r["tmrt_sol"] - r["tmrt_sombra"], abs=0.02)


def test_escenario_horario_mas_sombra_menos_estres():
    calc = Temperatura(-31.4, -64.2, k_factor=0.04)
    esc20 = escenario_horario(calc, date(2026, 1, 15), [8, 12, 16],
                              20.0, 34.0, 60.0, 4.0, sombra_pct=20.0)
    esc80 = escenario_horario(calc, date(2026, 1, 15), [8, 12, 16],
                              20.0, 34.0, 60.0, 4.0, sombra_pct=80.0)
    hi20 = max(r["hi_sombra"] for r in esc20)
    hi80 = max(r["hi_sombra"] for r in esc80)
    assert hi80 < hi20


def test_resumen_y_comparacion_ab():
    calc = Temperatura(-31.4, -64.2, k_factor=0.04)
    horas = [float(h) for h in range(8, 19)]
    base = escenario_horario(calc, date(2026, 1, 15), horas, 20.0, 34.0,
                             60.0, 4.0, sombra_pct=20.0)
    prop = escenario_horario(calc, date(2026, 1, 15), horas, 20.0, 34.0,
                             60.0, 4.0, sombra_pct=60.0)
    rb = resumen_escenario(base)
    cmp = comparar_escenarios(base, prop)
    assert rb["grados_hora_hi_sol"] >= rb["grados_hora_hi_sombra"]
    assert cmp["delta_hi_max"] <= 0.0
    assert cmp["delta_grados_hora_hi"] <= 0.0
    assert rb["hi_max_sol"] >= rb["hi_max_sombra"]


def test_ranking_arboles_arbol_grande_gana():
    calc = Temperatura(-31.4, -64.2, k_factor=0.04)
    chico = Arbol(0, 0, 5, 1.0, 1.5)
    grande = Arbol(0, 0, 12, 1.0, 4.0)
    ranking = ranking_arboles([chico, grande], calc, date(2026, 1, 15), 12.0)
    assert ranking[0]["arbol"] is grande
    assert ranking[0]["area_sombra_m2"] > ranking[1]["area_sombra_m2"]
    assert ranking[0]["delta_tmrt_prom"] > 0


def test_ranking_arboles_sol_bajo_no_rompe():
    calc = Temperatura(-31.4, -64.2, k_factor=0.04)
    arbol = Arbol(0, 0, 5, 1.0, 2.0)
    ranking = ranking_arboles([arbol], calc, date(2026, 6, 21), 22.0)
    assert ranking[0]["delta_tmrt_prom"] == 0.0
    assert ranking[0]["categoria"] == "Sol bajo el horizonte"


def test_mapa_estres_bandas_sumadas():
    mapa = np.full((10, 10), 45.0)
    mapa[:5, :] = 33.0
    res = mapa_estres(mapa, ta=30.0, rh=60.0)
    assert sum(res["por_area"].values()) == pytest.approx(100.0, abs=0.2)
    assert "Peligro" in res["por_area"]
    assert res["media_tmrt"] == pytest.approx(39.0, abs=0.1)


# ---------------------------------------------------------------- validation

def test_metricas_perfectas():
    m = metricas([30.0, 31.0, 32.0], [30.0, 31.0, 32.0])
    assert m["rmse"] == 0.0 and m["mae"] == 0.0 and m["bias"] == 0.0 and m["r2"] == 1.0


def test_metricas_bias_positivo():
    m = metricas([30.0, 31.0, 32.0], [32.0, 33.0, 34.0])
    assert m["bias"] == pytest.approx(2.0)
    assert m["rmse"] == pytest.approx(2.0)


def test_metricas_exige_2_puntos():
    with pytest.raises(ValueError):
        metricas([30.0], [31.0])


def test_k_factor_desde_mediciones_fuerza_origen():
    """Dado Tmrt = Ta + k·rad con k conocido, el ajuste debe recuperarlo."""
    k_real = 0.03
    filas = [{"tmrt_medido": 30.0 + k_real * rad, "ta": 30.0, "rad": rad}
             for rad in (500.0, 700.0, 900.0)]
    ajuste = k_factor_desde_mediciones(filas)
    assert ajuste["k_factor"] == pytest.approx(k_real, abs=0.002)
    assert ajuste["r2"] > 0.99


def test_leer_csv_mediciones_con_globo(tmp_path):
    csv = tmp_path / "mediciones.csv"
    csv.write_text("tg,ta,rad,v\n45.2,30.0,750.0,0.5\n48.0,31.0,800.0,0.8\n",
                   encoding="utf-8")
    filas = leer_csv_mediciones(str(csv))
    assert len(filas) == 2
    assert filas[0]["tmrt_medido"] > 30.0
    assert filas[0]["rad"] == 750.0


def test_leer_csv_mediciones_errores(tmp_path):
    malo = tmp_path / "malo.csv"
    malo.write_text("foo,bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        leer_csv_mediciones(str(malo))
    with pytest.raises(FileNotFoundError):
        leer_csv_mediciones(str(tmp_path / "inexistente.csv"))


# ---------------------------------------------------------------- especies

def test_especies_rangos_fisicos():
    for nombre, p in ESPECIES.items():
        assert 0 < p["rho_copa"] <= 1
        assert 0 < p["transmitancia"] <= 1
        assert 0 < p["albedo_copa"] <= 1
        assert p["altura_tipica"] > 0
        assert p["radio_copa_tipico"] > 0
        assert "ref" in p


def test_especies_caducifolias_y_perennes():
    nombres = nombres_especies()
    assert "Plátano (Platanus × acerifolia)" in nombres
    assert ESPECIES["Plátano (Platanus × acerifolia)"]["caducifolio"] is True
    assert ESPECIES["Pino (Pinus sp.)"]["caducifolio"] is False
