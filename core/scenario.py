"""Herramientas de escenario: barrido horario, comparación A/B,
ranking de árboles y mapa de estrés térmico.

Todos los cálculos reutilizan el motor existente (`Temperatura` de
shadow_temp.py, `calcular_sombra_arboles` de modelo_con_excel.py) —
no duplican física, solo orquestan series horarias y resúmenes.
"""
from __future__ import annotations

import math

import numpy as np

from core.climate_profile import atenuacion_copa, descomponer_radiacion, velocidad_viento
from core.thermal_comfort import (categoria_estres, categoria_utci, grados_hora,
                                  indice_calor, temperatura_aparente, utci)
from modelo_con_excel import calcular_sombra_arboles

UMBRAL_HI = 32.2  # "Mucha precaución" (NWS) — sobre esto hay estrés real


def temperatura_diurna(ta_min: float, ta_max: float, hora: float) -> float:
    """Temperatura del aire diurna (aproximación senoidal documentada):
    mínima a las 6 h, máxima a las 15 h — la fase usa período de 18 h
    para que el pico caiga a las 15 (inercia térmica, misma fase que
    modelo_con_excel.temperatura_ambiente). Antes de las 6 y después de
    las 18 la temperatura vuelve al mínimo (noche)."""
    if hora <= 6:
        return ta_min
    if hora >= 18:
        return ta_min
    return ta_min + (ta_max - ta_min) * math.sin(math.pi * (hora - 6) / 18)


def escenario_horario(calc, fecha, horas, ta_min: float, ta_max: float,
                      rh: float, v_ms: float, sombra_pct: float,
                      nubosidad: str = "Despejado", shadow_type: str = "tree",
                      k_factor: float | None = None,
                      viento_bajo_copa: float | None = None) -> list[dict]:
    """Barrido horario del día: por cada hora calcula elevación solar,
    GHI, Tmrt sol/sombra y los índices de confort (Heat Index y
    Temperatura Aparente) para ambas condiciones.

    - `v_ms`: viento de referencia a 10 m; `viento_bajo_copa`: viento
      efectivo (si es None se usa v_ms atenuado por `atenuacion_copa`
      con rho_copa=0.75, copa densa).
    - `k_factor`: si se pasa, sobreescribe el del motor (para escenarios
      "qué pasa si calibré distinto").
    """
    doy = fecha.timetuple().tm_yday
    k = float(k_factor) if k_factor is not None else float(calc.k_factor)
    v_efectivo = viento_bajo_copa if viento_bajo_copa is not None else v_ms * atenuacion_copa(0.75)

    resultados = []
    for hora in horas:
        ta = temperatura_diurna(ta_min, ta_max, hora)
        elev = calc.solar_altitude(doy, hora)
        ghi = calc.clear_sky_radiation(elev)
        rad = descomponer_radiacion(ghi, elev, nubosidad)
        tau = calc.shadow_transmittance(sombra_pct, shadow_type)
        tmrt_sol = ta + k * rad["ghi"]
        tmrt_sombra = ta + k * rad["ghi"] * tau
        utci_sol = utci(ta, tmrt_sol, v_efectivo, rh)
        utci_sombra = utci(ta, tmrt_sombra, v_efectivo, rh)
        resultados.append({
            "hora": hora,
            "elevacion": round(elev, 2),
            "ghi": round(rad["ghi"], 1),
            "dhi": round(rad["dhi"], 1),
            "ta": round(ta, 2),
            "tmrt_sol": round(tmrt_sol, 2),
            "tmrt_sombra": round(tmrt_sombra, 2),
            "hi_sol": round(indice_calor(max(tmrt_sol, ta), rh), 2),
            "hi_sombra": round(indice_calor(max(tmrt_sombra, ta), rh), 2),
            "at_sol": round(temperatura_aparente(tmrt_sol, rh, v_efectivo), 2),
            "at_sombra": round(temperatura_aparente(tmrt_sombra, rh, v_efectivo), 2),
            "utci_sol": round(utci_sol, 2) if utci_sol is not None else None,
            "utci_sombra": round(utci_sombra, 2) if utci_sombra is not None else None,
            "delta_tmrt": round(tmrt_sol - tmrt_sombra, 2),
        })
    return resultados


def resumen_escenario(resultados: list[dict], umbral: float = UMBRAL_HI) -> dict:
    """Resumen operativo de un escenario: máximos y grados-hora de
    estrés (Heat Index sobre el umbral) para sol y sombra."""
    horas = [(r["hora"], r["hi_sol"]) for r in resultados]
    horas_sombra = [(r["hora"], r["hi_sombra"]) for r in resultados]
    horas_at_sol = [(r["hora"], r["at_sol"]) for r in resultados]
    horas_at_sombra = [(r["hora"], r["at_sombra"]) for r in resultados]
    utcis_sol = [r["utci_sol"] for r in resultados if r["utci_sol"] is not None]
    utcis_sombra = [r["utci_sombra"] for r in resultados if r["utci_sombra"] is not None]
    utci_sol = max(utcis_sol) if utcis_sol else None
    utci_sombra = max(utcis_sombra) if utcis_sombra else None
    return {
        "hi_max_sol": max((r["hi_sol"] for r in resultados), default=0.0),
        "hi_max_sombra": max((r["hi_sombra"] for r in resultados), default=0.0),
        "at_max_sol": max((r["at_sol"] for r in resultados), default=0.0),
        "at_max_sombra": max((r["at_sombra"] for r in resultados), default=0.0),
        "utci_max_sol": utci_sol,
        "utci_max_sombra": utci_sombra,
        "utci_categoria_sol": categoria_utci(utci_sol),
        "utci_categoria_sombra": categoria_utci(utci_sombra),
        "delta_tmrt_max": max((r["delta_tmrt"] for r in resultados), default=0.0),
        "grados_hora_hi_sol": grados_hora(horas, umbral),
        "grados_hora_hi_sombra": grados_hora(horas_sombra, umbral),
        "grados_hora_at_sol": grados_hora(horas_at_sol, 32.0),
        "grados_hora_at_sombra": grados_hora(horas_at_sombra, 32.0),
        "categoria_pico_sol": categoria_estres(
            max((r["hi_sol"] for r in resultados), default=0.0), "heat"),
        "categoria_pico_sombra": categoria_estres(
            max((r["hi_sombra"] for r in resultados), default=0.0), "heat"),
    }


