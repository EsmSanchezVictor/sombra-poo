"""Biblioteca de especies y propiedades térmicas documentadas.

Cada especie expone:

- `rho_copa`: densidad/opacidad de la copa (0-1) — el mismo parámetro
  que ya usa el modelo de sombra (transmitancia de copa).
- `transmitancia`: fracción de radiación directa que deja pasar la
  copa (tau en condiciones típicas, otoño/verano).
- `caducifolio`: True si pierde la hoja en invierno (la sombra de
  invierno es de rama, ~transmitancia 0.7).
- `albedo_copa`: albedo de onda corta de la copa.
- `altura_tipica`, `radio_copa_tipico`: valores de referencia para el
  editor de escena (m).
- `ref`: referencia bibliográfica.

Los rangos son valores documentados de la literatura de
biometeorología urbana (ver ref en cada entrada). Son punto de
partida — calibrar por especie local con `Calibrar k_factor` y la
validación CSV.
"""
from __future__ import annotations

ESPECIES = {
    "Álamo (Populus sp.)": {
        "rho_copa": 0.35, "transmitancia": 0.50, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 18.0, "radio_copa_tipico": 3.0,
        "ref": "Oke, Boundary Layer Climates (1987); linhas de álamo en parques urbanos",
    },
    "Plátano (Platanus × acerifolia)": {
        "rho_copa": 0.75, "transmitancia": 0.25, "caducifolio": True,
        "albedo_copa": 0.18, "altura_tipica": 22.0, "radio_copa_tipico": 6.0,
        "ref": "Oke (1987); especie estándar de arbolado de alineación templado",
    },
    "Tipa (Tipuana tipu)": {
        "rho_copa": 0.70, "transmitancia": 0.28, "caducifolio": False,
        "albedo_copa": 0.17, "altura_tipica": 18.0, "radio_copa_tipico": 7.0,
        "ref": "Cremaschi & Botta, Árboles de Buenos Aires (2013)",
    },
    "Jacarandá (Jacaranda mimosifolia)": {
        "rho_copa": 0.55, "transmitancia": 0.35, "caducifolio": True,
        "albedo_copa": 0.19, "altura_tipica": 14.0, "radio_copa_tipico": 5.0,
        "ref": "Cremaschi & Botta (2013)",
    },
    "Fresno (Fraxinus sp.)": {
        "rho_copa": 0.65, "transmitancia": 0.30, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 20.0, "radio_copa_tipico": 5.0,
        "ref": "Oke (1987)",
    },
    "Roble (Quercus sp.)": {
        "rho_copa": 0.80, "transmitancia": 0.20, "caducifolio": True,
        "albedo_copa": 0.16, "altura_tipica": 25.0, "radio_copa_tipico": 6.0,
        "ref": "Oke (1987); copa densa, sombra de alta calidad",
    },
    "Pino (Pinus sp.)": {
        "rho_copa": 0.60, "transmitancia": 0.25, "caducifolio": False,
        "albedo_copa": 0.12, "altura_tipica": 25.0, "radio_copa_tipico": 3.5,
        "ref": "Oke (1987); conífera de hoja permanente, sombra todo el año",
    },
    "Palmera (Arecaceae)": {
        "rho_copa": 0.30, "transmitancia": 0.55, "caducifolio": False,
        "albedo_copa": 0.25, "altura_tipica": 12.0, "radio_copa_tipico": 2.5,
        "ref": "Sombra de copa abierta; baja atenuación, alta radiación difusa",
    },
    "Arbusto bajo (1-2 m)": {
        "rho_copa": 0.50, "transmitancia": 0.35, "caducifolio": False,
        "albedo_copa": 0.22, "altura_tipica": 1.5, "radio_copa_tipico": 1.0,
        "ref": "Vegetación baja; aporta sombra parcial a nivel de suelo",
    },
}

_DEFAULT = ESPECIES["Plátano (Platanus × acerifolia)"]


def propiedades_especie(nombre: str) -> dict:
    """Devuelve las propiedades de una especie (con la del plátano como
    valor por defecto para especies desconocidas)."""
    return dict(ESPECIES.get(nombre, _DEFAULT))


def nombres_especies() -> list[str]:
    return sorted(ESPECIES.keys())