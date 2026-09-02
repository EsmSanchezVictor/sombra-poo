"""Registro único de versiones y nombres metodológicos del proyecto.

No contiene física: centraliza etiquetas y versiones para evitar que UI,
Excel, snapshots e informes describan de manera distinta el mismo cálculo.
"""
from __future__ import annotations

SCIENTIFIC_RELEASE = "v17"
SCIENTIFIC_SCHEMA = "sombra-science/1.0"
SHADOW_ALGORITHM_VERSION = "shadow_photo_v11"
UNCERTAINTY_METHOD_VERSION = "operational_monte_carlo_v1"

TMRT_MODELS = {
    "standard": {
        "label": "Estándar · empírico calibrable",
        "version": "tmrt_standard_v1",
        "status": "predeterminado",
    },
    "advanced": {
        "label": "Avanzado · balance radiativo v1",
        "version": "advanced_radiative_v1",
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
    }
