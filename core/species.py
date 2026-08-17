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

Base de datos editable: `ESPECIES` (abajo) es la base original en
código; las especies creadas o editadas por el usuario se persisten en
`data/species_db.json` y se superponen a la base original en
`especies_db()`. Editar una especie original crea un override;
eliminarla la restaura a su valor de fábrica.
"""
from __future__ import annotations

import json
import os

ESPECIES = {
    "Álamo (Populus sp.)": {
        "rho_copa": 0.35, "transmitancia": 0.50, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 18.0, "radio_copa_tipico": 3.0,
        "ref": "Oke, Boundary Layer Climates (1987); líneas de álamo en parques urbanos",
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
    # --- Especies típicas de Argentina y nativas (añadidas en v3.3) ---
    "Algarrobo blanco (Prosopis alba)": {
        "rho_copa": 0.65, "transmitancia": 0.30, "caducifolio": True,
        "albedo_copa": 0.18, "altura_tipica": 15.0, "radio_copa_tipico": 6.0,
        "ref": "Cabrera, Flora arbórea argentina (1942); INTA, Árboles nativos",
    },
    "Quebracho colorado (Schinopsis balansae)": {
        "rho_copa": 0.80, "transmitancia": 0.20, "caducifolio": False,
        "albedo_copa": 0.16, "altura_tipica": 20.0, "radio_copa_tipico": 5.0,
        "ref": "Cabrera (1942); copa densa y persistente del Chaco",
    },
    "Lapacho rosado (Handroanthus impetiginosus)": {
        "rho_copa": 0.60, "transmitancia": 0.32, "caducifolio": True,
        "albedo_copa": 0.18, "altura_tipica": 18.0, "radio_copa_tipico": 5.0,
        "ref": "Cabrera (1942); caducifolio brevemente en invierno",
    },
    "Palo borracho (Ceiba speciosa)": {
        "rho_copa": 0.50, "transmitancia": 0.40, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 18.0, "radio_copa_tipico": 5.0,
        "ref": "Cremaschi & Botta (2013); copa abierta, sombra liviana",
    },
    "Ombú (Phytolacca dioica)": {
        "rho_copa": 0.55, "transmitancia": 0.35, "caducifolio": False,
        "albedo_copa": 0.22, "altura_tipica": 10.0, "radio_copa_tipico": 6.0,
        "ref": "Cabrera (1942); siempreverde de copa ancha",
    },
    "Ceibo (Erythrina crista-galli)": {
        "rho_copa": 0.45, "transmitancia": 0.42, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 8.0, "radio_copa_tipico": 4.0,
        "ref": "Cabrera (1942); árbol nacional, flor naranja en verano",
    },
    "Espinillo (Vachellia caven)": {
        "rho_copa": 0.40, "transmitancia": 0.45, "caducifolio": True,
        "albedo_copa": 0.22, "altura_tipica": 6.0, "radio_copa_tipico": 3.0,
        "ref": "Cabrera (1942); copa abierta y baja, caducifolio en invierno",
    },
    "Caldén (Prosopis caldenia)": {
        "rho_copa": 0.70, "transmitancia": 0.28, "caducifolio": True,
        "albedo_copa": 0.18, "altura_tipica": 12.0, "radio_copa_tipico": 6.0,
        "ref": "Cabrera (1942); bosque de caldén pampeano, copa achaparrada",
    },
    "Tala (Celtis tala)": {
        "rho_copa": 0.60, "transmitancia": 0.30, "caducifolio": True,
        "albedo_copa": 0.19, "altura_tipica": 10.0, "radio_copa_tipico": 5.0,
        "ref": "Cabrera (1942); caducifolio del talar ribereño bonaerense",
    },
    "Sauce criollo (Salix humboldtiana)": {
        "rho_copa": 0.55, "transmitancia": 0.35, "caducifolio": True,
        "albedo_copa": 0.20, "altura_tipica": 12.0, "radio_copa_tipico": 4.0,
        "ref": "Cabrera (1942); ribereño, copa péndula y liviana",
    },
    "Cina-cina (Parkinsonia aculeata)": {
        "rho_copa": 0.40, "transmitancia": 0.45, "caducifolio": True,
        "albedo_copa": 0.22, "altura_tipica": 7.0, "radio_copa_tipico": 4.0,
        "ref": "Cabrera (1942); copa abierta, follaje muy fino",
    },
    "Mora (Morus alba)": {
        "rho_copa": 0.70, "transmitancia": 0.28, "caducifolio": True,
        "albedo_copa": 0.18, "altura_tipica": 10.0, "radio_copa_tipico": 5.0,
        "ref": "Cremaschi & Botta (2013); muy usada en veredas de Buenos Aires",
    },
    "Tilo (Tilia × moltkei)": {
        "rho_copa": 0.75, "transmitancia": 0.25, "caducifolio": True,
        "albedo_copa": 0.17, "altura_tipica": 20.0, "radio_copa_tipico": 5.0,
        "ref": "Cremaschi & Botta (2013); arbolado de alineación clásico porteño",
    },
}

_DEFAULT = ESPECIES["Plátano (Platanus × acerifolia)"]

_CAMPOS = ("rho_copa", "transmitancia", "caducifolio", "albedo_copa",
           "altura_tipica", "radio_copa_tipico", "ref")


def _ruta_db() -> str:
    """data/species_db.json — junto a settings.json, bajo el root del repo."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return os.path.join(base, "data", "species_db.json")


