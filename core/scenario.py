"""Escenarios horarios, comparación A/B y ranking de árboles.

La sombra modifica principalmente la carga radiativa (Tmrt) y, por esa vía,
el UTCI. Heat Index y Temperatura Aparente se calculan con temperatura DEL
AIRE, humedad y viento; no se alimentan con Tmrt.
"""
from __future__ import annotations

import math
import numpy as np

from core.climate_profile import (
    atenuacion_copa,
    descomponer_radiacion,
    factor_ghi_nubosidad,
    temperatura_diurna_ciclo,
)
from core.thermal_comfort import (
    categoria_estres,
    categoria_utci,
    grados_hora,
    indice_calor,
    temperatura_aparente,
    utci,
)
from modelo_con_excel import calcular_sombra_arboles

UMBRAL_HI = 32.2


def temperatura_diurna(ta_min: float, ta_max: float, hora: float) -> float:
    return temperatura_diurna_ciclo(float(hora), float(ta_min), float(ta_max), 6.0, 15.0)


def escenario_horario(
    calc,
    fecha,
    horas,
    ta_min: float,
    ta_max: float,
    rh: float,
    v_ms: float,
    sombra_pct: float,
    nubosidad: str = "Despejado",
    shadow_type: str = "tree",
    k_factor: float | None = None,
    viento_bajo_copa: float | None = None,
    full_shadow_transmittance: float | None = None,
) -> list[dict]:
    """Barrido horario del día.

    ``v_ms`` es la velocidad meteorológica de referencia usada por UTCI y por
    Temperatura Aparente. ``viento_bajo_copa`` se conserva como diagnóstico
    microclimático local, pero NO se sustituye por el viento estándar de UTCI.
    """
    doy = fecha.timetuple().tm_yday
    k = float(k_factor) if k_factor is not None else float(calc.k_factor)
    v_ms = max(0.0, float(v_ms))
    v_local = (
        max(0.0, float(viento_bajo_copa))
        if viento_bajo_copa is not None
        else v_ms * atenuacion_copa(0.75)
    )

    resultados = []
    for hora in horas:
        ta = temperatura_diurna(ta_min, ta_max, hora)
        elev = calc.solar_altitude(doy, hora)
        ghi_clear = calc.clear_sky_radiation(elev)
        ghi = ghi_clear * factor_ghi_nubosidad(nubosidad)
        rad = descomponer_radiacion(ghi, elev, nubosidad)
        tau = calc.shadow_transmittance(
            sombra_pct,
            shadow_type,
            full_shadow_transmittance=full_shadow_transmittance,
        )
        tmrt_result = calc.calculate_tmrt(
            ta,
            sombra_pct,
            shadow_type=shadow_type,
            date_value=fecha,
            time_value=hora,
            radiation_override=rad["ghi"],
            solar_altitude_override=elev,
            full_shadow_transmittance=full_shadow_transmittance,
            dni_override=rad.get("dni_normal"),
            dhi_override=rad.get("dhi"),
        )
        tmrt_sol = float(tmrt_result["Tmrt_sol"])
        tmrt_sombra = float(tmrt_result["Tmrt_sombra"])

        hi_air = indice_calor(ta, rh)
        at_air = temperatura_aparente(ta, rh, v_ms)
        utci_sol = utci(ta, tmrt_sol, v_ms, rh)
        utci_sombra = utci(ta, tmrt_sombra, v_ms, rh)

        resultados.append({
            "hora": float(hora),
            "elevacion": round(elev, 2),
            "ghi_clear": round(ghi_clear, 1),
            "ghi": round(rad["ghi"], 1),
            "dhi": round(rad["dhi"], 1),
            "ta": round(ta, 2),
            "v_ref_10m": round(v_ms, 3),
            "v_local_estimado": round(v_local, 3),
            "tmrt_sol": round(tmrt_sol, 2),
            "tmrt_sombra": round(tmrt_sombra, 2),
            "hi_air": round(hi_air, 2),
            "at_air": round(at_air, 2),
            # Claves históricas conservadas para no romper UI/proyectos.
            # Son iguales porque HI/AT no incorporan Tmrt.
            "hi_sol": round(hi_air, 2),
            "hi_sombra": round(hi_air, 2),
            "at_sol": round(at_air, 2),
            "at_sombra": round(at_air, 2),
            "utci_sol": round(utci_sol, 2) if utci_sol is not None else None,
            "utci_sombra": round(utci_sombra, 2) if utci_sombra is not None else None,
            "delta_tmrt": round(tmrt_sol - tmrt_sombra, 2),
            "tau_efectiva": round(tau, 4),
            "modelo_tmrt": tmrt_result.get("Modelo_Tmrt", "standard"),
        })
    return resultados


