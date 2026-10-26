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
    utci_array,
)
from core.surface_model import calcular_sombra_arboles

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
    scenario_provider=None,
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
        hourly = scenario_provider(ta, hora, calc) if scenario_provider is not None else None
        if hourly is not None:
            hour_calc = hourly.calculator()
            ta, rh, v_ms = hourly.air_temp_c, hourly.rh_pct, hourly.wind_ref_10m_m_s
        else:
            hour_calc = calc
        elev = hourly.solar_elevation if hourly is not None else calc.solar_altitude(doy, hora)
        ghi_clear = calc.clear_sky_radiation(elev)
        ghi = hourly.ghi if hourly is not None else ghi_clear * factor_ghi_nubosidad(nubosidad)
        rad = descomponer_radiacion(ghi, elev, nubosidad)
        if hourly is not None:
            rad.update(dni_normal=hourly.dni, dhi=hourly.dhi)
        tau = calc.shadow_transmittance(
            sombra_pct,
            shadow_type,
            full_shadow_transmittance=full_shadow_transmittance,
        )
        tmrt_result = hour_calc.calculate_tmrt(
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
            "effective_scenario": hourly.to_dict() if hourly is not None else None,
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
    utcis_sol = [r["utci_sol"] for r in resultados if r["utci_sol"] is not None and np.isfinite(r["utci_sol"])]
    utcis_sombra = [r["utci_sombra"] for r in resultados if r["utci_sombra"] is not None and np.isfinite(r["utci_sombra"])]
    utci_sol = max(utcis_sol) if utcis_sol else (float("nan") if any(r["utci_sol"] is not None for r in resultados) else None)
    utci_sombra = max(utcis_sombra) if utcis_sombra else (float("nan") if any(r["utci_sombra"] is not None for r in resultados) else None)
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
        "utci_horas_validas_sol": len(utcis_sol),
        "utci_horas_validas_sombra": len(utcis_sombra),
        "utci_horas_fuera_dominio_sol": sum(r["utci_sol"] is not None and not np.isfinite(r["utci_sol"]) for r in resultados),
        "utci_horas_fuera_dominio_sombra": sum(r["utci_sombra"] is not None and not np.isfinite(r["utci_sombra"]) for r in resultados),
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
                    extent: float = 60.0, resolucion: int = 240, *, scenario=None) -> list[dict]:
    """Potencial individual por ΔTmrt medio en un dominio fijo.

    Cada árbol se compara solo contra el mismo dominio al sol. No atribuye
    aportes marginales en escenas con solapes, edificios o evapotranspiración.
    La UI debe aportar el escenario efectivo de Temperatura; sin escenario
    se conserva exclusivamente la aproximación estándar histórica.
    """
    extent = float(extent)
    if not math.isfinite(extent) or extent <= 0:
        raise ValueError("El tamaño del dominio debe ser positivo y finito.")
    if isinstance(resolucion, bool) or not isinstance(resolucion, (int, np.integer)) or not 2 <= resolucion <= 640:
        raise ValueError("La resolución del ranking debe ser un entero entre 2 y 640.")
    arboles = list(arboles)
    if scenario is not None:
        calc = scenario.calculator()
        elev, ghi = scenario.solar_elevation, scenario.ghi
        azimuth = math.radians(scenario.solar_azimuth)
        metadata = scenario.to_dict()
        method = "individual_tree_tmrt_v2"
    else:
        if calc.model_mode != calc.MODEL_STANDARD:
            raise ValueError("El ranking avanzado requiere un escenario efectivo de Temperatura.")
        doy = fecha.timetuple().tm_yday
        elev = calc.solar_altitude(doy, hora)
        ghi = calc.clear_sky_radiation(elev)
        azimuth = math.radians(calc.solar_azimuth(doy, hora))
        metadata = None
        method = "legacy_standard_empirical"
    base = dict(extent_m=extent, resolution=resolucion, method=method, domain_center_m=[0.0, 0.0],
                domain_bounds_m=[-extent/2, extent/2, -extent/2, extent/2],
                tmrt_model=calc.model_mode, effective_scenario=metadata,
                comparison="individual_tree_against_full_sun", overlap_attribution=False)
    for i, arbol in enumerate(arboles, start=1):
        geometry = [float(getattr(arbol, name)) for name in ("x", "y", "h", "radio_copa", "rho_copa")]
        if not all(math.isfinite(x) for x in geometry) or geometry[2] < 0 or geometry[3] <= 0 or not 0 <= geometry[4] <= 1:
            raise ValueError(f"Geometría o densidad inválida en el árbol {i}.")
    if not arboles:
        return []
    if elev <= 0 or ghi <= 0:
        category = "Sol bajo el horizonte" if elev <= 0 else "Sin radiación solar"
        return [dict(base, arbol=a, tree_index=i, area_sombra_m2=0.0, cobertura_frac=0.0,
                     delta_tmrt_prom=0.0, categoria=category) for i, a in enumerate(arboles, start=1)]
    # Centros de celda: todas las celdas pesan extent²/N², sin contar el
    # borde exterior dos veces ni superar el área física del dominio.
    step = extent / resolucion
    axis = -extent / 2 + (np.arange(resolucion) + 0.5) * step
    X, Y = np.meshgrid(axis, axis)
    zero = np.zeros_like(X, dtype=np.float32)
    if scenario is not None:
        kwargs = scenario.calculation_kwargs()
        sun = calc.calculate_tmrt_map(scenario.air_temp_c, zero,
                                     transmittance_map_override=np.ones_like(X), **kwargs)["Tmrt_map"]
    ranking = []
    for i, arbol in enumerate(arboles, start=1):
        tau = calcular_sombra_arboles(X, Y, [arbol], math.radians(elev), azimuth)
        cobertura = float(np.count_nonzero(tau < 1.0)) / (resolucion * resolucion)
        if scenario is not None:
            shaded = calc.calculate_tmrt_map(scenario.air_temp_c, zero,
                                            transmittance_map_override=tau, **kwargs)["Tmrt_map"]
            delta_tmrt = float(np.mean(sun.astype(np.float64) - shaded))
        else:
            delta_tmrt = float(calc.k_factor) * ghi * float(np.mean(1.0 - tau))
        ranking.append(dict(base, arbol=arbol, tree_index=i,
                            area_sombra_m2=cobertura * extent * extent,
                            cobertura_frac=cobertura, delta_tmrt_prom=delta_tmrt,
                            categoria="Con sombra" if cobertura else "Sin sombra dentro del dominio"))
    # Mantener precisión para ordenar; el redondeo corresponde a la vista.
    ranking.sort(key=lambda r: r["delta_tmrt_prom"], reverse=True)
    return ranking