def _cargar_custom() -> dict:
    ruta = _ruta_db()
    try:
        with open(ruta, "r", encoding="utf-8") as handle:
            datos = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _guardar_custom(datos: dict) -> None:
    ruta = _ruta_db()
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as handle:
        json.dump(datos, handle, indent=2, ensure_ascii=False, sort_keys=True)


def especies_db() -> dict:
    """Base completa: originales + overrides/creaciones del usuario."""
    return {**ESPECIES, **_cargar_custom()}


def propiedades_especie(nombre: str) -> dict:
    """Devuelve las propiedades de una especie (con la del plátano como
    valor por defecto para especies desconocidas)."""
    return dict(especies_db().get(nombre, _DEFAULT))


def nombres_especies() -> list[str]:
    return sorted(especies_db().keys())


def validar_especie(nombre: str, props: dict) -> tuple[bool, str]:
    """Valida una entrada completa de especie (el editor la pide toda).
    Devuelve (ok, mensaje de error)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return False, "El nombre de la especie no puede estar vacío."
    errores = []
    for campo, rango in (("rho_copa", (0.0, 1.0)), ("transmitancia", (0.0, 1.0)),
                         ("albedo_copa", (0.0, 1.0))):
        try:
            valor = float(props.get(campo))
        except (TypeError, ValueError):
            return False, f"{campo} debe ser un número."
        if not (rango[0] <= valor <= rango[1]):
            return False, f"{campo} debe estar entre {rango[0]} y {rango[1]}."
    for campo in ("altura_tipica", "radio_copa_tipico"):
        try:
            valor = float(props.get(campo))
        except (TypeError, ValueError):
            return False, f"{campo} debe ser un número."
        if valor <= 0:
            return False, f"{campo} debe ser mayor que 0."
    if not str(props.get("ref", "")).strip():
        return False, "La referencia bibliográfica no puede estar vacía."
    if props.get("caducifolio") not in (True, False):
        return False, "caducifolio debe ser sí o no."
    return True, ""


def guardar_especie(nombre: str, props: dict) -> tuple[bool, str]:
    """Crea o actualiza una especie en la base de datos del usuario.
    Si el nombre pertenece a la base original, queda un override."""
    nombre = (nombre or "").strip()
    ok, error = validar_especie(nombre, props)
    if not ok:
        return False, error
    custom = _cargar_custom()
    custom[nombre] = {
        campo: props.get(campo) for campo in _CAMPOS
    }
    _guardar_custom(custom)
    return True, ""


def eliminar_especie(nombre: str) -> bool:
    """Elimina la especie de la base del usuario. Si era un override de
    una especie original, se restaura el valor de fábrica."""
    nombre = (nombre or "").strip()
    custom = _cargar_custom()
    if nombre not in custom:
        return False
    del custom[nombre]
    _guardar_custom(custom)
    return True


def color_copa(nombre: str) -> str:
    """Color de copa para las vistas 3D según la especie: verde oscuro
    para perennes, verde claro para caducifolias (follaje de verano)."""
    if not nombre:
        return "forestgreen"
    try:
        props = especies_db()[nombre]
    except KeyError:
        return "forestgreen"
    if props.get("caducifolio"):
        return "#66BB6A"
    return "#2E7D32"