def comparar_escenarios(base: list[dict], propuesto: list[dict]) -> dict:
    """Δ de la propuesta contra la línea base (sombra): cuánto baja el
    pico de estrés y los grados-hora al pasar de un % de sombra a otro."""
    rb = resumen_escenario(base)
    rp = resumen_escenario(propuesto)
    return {
        "delta_hi_max": round(rp["hi_max_sombra"] - rb["hi_max_sombra"], 2),
        "delta_grados_hora_hi": round(
            rp["grados_hora_hi_sombra"] - rb["grados_hora_hi_sombra"], 2),
        "delta_grados_hora_at": round(
            rp["grados_hora_at_sombra"] - rb["grados_hora_at_sombra"], 2),
        "base": rb,
        "propuesto": rp,
    }


def ranking_arboles(arboles, calc, fecha, hora: float,
                    extent: float = 60.0, resolucion: int = 240) -> list[dict]:
    """Ranking de efectividad de cada árbol de la escena: área de sombra
    proyectada a una hora dada y su aporte a la reducción de Tmrt
    promedio sobre la escena.

    `calcular_sombra_arboles` devuelve un mapa de transmitancia (1 =
    pleno sol, < 1 = sombreado, según rho_copa de cada copa), así que el
    ΔTmrt promedio se calcula directo con física del modelo:

        ΔTmrt = k · GHI · media(1 − transmitancia)

    Devuelve una lista ordenada de mayor a menor aporte:
    [{arbol, area_sombra_m2, cobertura_frac, delta_tmrt_prom}].
    """
    doy = fecha.timetuple().tm_yday
    elev = calc.solar_altitude(doy, hora)
    ghi = calc.clear_sky_radiation(elev)
    if elev <= 0 or ghi <= 0:
        return [{"arbol": a, "area_sombra_m2": 0.0, "cobertura_frac": 0.0,
                 "delta_tmrt_prom": 0.0, "categoria": "Sol bajo el horizonte"}
                for a in arboles]
    theta = math.radians(elev)
    azimuth = math.radians(calc.solar_azimuth(doy, hora))

    axis = np.linspace(-extent / 2, extent / 2, resolucion)
    X, Y = np.meshgrid(axis, axis)
    paso = extent / (resolucion - 1)

    ranking = []
    for arbol in arboles:
        tau = calcular_sombra_arboles(X, Y, [arbol], theta, azimuth)
        sombreado = tau < 1.0
        area = float(np.count_nonzero(sombreado)) * paso * paso
        cobertura = float(np.count_nonzero(sombreado)) / (resolucion * resolucion)
        delta_tmrt = float(calc.k_factor) * ghi * float(np.mean(1.0 - tau))
        ranking.append({
            "arbol": arbol,
            "area_sombra_m2": round(area, 1),
            "cobertura_frac": round(cobertura, 4),
            "delta_tmrt_prom": round(delta_tmrt, 2),
            "categoria": "Con sombra",
        })
    ranking.sort(key=lambda r: r["delta_tmrt_prom"], reverse=True)
    return ranking


def mapa_estres(valores_2d, ta: float, rh: float, indice: str = "heat") -> dict:
    """Clasifica un mapa (array 2D de Tmrt, p. ej. del Panel 2) en
    bandas de estrés térmico y devuelve el % de área en cada banda y el
    valor medio por banda. El Heat Index se evalúa con T = Tmrt
    (incluye la radiación como temperatura operativa)."""
    valores = np.asarray(valores_2d, dtype=float)
    if valores.ndim != 2 or valores.size == 0:
        raise ValueError("Se espera un mapa 2D no vacío.")
    validos = valores[~np.isnan(valores)]
    if validos.size == 0:
        raise ValueError("El mapa no tiene valores válidos.")
    total = validos.size
    if indice == "heat":
        ind = np.array([indice_calor(max(float(v), ta), rh) for v in validos])
    else:
        ind = validos
    categorias = {}
    for v in ind:
        cat = categoria_estres(float(v), indice)
        categorias[cat] = categorias.get(cat, 0) + 1
    return {
        "por_area": {cat: round(n / total * 100, 1) for cat, n in sorted(categorias.items())},
        "media_tmrt": round(float(np.mean(validos)), 2),
        "min_tmrt": round(float(np.min(validos)), 2),
        "max_tmrt": round(float(np.max(validos)), 2),
        "n_pixeles": int(total),
        "indice": indice,
    }