def ranking_export_payload(ranking, *, scene_name):
    """Snapshot JSON de árboles + resultados + procedencia; sin objetos Tk."""
    from core.app_version import APP_RELEASE
    from core.model_registry import methodology_manifest
    rows = []
    for result in ranking:
        tree = result["arbol"]
        row = {key: val for key, val in result.items() if key not in ("arbol", "effective_scenario")}
        row["tree"] = {name: float(getattr(tree, name)) for name in ("x", "y", "h", "radio_copa", "rho_copa")}
        row["tree"]["species"] = str(getattr(tree, "especie", ""))
        rows.append(row)
    return dict(schema_version=1, app_release=APP_RELEASE, methodology=methodology_manifest(),
                scene_name=str(scene_name), effective_scenario=ranking[0]["effective_scenario"] if ranking else None,
                interpretation="Potencial individual en dominio fijo; no suma de beneficios ni aporte marginal en la escena completa.",
                rows=rows)


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
        ind = utci_array(ta, validos.astype(np.float32, copy=False), v_ms, rh)
        if ind is None:
            raise ValueError("UTCI no disponible: instale pythermalcomfort.")
        ind = np.asarray(ind, dtype=np.float32).reshape(-1)
        outside_domain = int(np.count_nonzero(~np.isfinite(ind)))
        ind = ind[np.isfinite(ind)]

        # Clasificación completamente vectorizada: no se llama a Python una
        # vez por píxel. El orden sigue las bandas estándar de UTCI.
        bandas = (
            ("Estrés por frío extremo", -np.inf, -40.0),
            ("Estrés por frío muy fuerte", -40.0, -27.0),
            ("Estrés por frío fuerte", -27.0, -13.0),
            ("Estrés por frío moderado", -13.0, 0.0),
            ("Estrés por frío leve", 0.0, 9.0),
            ("Sin estrés térmico", 9.0, 26.0),
            ("Estrés de calor moderado", 26.0, 32.0),
            ("Estrés de calor fuerte", 32.0, 38.0),
            ("Estrés de calor muy fuerte", 38.0, 46.0),
            ("Estrés de calor extremo", 46.0, np.inf),
        )
        categorias = {"Fuera de dominio UTCI": outside_domain} if outside_domain else {}
        for nombre, inferior, superior in bandas:
            n = int(np.count_nonzero((ind >= inferior) & (ind < superior)))
            if n:
                categorias[nombre] = n
    elif indice == "heat":
        valor = indice_calor(float(ta), rh)
        categorias = {categoria_estres(valor, "heat"): int(validos.size)}
    elif indice == "at":
        valor = temperatura_aparente(float(ta), rh, v_ms)
        categorias = {categoria_estres(valor, "at"): int(validos.size)}
    else:
        raise ValueError("indice debe ser 'utci', 'heat' o 'at'.")

    total = int(validos.size)
    return {
        "por_area": {cat: round(n / total * 100, 1) for cat, n in categorias.items()},
        "media_tmrt": round(float(np.mean(validos)), 2),
        "min_tmrt": round(float(np.min(validos)), 2),
        "max_tmrt": round(float(np.max(validos)), 2),
        "n_pixeles": int(total),
        "indice": indice,
        "n_pixeles_validos_indice": int(ind.size) if indice == "utci" else total,
        "n_pixeles_fuera_dominio": outside_domain if indice == "utci" else 0,
    }
