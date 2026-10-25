"""Registro único de versiones y nombres metodológicos del proyecto.

No contiene física: centraliza etiquetas y versiones para evitar que UI,
Excel, snapshots e informes describan de manera distinta el mismo cálculo.
"""
from __future__ import annotations

SCIENTIFIC_RELEASE = "v35.6-etapa3.2"
SCIENTIFIC_SCHEMA = "sombra-science/1.2"
SHADOW_ALGORITHM_VERSION = "shadow_photo_v11"
UNCERTAINTY_METHOD_VERSION = "operational_monte_carlo_v1"

TMRT_MODELS = {
    "standard": {
        "label": "Estándar · empírico calibrable",
        "version": "tmrt_standard_v1",
        "status": "predeterminado",
    },
    "advanced": {
        "label": "Avanzado · balance radiativo v2",
        "version": "advanced_radiative_v2",
        "status": "requiere validación local",
    },
}

SURFACE_MODELS = {
    "standard": {
        "label": "Estándar · balance linealizado legacy",
        "version": "surface_standard_v1",
    },
    "advanced": {
        "label": "Avanzado seco · balance no lineal v1",
        "version": "surface_energy_advanced_v1",
    },
    "advanced_vegetation": {
        "label": "Avanzado vegetación + ET v2",
        "version": "surface_energy_vegetation_v2",
    },
}

RADIATION_SOURCES = {
    "clear_sky": "Cielo despejado modelado",
    "manual_measured": "Medición puntual",
    "manual_scenario": "Escenario manual",
    "observed_series": "Serie meteorológica observada",
}


def methodology_manifest() -> dict:
    return {
        "scientific_release": SCIENTIFIC_RELEASE,
        "scientific_schema": SCIENTIFIC_SCHEMA,
        "shadow_algorithm": SHADOW_ALGORITHM_VERSION,
        "uncertainty_method": UNCERTAINTY_METHOD_VERSION,
        "tmrt_models": TMRT_MODELS,
        "surface_models": SURFACE_MODELS,
        "radiation_sources": RADIATION_SOURCES,
        "effective_scenario_schema": 2,
        "wind_reference_height_m": 10.0,
        "vegetation_wind_height_m": 2.0,
        "vegetation_wind_conversion": "neutral logarithmic profile, z0=0.03 m; operational assumption",
        "utci_domain": {"tdb_c": [-50, 50], "tr_minus_tdb_c": [-30, 70], "wind_10m_m_s": [0.5, 17], "rh_pct": [0, 100]},
        "local_time_policy": "strict_local_time_v1: reject ambiguous/nonexistent naive time; accept explicit offset or API fold",
        "tree_ranking_method": "individual_tree_tmrt_v2: same effective Tmrt context, cell centers, no scene overlap attribution",
        "date_policy": "visible day of year with stored calendar year; 24 h rolls to next date",
    }