def resumen_escenario(resultados: list[dict], umbral: float = UMBRAL_HI) -> dict:
    hi_series = [(r["hora"], r["hi_air"]) for r in resultados]
    at_series = [(r["hora"], r["at_air"]) for r in resultados]
    utcis_sol = [r["utci_sol"] for r in resultados if r["utci_sol"] is not None]
    utcis_sombra = [r["utci_sombra"] for r in resultados if r["utci_sombra"] is not None]
    utci_sol = max(utcis_sol) if utcis_sol else None
    utci_sombra = max(utcis_sombra) if utcis_sombra else None
    hi_max = max((r["hi_air"] for r in resultados), default=0.0)
    at_max = max((r["at_air"] for r in resultados), default=0.0)
    gh_hi = grados_hora(hi_series, umbral)
    gh_at = grados_hora(at_series, 32.0)
    return {
        "hi_max_air": hi_max,
        "at_max_air": at_max,
        "hi_max_sol": hi_max,
        "hi_max_sombra": hi_max,
        "at_max_sol": at_max,
        "at_max_sombra": at_max,
        "utci_max_sol": utci_sol,
        "utci_max_sombra": utci_sombra,
        "utci_categoria_sol": categoria_utci(utci_sol),
        "utci_categoria_sombra": categoria_utci(utci_sombra),
        "delta_tmrt_max": max((r["delta_tmrt"] for r in resultados), default=0.0),
        "grados_hora_hi_air": gh_hi,
        "grados_hora_at_air": gh_at,
        "grados_hora_hi_sol": gh_hi,
        "grados_hora_hi_sombra": gh_hi,
        "grados_hora_at_sol": gh_at,
        "grados_hora_at_sombra": gh_at,
        "categoria_pico_air": categoria_estres(hi_max, "heat"),
        "categoria_pico_sol": categoria_estres(hi_max, "heat"),
        "categoria_pico_sombra": categoria_estres(hi_max, "heat"),
    }


def comparar_escenarios(base: list[dict], propuesto: list[dict]) -> dict:
    rb = resumen_escenario(base)
    rp = resumen_escenario(propuesto)
    delta_utci = None
    if rb["utci_max_sombra"] is not None and rp["utci_max_sombra"] is not None:
        delta_utci = round(rp["utci_max_sombra"] - rb["utci_max_sombra"], 2)
    return {
        # Se conservan; si solo cambia sombra, HI/AT deben permanecer iguales.
        "delta_hi_max": round(rp["hi_max_sombra"] - rb["hi_max_sombra"], 2),
        "delta_grados_hora_hi": round(
            rp["grados_hora_hi_sombra"] - rb["grados_hora_hi_sombra"], 2
        ),
        "delta_grados_hora_at": round(
            rp["grados_hora_at_sombra"] - rb["grados_hora_at_sombra"], 2
        ),
        "delta_utci_max": delta_utci,
        "delta_tmrt_max": round(rp["delta_tmrt_max"] - rb["delta_tmrt_max"], 2),
        "base": rb,
        "propuesto": rp,
    }


def ranking_arboles(arboles, calc, fecha, hora: float,
                    extent: float = 60.0, resolucion: int = 240) -> list[dict]:
    """Ranking por área proyectada y reducción media de Tmrt de la escena."""
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


def mapa_estres(
    valores_2d,
    ta: float,
    rh: float,
    indice: str = "utci",
    v_ms: float = 1.0,
) -> dict:
    """Clasifica un mapa de Tmrt con un índice físicamente compatible.

    - ``utci``: usa Ta, Tmrt de cada píxel, viento de referencia y RH.
    - ``heat``: Heat Index usa únicamente Ta/RH, por lo que no genera una
      variación espacial por sombra; se mantiene por compatibilidad.
    - ``at``: Temperatura Aparente usa Ta/RH/viento, también uniforme si esas
      variables son uniformes.
    """
    valores = np.asarray(valores_2d, dtype=float)
    if valores.ndim != 2 or valores.size == 0:
        raise ValueError("Se espera un mapa 2D no vacío.")
    validos = valores[np.isfinite(valores)]
    if validos.size == 0:
        raise ValueError("El mapa no tiene valores válidos.")

    if indice == "utci":
        ind = np.array([utci(ta, float(tmrt), v_ms, rh) for tmrt in validos], dtype=object)
        if any(v is None for v in ind):
            raise ValueError("UTCI no disponible: instale pythermalcomfort.")
        categorias = {}
        for v in ind:
            cat = categoria_utci(float(v))
            categorias[cat] = categorias.get(cat, 0) + 1
    elif indice == "heat":
        valor = indice_calor(float(ta), rh)
        categorias = {categoria_estres(valor, "heat"): int(validos.size)}
    elif indice == "at":
        valor = temperatura_aparente(float(ta), rh, v_ms)
        categorias = {categoria_estres(valor, "at"): int(validos.size)}
    else:
        raise ValueError("indice debe ser 'utci', 'heat' o 'at'.")

    total = validos.size
    return {
        "por_area": {cat: round(n / total * 100, 1) for cat, n in sorted(categorias.items())},
        "media_tmrt": round(float(np.mean(validos)), 2),
        "min_tmrt": round(float(np.min(validos)), 2),
        "max_tmrt": round(float(np.max(validos)), 2),
        "n_pixeles": int(total),
        "indice": indice,
    }
