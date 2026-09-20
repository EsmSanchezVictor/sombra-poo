import os
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import math
from core.scene_objects import adaptar_objetos_escena
from core.species import color_copa, propiedades_especie
from core.crown_shapes import CANOPY_SHAPES, DEFAULT_CANOPY_SHAPE, normalize_canopy_shape
from ui.canopy_rendering import draw_canopy_2d
from core.climate_profile import temperatura_diurna_ciclo, VIENTO_CATEGORIA_MS
from core.solar_math import (
    solar_declination_deg, equation_of_time_degrees, standard_meridian_deg,
    timezone_offset_hours, solar_elevation_deg, solar_azimuth_deg,
)
from tkinter import messagebox
from plot_style import CMAP_TEMPERATURA
from core.excel_scene import save_scene_excel, load_scene_excel, apply_parameters_to_vars
from core.materials import get_surface_material, effective_structure_transmittance
from core.surface_energy import (
    solve_surface_energy_balance, cloud_fraction_from_label, downwelling_longwave,
)
from ui.scene3d import render_scene_3d
from ui.solar_indicator import add_solar_indicator_2d
from ui.modal_style import prepare_dialog, dialog_header
from core.vegetation import (
    VegetationConfig, phenology_factor, ground_latent_heat_flux_wm2,
    species_canopy_latent_flux_wm2,
)

# Constantes
sigma = 5.67e-8  # Constante de Stefan-Boltzmann


class Material:
    def __init__(self, alpha, epsilon):
        self.alpha = alpha
        self.epsilon = epsilon


class Arbol:
    def __init__(self, x, y, h, rho_copa, radio_copa, forma_copa=DEFAULT_CANOPY_SHAPE, especie=""):
        self.x = x
        self.y = y
        self.h = h
        self.rho_copa = rho_copa
        self.radio_copa = radio_copa
        self.forma_copa = normalize_canopy_shape(forma_copa)
        self.especie = str(especie or "")


class Estructura:
    def __init__(self, tipo, x1, y1, x2, y2, altura=0, opacidad=1, material=None):
        self.tipo = tipo
        # Una pared es un SEGMENTO orientado: ordenar x/y por separado cambia
        # la pendiente de diagonales. Solo los elementos rectangulares se
        # normalizan a bounding box.
        if tipo == "Pared":
            self.x1, self.y1 = float(x1), float(y1)
            self.x2, self.y2 = float(x2), float(y2)
        else:
            self.x1, self.x2 = sorted((float(x1), float(x2)))
            self.y1, self.y2 = sorted((float(y1), float(y2)))
        self.altura = float(altura)
        self.opacidad = float(opacidad)
        self.material = material


# Materiales predefinidos (valores promedio dentro de los rangos)
materiales = {
    "acero inoxidable": Material(alpha=0.3, epsilon=0.2),
    "aluminio": Material(alpha=0.2, epsilon=0.125),
    "madera tratada": Material(alpha=0.7, epsilon=0.85),
    "policarbonato": Material(alpha=0.85, epsilon=0.9),
    "Policarbonato (paneles)": Material(alpha=0.85, epsilon=0.9),
    "Hormigón": Material(alpha=0.9, epsilon=0.9),
    "PVC (estructuras ligeras)": Material(alpha=0.8, epsilon=0.925),
    "Fibra de vidrio": Material(alpha=0.85, epsilon=0.89),
    "Lámina de polietileno (HDPE)": Material(alpha=0.35, epsilon=0.925),
    "Vidrio templado": Material(alpha=0.85, epsilon=0.9),
    "Ladrillo cerámico": Material(alpha=0.88, epsilon=0.875),
    "Corrugado de hierro": Material(alpha=0.8, epsilon=0.25),
    "ETFE": Material(alpha=0.3, epsilon=0.9),
    "CLT (Madera laminada natural)": Material(alpha=0.7, epsilon=0.85),
    "Aerogel": Material(alpha=0.25, epsilon=0.925),
    "Tierra apisonada": Material(alpha=0.4, epsilon=0.9),
    "Paca de paja": Material(alpha=0.5, epsilon=0.9),
    "Corcho": Material(alpha=0.3, epsilon=0.9),
    "Fibra de carbono": Material(alpha=0.8, epsilon=0.75),
    "Chapa de Zinc": Material(alpha=0.7, epsilon=0.25),
    "Terracota": Material(alpha=0.7, epsilon=0.875),
    "Micelio (hongos)": Material(alpha=0.5, epsilon=0.9),
    "Plástico reciclado": Material(alpha=0.7, epsilon=0.925),
    "Lana de vidrio": Material(alpha=0.3, epsilon=0.9),
    "Caucho": Material(alpha=0.8, epsilon=0.925),
    "Malla de acero": Material(alpha=0.7, epsilon=0.2),
    "Geotextil": Material(alpha=0.4, epsilon=0.9),
    "Tablero de óxido de magnesio": Material(alpha=0.5, epsilon=0.9),
    "Ferrocemento": Material(alpha=0.7, epsilon=0.9),
    "Hempcrete": Material(alpha=0.4, epsilon=0.9),
    "Fotocerámica (Vidrio Fotovoltaico)": Material(alpha=0.3, epsilon=0.9),
    "Concreto Translúcido": Material(alpha=0.5, epsilon=0.9),
    "Materiales de Cambio de Fase (PCMs)": Material(alpha=0.45, epsilon=0.925),
    "Acero Corten": Material(alpha=0.7, epsilon=0.7),
    # FIX (bug #2): alpha estaba en 1.0e-7 (prácticamente cero), físicamente
    # implausible para un composite madera-plástico. Corregido a un valor
    # razonable para el rango típico de absortividad de este material.
    "Composite Madera-Plástico": Material(alpha=0.7, epsilon=0.9),
    "Pinturas Intumescentes": Material(alpha=0.4, epsilon=0.925),
    "Cobre (superficies antibacterianas)": Material(alpha=0.8, epsilon=0.315),
    "Espuma de Poliuretano": Material(alpha=0.3, epsilon=0.9),
    "Concreto Autocurativo": Material(alpha=0.6, epsilon=0.9),
    "Ladrillos de PET reciclado": Material(alpha=0.95, epsilon=0.925),
    "asfalto": Material(alpha=0.95, epsilon=0.95),
    "cemento": Material(alpha=0.6, epsilon=0.9),
    "suelo": Material(alpha=0.4, epsilon=0.9),
}

# v35.5: catálogo visible depurado para la interfaz. Se conserva el diccionario
# ``materiales`` como fuente del modelo físico, pero el usuario ve nombres
# consistentes y sin duplicados. Los dos policarbonatos se mantienen porque
# representan variantes constructivas distintas.
MATERIAL_CHOICES = (
    "Acero inoxidable",
    "Aluminio",
    "Madera tratada",
    "Policarbonato",
    "Policarbonato (paneles)",
    "Hormigón",
    "PVC (estructuras ligeras)",
    "Fibra de vidrio",
    "Lámina de polietileno (HDPE)",
    "Vidrio templado",
    "Ladrillo cerámico",
    "Corrugado de hierro",
    "ETFE",
    "CLT (Madera laminada natural)",
    "Aerogel",
    "Tierra apisonada",
    "Paca de paja",
    "Corcho",
    "Fibra de carbono",
    "Chapa de zinc",
    "Terracota",
    "Micelio (hongos)",
    "Plástico reciclado",
    "Lana de vidrio",
    "Caucho",
    "Malla de acero",
    "Geotextil",
    "Tablero de óxido de magnesio",
    "Ferrocemento",
    "Hempcrete",
    "Fotocerámica (vidrio fotovoltaico)",
    "Concreto Translúcido",
    "Materiales de cambio de fase (PCMs)",
    "Acero Corten",
    "Composite madera-plástico",
    "Pinturas intumescentes",
    "Cobre (superficies antibacterianas)",
    "Espuma de poliuretano",
    "Concreto autocurativo",
    "Ladrillos de PET reciclado",
    "Asfalto",
    "Cemento",
    "Suelo",
)

def _norm_material_display(text):
    import unicodedata
    raw = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().casefold()

_MATERIAL_DISPLAY_BY_NORM = {_norm_material_display(name): name for name in MATERIAL_CHOICES}

def material_display_name(name):
    """Devuelve el nombre canónico visible, tolerando archivos históricos."""
    key = _norm_material_display(name)
    return _MATERIAL_DISPLAY_BY_NORM.get(key, str(name or MATERIAL_CHOICES[0]))

# FIX (bug #1): índice normalizado en minúsculas. La mayoría de las claves de
# arriba tienen mayúsculas ("Hormigón", "Vidrio templado"...), pero el
# material que llega del Excel se compara en minúsculas más abajo. Sin este
# índice, `estructura.material.lower() in materiales` casi nunca matcheaba y
# todo caía en "suelo" en silencio.
MATERIALES_LOWER = {k.lower(): v for k, v in materiales.items()}
# Compatibilidad con proyectos/Excel previos que guardaron el duplicado sin tilde.
MATERIALES_LOWER["concreto translucido"] = materiales["Concreto Translúcido"]


def declinacion_solar(dia_del_año):
    """Declinación solar [°], delegada al núcleo solar compartido."""
    return solar_declination_deg(dia_del_año)


def ecuacion_del_tiempo(dia_del_año):
    """Ecuación del tiempo [grados horarios]."""
    return equation_of_time_degrees(dia_del_año)


def _meridiano_estandar(longitud, huso_horas=None):
    return standard_meridian_deg(longitud, huso_horas)


def _huso_desde_timezone(timezone_name, dia_del_año, hora_local=12.0, year=2026):
    return timezone_offset_hours(
        timezone_name, dia_del_año, hora_local, year=year
    )


def angulo_solar(latitud, longitud, dia_del_año, hora_local, huso_horas=None):
    """Elevación solar en radianes para compatibilidad histórica."""
    return np.radians(
        solar_elevation_deg(
            latitud, longitud, dia_del_año, hora_local, huso_horas
        )
    )


def azimut_solar(latitud, longitud, dia_del_año, hora_local, theta_sol, huso_horas=None):
    """Azimut solar en radianes, 0=norte, horario."""
    elev_deg = np.degrees(float(theta_sol))
    return np.radians(
        solar_azimuth_deg(
            latitud, longitud, dia_del_año, hora_local, huso_horas,
            elevation_deg=elev_deg,
        )
    )


def temperatura_ambiente(hora_local, T_min, T_max, hora_min=6, hora_max=15):
    """Ciclo diurno de temperatura con desfase térmico.

    FIX (bug #4): la versión anterior (`T_min + (T_max-T_min)*sin(pi*hora/24)`)
    ponía el mínimo a medianoche y el máximo al mediodía solar. En la
    realidad el mínimo ocurre cerca del amanecer (hora_min, default 6h) y el
    máximo 2-3 horas después del mediodía (hora_max, default 15h) por
    inercia térmica. Los defaults no rompen los call sites existentes.

    FIX (v4): la corrección de fase de arriba seguía usando una sinusoide
    de período fijo `2*(hora_max-hora_min)` SIN acotar fuera de
    [hora_min, hora_max], así que la curva volvía a subir antes de
    medianoche (con T_min=18°C/T_max=30°C, a las 0h daba ~27°C, casi el
    máximo del día). Ahora delega en `core.climate_profile.
    temperatura_diurna_ciclo`, que da exactamente los mismos valores
    dentro de [hora_min, hora_max] pero decae de forma continua hacia
    T_min durante la noche en vez de seguir oscilando. La misma función
    unificada la usa `core/scenario.py::temperatura_diurna`, así ambos
    módulos comparten un solo ciclo diurno.
    """
    return temperatura_diurna_ciclo(float(hora_local), float(T_min), float(T_max), hora_min, hora_max)


def calcular_sombra_arboles(X, Y, arboles, theta_sol, azimut_sol, elongacion_maxima=6.0):
    """Sombra de cada copa modelada como elipse orientada según el acimut solar.

    FIX (bug #6): antes se trasladaba un círculo de radio fijo, subestimando
    el área de sombra real a sol bajo (amanecer/atardecer), cuando la sombra
    de una copa se alarga y se elipsifica. `elongacion_maxima` evita sombras
    de longitud no acotada cerca del horizonte (theta_sol -> 0).
    """
    sombra = np.ones_like(X)
    if theta_sol <= 0:
        return sombra
    tan_theta = np.tan(max(theta_sol, np.radians(2)))
    for arbol in arboles:
        longitud_sombra = arbol.h / tan_theta
        dx = -longitud_sombra * np.sin(azimut_sol)
        dy = -longitud_sombra * np.cos(azimut_sol)
        cx = arbol.x + dx
        cy = arbol.y + dy

        elongacion = min(1 / max(np.sin(theta_sol), 1e-3), elongacion_maxima)
        semi_eje_mayor = arbol.radio_copa * elongacion
        semi_eje_menor = arbol.radio_copa

        # Coordenadas relativas rotadas al sistema alineado con la sombra
        dx_rel = (X - cx) * np.cos(azimut_sol) - (Y - cy) * np.sin(azimut_sol)
        dy_rel = (X - cx) * np.sin(azimut_sol) + (Y - cy) * np.cos(azimut_sol)

        # dy_rel queda alineado con la dirección de proyección de la sombra;
        # por eso el eje MAYOR debe dividir dy_rel (antes estaba girado 90°).
        dentro_elipse = (dx_rel / semi_eje_menor) ** 2 + (dy_rel / semi_eje_mayor) ** 2 <= 1

        # Si el árbol tiene especie, usar la transmitancia de copa documentada
        # en la biblioteca. Para árboles antiguos/sin especie se conserva la
        # compatibilidad tau = 1-rho_copa.
        tau_copa = 1.0 - float(arbol.rho_copa)
        especie = getattr(arbol, "especie", "")
        if especie:
            try:
                tau_copa = float(propiedades_especie(especie).get("transmitancia", tau_copa))
            except Exception:
                pass
        tau_copa = float(np.clip(tau_copa, 0.0, 1.0))
        sombra[dentro_elipse] *= tau_copa
    return sombra


def _punto_en_poligono(X, Y, poligono):
    """Ray casting vectorizado (numpy) para test de punto-en-polígono.

    Usado por `sombra_estructuras` para calcular la huella real de sombra
    proyectada por una pared, en vez de aproximarla con un bounding box.
    """
    n = len(poligono)
    dentro = np.zeros(X.shape, dtype=bool)
    x1p, y1p = poligono[-1]
    for i in range(n):
        x2p, y2p = poligono[i]
        cond = ((y1p > Y) != (y2p > Y)) & \
               (X < (x2p - x1p) * (Y - y1p) / (y2p - y1p + 1e-12) + x1p)
        dentro ^= cond
        x1p, y1p = x2p, y2p
    return dentro


def sombra_estructuras(X, Y, estructuras, theta_sol, azimut_sol):
    """Fracción geométrica bloqueada por estructuras (modelo estándar).

    Conserva la semántica legacy: opacidad 1 bloquea toda la radiación, sin
    considerar transmitancia óptica del material. El modo avanzado usa
    ``transmitancia_estructuras_avanzada``.
    """
    sombra_total = np.zeros_like(X, dtype=float)
    if theta_sol <= 0:
        return sombra_total
    for estructura in estructuras:
        if getattr(estructura, "tipo", None) not in {"Pared", "Galeria"}:
            continue
        mask = _mascara_sombra_estructura(X, Y, estructura, theta_sol, azimut_sol)
        sombra_total[mask] += float(getattr(estructura, "opacidad", 1.0))
    return np.clip(sombra_total, 0, 1)


_VIENTO_CATEGORIA_A_MS = VIENTO_CATEGORIA_MS


def calcular_coeficiente_conveccion(viento):
    """FIX (bug #5): antes devolvía valores fijos (5/15/25/10 W/m2K) según
    una categoría de texto, ignorando la velocidad de viento real en m/s.
    Ahora usa la correlación simplificada de McAdams para convección forzada
    exterior: h = 5.7 + 3.8 * v (v en m/s). Sigue aceptando categorías de
    texto por compatibilidad, traduciéndolas a una velocidad estimada.
    """
    if isinstance(viento, str):
        text = viento.strip().lower().replace(",", ".")
        if text in _VIENTO_CATEGORIA_A_MS:
            v = _VIENTO_CATEGORIA_A_MS[text]
        else:
            try:
                # Series meteorológicas cargadas en una StringVar llegan como
                # texto numérico (p. ej. "3.2"). Antes se trataban como una
                # categoría desconocida y se sustituían silenciosamente por
                # 2 m/s.
                v = max(0.0, float(text))
            except (TypeError, ValueError):
                v = 2.0
    else:
        v = max(0.0, float(viento))
    return 5.7 + 3.8 * v


def asignar_materiales_grilla(X, Y, estructuras, debug=False):
    """Asigna alpha/epsilon a cada celda de la grilla según el material
    de las estructuras que la cubren. Devuelve (alpha, epsilon).

    Extraído de generar_grafico() para poder testearlo: el material se
    busca con el índice normalizado MATERIALES_LOWER (FIX bug #1) y si no
    se reconoce se avisa y se usa 'suelo' por defecto, en vez de fallar
    en silencio con propiedades equivocadas.
    """
    alpha = np.full_like(X, materiales["suelo"].alpha, dtype=float)
    epsilon = np.full_like(X, materiales["suelo"].epsilon, dtype=float)
    for estructura in estructuras:
        # Esta grilla representa la TEMPERATURA DE LA SUPERFICIE HORIZONTAL
        # del suelo. Una pared o el material de una cubierta no deben pintar
        # el piso con sus propiedades térmicas. Solo los elementos a nivel de
        # suelo (Sendero) modifican alpha/epsilon de la grilla.
        if getattr(estructura, "tipo", None) != "Sendero":
            continue
        mat = MATERIALES_LOWER.get(estructura.material.lower()) if getattr(estructura, "material", None) else None
        if mat is None:
            if debug:
                print(f"[aviso] material no reconocido: {getattr(estructura, 'material', None)!r} "
                      f"— se usan propiedades de 'suelo' por defecto")
            continue
        mask = (X >= estructura.x1) & (X <= estructura.x2) & \
               (Y >= estructura.y1) & (Y <= estructura.y2)
        alpha[mask] = mat.alpha
        epsilon[mask] = mat.epsilon
    return alpha, epsilon



def asignar_propiedades_avanzadas_grilla(X, Y, estructuras, debug=False):
    """Propiedades físicas de la superficie horizontal para el modo avanzado.

    Solo ``Sendero`` modifica el material del suelo, igual que en el modelo
    estándar. Paredes/cubiertas intervienen por su sombra/transmitancia, no
    reemplazando artificialmente el material del piso.
    """
    base_legacy = materiales["suelo"]
    base = get_surface_material("suelo", legacy_alpha=base_legacy.alpha, legacy_epsilon=base_legacy.epsilon)
    props = {
        "alpha": np.full_like(X, base.solar_absorptance, dtype=float),
        "epsilon": np.full_like(X, base.longwave_emissivity, dtype=float),
        "conductivity": np.full_like(X, base.thermal_conductivity, dtype=float),
        "coupling_depth": np.full_like(X, base.coupling_depth_m, dtype=float),
        "heat_capacity": np.full_like(X, base.volumetric_heat_capacity, dtype=float),
    }
    for estructura in estructuras:
        if getattr(estructura, "tipo", None) != "Sendero":
            continue
        name = getattr(estructura, "material", None)
        legacy = MATERIALES_LOWER.get(str(name or "").lower())
        mat = get_surface_material(
            name,
            legacy_alpha=getattr(legacy, "alpha", None),
            legacy_epsilon=getattr(legacy, "epsilon", None),
        )
        if debug and mat.source_quality == "legacy_fallback":
            print(f"[aviso] propiedades avanzadas estimadas para material {name!r}")
        mask = ((X >= estructura.x1) & (X <= estructura.x2)
                & (Y >= estructura.y1) & (Y <= estructura.y2))
        props["alpha"][mask] = mat.solar_absorptance
        props["epsilon"][mask] = mat.longwave_emissivity
        props["conductivity"][mask] = mat.thermal_conductivity
        props["coupling_depth"][mask] = mat.coupling_depth_m
        props["heat_capacity"][mask] = mat.volumetric_heat_capacity
    return props


def _mascara_sombra_estructura(X, Y, estructura, theta_sol, azimut_sol):
    """Máscara geométrica de sombra para pared/galería."""
    if theta_sol <= 0 or getattr(estructura, "tipo", None) not in {"Pared", "Galeria"}:
        return np.zeros_like(X, dtype=bool)
    tan_theta = np.tan(max(theta_sol, np.radians(2)))
    longitud_sombra = float(estructura.altura) / tan_theta if estructura.altura > 0 else 0.0
    dx = -longitud_sombra * np.sin(azimut_sol)
    dy = -longitud_sombra * np.cos(azimut_sol)
    if estructura.tipo == "Pared":
        poligono = np.array([
            [estructura.x1, estructura.y1],
            [estructura.x2, estructura.y2],
            [estructura.x2 + dx, estructura.y2 + dy],
            [estructura.x1 + dx, estructura.y1 + dy],
        ])
    else:
        poligono = np.array([
            [estructura.x1 + dx, estructura.y1 + dy],
            [estructura.x2 + dx, estructura.y1 + dy],
            [estructura.x2 + dx, estructura.y2 + dy],
            [estructura.x1 + dx, estructura.y2 + dy],
        ])
    return _punto_en_poligono(X, Y, poligono)


def transmitancia_estructuras_avanzada(X, Y, estructuras, theta_sol, azimut_sol, debug=False):
    """Transmitancia SW de estructuras para el modelo avanzado.

    A diferencia del legado, un material físicamente transmisivo (vidrio,
    policarbonato, ETFE...) puede dejar pasar radiación incluso con opacidad
    geométrica 1. Los solapamientos multiplican transmitancias.
    """
    tau = np.ones_like(X, dtype=float)
    if theta_sol <= 0:
        return tau
    for estructura in estructuras:
        if getattr(estructura, "tipo", None) not in {"Pared", "Galeria"}:
            continue
        mask = _mascara_sombra_estructura(X, Y, estructura, theta_sol, azimut_sol)
        if not np.any(mask):
            continue
        name = getattr(estructura, "material", None)
        legacy = MATERIALES_LOWER.get(str(name or "").lower())
        tau_eff = effective_structure_transmittance(
            name,
            getattr(estructura, "opacidad", 1.0),
            legacy_alpha=getattr(legacy, "alpha", None),
            legacy_epsilon=getattr(legacy, "epsilon", None),
        )
        if debug:
            print(f"[material avanzado] {name}: tau_estructura={tau_eff:.3f}")
        tau[mask] *= tau_eff
    return np.clip(tau, 0.0, 1.0)



def _vegetation_config_from_vars(vars):
    """Configuración v13 desde proyecto/UI con defaults conservadores."""
    app = vars.get("_app_instance") if isinstance(vars, dict) else None
    settings = getattr(app, "settings", {}) if app is not None else {}

    def val(key, default):
        raw = vars.get("_" + key, settings.get(key, default)) if isinstance(vars, dict) else default
        if hasattr(raw, "get"):
            try:
                raw = raw.get()
            except Exception:
                raw = default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(default)

    return VegetationConfig(
        ground_vegetation_fraction=val("ground_vegetation_fraction", 0.50),
        water_availability=val("vegetation_water_availability", 0.75),
        canopy_water_availability=val("canopy_water_availability", 0.75),
    ).validated()


def _ground_vegetation_fraction_field(X, Y, estructuras, fraction):
    """Fracción vegetal del suelo; senderos se consideran no vegetados."""
    field = np.full_like(X, float(np.clip(fraction, 0.0, 1.0)), dtype=float)
    for estructura in estructuras:
        if getattr(estructura, "tipo", None) != "Sendero":
            continue
        mask = ((X >= estructura.x1) & (X <= estructura.x2)
                & (Y >= estructura.y1) & (Y <= estructura.y2))
        field[mask] = 0.0
    return field


def calcular_sombra_arboles_fenologica(X, Y, arboles, theta_sol, azimut_sol, dia, latitud, elongacion_maxima=6.0):
    """Transmitancia de copa con fenología para el avanzado vegetación v2.

    El modo estándar y el avanzado seco conservan exactamente la transmitancia
    histórica. Solo v2 interpola entre la transmitancia foliada y la de época
    sin hojas de las especies caducifolias.
    """
    sombra = np.ones_like(X, dtype=float)
    diagnostics = []
    if theta_sol <= 0:
        return sombra, diagnostics
    tan_theta = np.tan(max(theta_sol, np.radians(2)))
    for arbol in arboles:
        longitud_sombra = arbol.h / tan_theta
        dx = -longitud_sombra * np.sin(azimut_sol)
        dy = -longitud_sombra * np.cos(azimut_sol)
        cx, cy = arbol.x + dx, arbol.y + dy
        elongacion = min(1 / max(np.sin(theta_sol), 1e-3), elongacion_maxima)
        a_major = arbol.radio_copa * elongacion
        a_minor = arbol.radio_copa
        dx_rel = (X - cx) * np.cos(azimut_sol) - (Y - cy) * np.sin(azimut_sol)
        dy_rel = (X - cx) * np.sin(azimut_sol) + (Y - cy) * np.cos(azimut_sol)
        mask = (dx_rel / a_minor) ** 2 + (dy_rel / a_major) ** 2 <= 1

        especie = getattr(arbol, "especie", "")
        props = propiedades_especie(especie) if especie else {}
        tau_summer = float(props.get("transmitancia", 1.0 - float(arbol.rho_copa)))
        deciduous = bool(props.get("caducifolio", False))
        ph = phenology_factor(dia, latitud, deciduous)
        tau_leaf_off = float(props.get("transmitancia_sin_hojas", max(0.65, tau_summer)))
        tau_eff = tau_leaf_off - ph * (tau_leaf_off - tau_summer) if deciduous else tau_summer
        tau_eff = float(np.clip(tau_eff, 0.0, 1.0))
        sombra[mask] *= tau_eff
        diagnostics.append({
            "especie": especie or "sin especie",
            "phenology_factor": ph,
            "transmitancia_verano": tau_summer,
            "transmitancia_sin_hojas": tau_leaf_off,
            "transmitancia_efectiva": tau_eff,
            "lai_tipico": float(props.get("lai_tipico", 3.0)),
            "kc_et": float(props.get("kc_et", 1.0)),
            "source_quality": props.get("veg_source_quality", "generic_default"),
        })
    return np.clip(sombra, 0.0, 1.0), diagnostics


def _canopy_et_diagnostics(X, Y, arboles, T_amb, rh, viento, I_sol, lw_local, dia, latitud, cfg):
    """ET de copa separada del balance del suelo; devuelve campo + detalle."""
    field = np.zeros_like(X, dtype=float)
    rows = []
    lw_mean = float(np.nanmean(lw_local))
    for arbol in arboles:
        especie = getattr(arbol, "especie", "")
        props = propiedades_especie(especie) if especie else {}
        ph = phenology_factor(dia, latitud, bool(props.get("caducifolio", False)),
                              leaf_off_fraction=cfg.leaf_off_fraction)
        r = species_canopy_latent_flux_wm2(
            air_temp_k=float(T_amb), rh_pct=rh, wind=viento,
            ghi_wm2=float(I_sol), longwave_down_wm2=lw_mean,
            lai=float(props.get("lai_tipico", 3.0)),
            kc=float(props.get("kc_et", 1.0)), phenology=ph,
            water_availability=cfg.canopy_water_availability, config=cfg,
        )
        radius = max(0.1, float(getattr(arbol, "radio_copa", 1.0)))
        mask = (X - float(arbol.x)) ** 2 + (Y - float(arbol.y)) ** 2 <= radius ** 2
        # Solapes: el flujo se suma, con tope global explícito.
        field[mask] += r["latent_heat_flux_wm2"]
        row = dict(r)
        row.update({
            "especie": especie or "sin especie",
            "x": float(arbol.x), "y": float(arbol.y), "radio_copa_m": radius,
            "source_quality": props.get("veg_source_quality", "generic_default"),
        })
        rows.append(row)
    field = np.clip(field, 0.0, cfg.max_canopy_latent_wm2)
    return field, rows


def _surface_model_mode(vars):
    app = vars.get("_app_instance") if isinstance(vars, dict) else None
    if app is not None:
        # Los ajustes avanzados no deben seguir actuando de forma invisible
        # cuando la interfaz correspondiente vuelve a modo simple.
        try:
            if vars is getattr(app, "vars_modelo", None) and app.modo_modelo.get() == "simple":
                return "standard"
            if vars is getattr(app, "vars", None) and app.modo_edicion.get() == "simple":
                return "standard"
        except Exception:
            pass
    if app is not None and hasattr(app, "surface_model_mode"):
        try:
            mode = app.surface_model_mode.get()
            if mode in {"standard", "advanced", "advanced_vegetation"}:
                return mode
        except Exception:
            pass
    value = vars.get("_surface_model_mode", "standard") if isinstance(vars, dict) else "standard"
    if hasattr(value, "get"):
        value = value.get()
    text = str(value).lower()
    return text if text in {"standard", "advanced", "advanced_vegetation"} else "standard"

def _var_value(vars, key, default=None):
    value = vars.get(key, default)
    if hasattr(value, "get"):
        try:
            return value.get()
        except Exception:
            return default
    return value



def _longwave_local_avanzada(vars, X, Y, T_amb, tau_arboles, estructuras, rh, cloud_fraction):
    """LW incidente local aproximada para superficies horizontales.

    Fuera de coberturas usa Brutsaert/nubosidad. Bajo copa se interpola hacia
    emisión de follaje (epsilon~0.97, T~Ta) usando la atenuación de copa como
    proxy de obstrucción del cielo. Bajo una galería se reemplaza parcialmente
    el cielo por la emisividad LW del material de cubierta en su huella real.

    No es todavía un cálculo 3D de factores de vista; evita, sin embargo, el
    error de enfriar una superficie bajo techo como si siguiera viendo todo el
    cielo despejado.
    """
    l_sky, eps_sky = downwelling_longwave(float(T_amb), rh, cloud_fraction)
    ta4 = sigma * float(T_amb) ** 4
    canopy_fraction = np.clip(1.0 - np.asarray(tau_arboles, dtype=float), 0.0, 1.0)
    eps_field = eps_sky * (1.0 - canopy_fraction) + 0.97 * canopy_fraction

    for estructura in estructuras:
        if getattr(estructura, "tipo", None) != "Galeria":
            continue
        # Para LW importa la huella física del techo, no la sombra solar
        # desplazada por el acimut.
        mask = ((X >= estructura.x1) & (X <= estructura.x2)
                & (Y >= estructura.y1) & (Y <= estructura.y2))
        if not np.any(mask):
            continue
        name = getattr(estructura, "material", None)
        legacy = MATERIALES_LOWER.get(str(name or "").lower())
        mat = get_surface_material(
            name,
            legacy_alpha=getattr(legacy, "alpha", None),
            legacy_epsilon=getattr(legacy, "epsilon", None),
        )
        op = float(np.clip(getattr(estructura, "opacidad", 1.0), 0.0, 1.0))
        eps_field[mask] = (1.0 - op) * eps_field[mask] + op * mat.longwave_emissivity

    return np.clip(eps_field, 0.0, 1.0) * ta4, float(eps_sky)


def calcular_campo_termico_superficie(vars, X, Y, theta_sol, azimut_sol, I_sol, T_amb, debug=False):
    """Única fuente de verdad para temperatura superficial de Edición/Modelo.

    ``standard`` reproduce exactamente el balance linealizado histórico.
    ``advanced`` usa Stefan-Boltzmann no lineal, LW atmosférica dependiente de
    Ta/RH/nubosidad, convección y conducción al sustrato, además de óptica de
    materiales transmisivos.
    """
    mode = _surface_model_mode(vars)
    arboles = vars.get("arboles", [])
    estructuras = vars.get("estructuras", [])
    dia = float(_var_value(vars, "dia", 180) or 180)
    latitud = float(_var_value(vars, "lat", 0.0) or 0.0)
    phenology_diag = []
    if mode == "advanced_vegetation":
        tau_arboles, phenology_diag = calcular_sombra_arboles_fenologica(
            X, Y, arboles, theta_sol, azimut_sol, dia, latitud
        )
    else:
        tau_arboles = calcular_sombra_arboles(X, Y, arboles, theta_sol, azimut_sol)
    h_c = calcular_coeficiente_conveccion(_var_value(vars, "viento", "moderado"))

    if mode == "standard":
        sombra_estruct = sombra_estructuras(X, Y, estructuras, theta_sol, azimut_sol)
        tau_total = np.clip(tau_arboles * (1 - sombra_estruct), 0, 1)
        alpha, epsilon = asignar_materiales_grilla(X, Y, estructuras, debug=debug)
        q_solar = alpha * I_sol * tau_total
        h_r = 4 * epsilon * sigma * (T_amb ** 3)
        T = T_amb + q_solar / (h_c + h_r)
        finite = np.isfinite(T)
        T = np.where(finite, T, T_amb)
        return {
            "T": T,
            "tau": tau_total,
            "q_solar": q_solar,
            "h_c": h_c,
            "h_r": h_r,
            "model": "standard",
            "model_label": "Estándar · balance linealizado legacy",
            "diagnostics": {},
        }

    tau_estruct = transmitancia_estructuras_avanzada(
        X, Y, estructuras, theta_sol, azimut_sol, debug=debug
    )
    tau_total = np.clip(tau_arboles * tau_estruct, 0.0, 1.0)
    props = asignar_propiedades_avanzadas_grilla(X, Y, estructuras, debug=debug)
    incident_sw = np.maximum(0.0, float(I_sol)) * tau_total
    rh = float(_var_value(vars, "humedad", 50.0) or 50.0)
    cloudiness = _var_value(vars, "nubosidad", "Despejado")
    cloud_override = vars.get("_cloud_fraction_override")
    if hasattr(cloud_override, "get"):
        cloud_override = cloud_override.get()
    if cloud_override is None or cloud_override == "":
        cloud_fraction = cloud_fraction_from_label(cloudiness)
    else:
        cloud_fraction = min(1.0, max(0.0, float(cloud_override)))
    lw_local, eps_sky_clear = _longwave_local_avanzada(
        vars, X, Y, T_amb, tau_arboles, estructuras, rh, cloud_fraction
    )

    vegetation_diag = None
    latent_ground = 0.0
    if mode == "advanced_vegetation":
        cfg = _vegetation_config_from_vars(vars)
        veg_fraction = _ground_vegetation_fraction_field(
            X, Y, estructuras, cfg.ground_vegetation_fraction
        )
        ground_et = ground_latent_heat_flux_wm2(
            air_temp_k=float(T_amb), rh_pct=rh,
            wind=_var_value(vars, "viento", "moderado"),
            incident_shortwave_wm2=incident_sw,
            longwave_down_wm2=lw_local,
            vegetation_fraction=veg_fraction,
            water_availability=cfg.water_availability,
            config=cfg,
        )
        latent_ground = ground_et["latent_heat_flux_wm2"]
        canopy_field, canopy_rows = _canopy_et_diagnostics(
            X, Y, arboles, T_amb, rh, _var_value(vars, "viento", "moderado"),
            I_sol, lw_local, dia, latitud, cfg
        )
        vegetation_diag = {
            "ground": ground_et,
            "canopy_latent_heat_flux_field_wm2": canopy_field,
            "canopies": canopy_rows,
            "phenology": phenology_diag,
            "config": {
                "ground_vegetation_fraction": cfg.ground_vegetation_fraction,
                "water_availability": cfg.water_availability,
                "canopy_water_availability": cfg.canopy_water_availability,
            },
            "assumptions": [
                "ET de suelo: FAO-56 PM horaria sobre fracción vegetal global",
                "ET de copa se informa separada y no se resta al balance del suelo",
                "LAI/Kc genéricos se usan cuando la especie no tiene datos específicos",
            ],
        }

    energy = solve_surface_energy_balance(
        air_temp_k=float(T_amb),
        incident_shortwave_wm2=incident_sw,
        solar_absorptance=props["alpha"],
        longwave_emissivity=props["epsilon"],
        convective_coefficient_wm2k=h_c,
        thermal_conductivity_wmk=props["conductivity"],
        coupling_depth_m=props["coupling_depth"],
        rh_pct=rh,
        cloud_fraction=cloud_fraction,
        substrate_temp_k=float(T_amb),
        latent_heat_flux_wm2=latent_ground,
        longwave_down_override_wm2=lw_local,
    )
    energy["sky_emissivity_clear_area"] = eps_sky_clear
    if vegetation_diag is not None:
        energy["vegetation"] = vegetation_diag
    T = np.asarray(energy["surface_temp_k"], dtype=float)
    is_veg = mode == "advanced_vegetation"
    return {
        "T": T,
        "tau": tau_total,
        "q_solar": np.asarray(energy["q_shortwave_absorbed"], dtype=float),
        "h_c": h_c,
        "h_r": None,
        "model": mode,
        "model_label": (
            "Avanzado · superficie + vegetación/ET v2" if is_veg
            else "Avanzado · balance energético de superficie v1"
        ),
        "diagnostics": energy,
        "properties": props,
    }

def _aplicar_parametros_app_desde_excel(vars, parametros):
    """Sincroniza controles de la UI con los parámetros cargados.

    ``vars`` incluye ``_app_instance`` en la aplicación real; los tests y usos
    sin GUI simplemente ignoran esta parte.
    """
    app = vars.get('_app_instance') if isinstance(vars, dict) else None
    if app is None:
        return

    modo = str(parametros.get('modo_calculo', '') or '').strip().lower()
    if modo in {'simple', 'advanced'} and hasattr(app, 'modo_modelo'):
        app.modo_modelo.set(modo)

    surface_mode = str(parametros.get('surface_model_mode', '') or '').strip().lower()
    if surface_mode in {'standard', 'advanced', 'advanced_vegetation'} and hasattr(app, 'surface_model_mode'):
        app.surface_model_mode.set(surface_mode)

    for key in ("ground_vegetation_fraction", "vegetation_water_availability", "canopy_water_availability"):
        if key in parametros and hasattr(app, "settings"):
            try:
                app.settings[key] = float(parametros[key])
            except (TypeError, ValueError):
                pass

    if 'simple_temp_air_c' in parametros and hasattr(app, 'simple_temp_air_c'):
        try:
            app.simple_temp_air_c.set(float(parametros['simple_temp_air_c']))
        except (TypeError, ValueError):
            pass
    elif 'T_amb_base_K' in parametros and hasattr(app, 'simple_temp_air_c'):
        try:
            app.simple_temp_air_c.set(float(parametros['T_amb_base_K']) - 273.15)
        except (TypeError, ValueError):
            pass

    if 'simple_rh_pct' in parametros and hasattr(app, 'simple_rh'):
        try:
            app.simple_rh.set(float(parametros['simple_rh_pct']))
        except (TypeError, ValueError):
            pass
    elif 'humedad_relativa_pct' in parametros and hasattr(app, 'simple_rh'):
        try:
            app.simple_rh.set(float(parametros['humedad_relativa_pct']))
        except (TypeError, ValueError):
            pass

    for key, attr in (
        ('nubosidad', 'simple_cloudiness'),
        ('simple_country', 'simple_country'),
        ('simple_city', 'simple_city'),
    ):
        if key in parametros and hasattr(app, attr):
            try:
                getattr(app, attr).set(str(parametros[key]))
            except Exception:
                pass

    if parametros.get("radiation_source_mode") and hasattr(app, "radiation_source_mode"):
        mode_rad = str(parametros.get("radiation_source_mode")).strip().lower()
        if mode_rad in {"clear_sky", "manual_measured", "manual_scenario", "observed_series"}:
            app.radiation_source_mode.set(mode_rad)
    met_name = str(parametros.get("meteorology_csv", "") or "").strip()
    if met_name and hasattr(app, "meteorology_service"):
        candidates = [met_name]
        project = getattr(getattr(app, "project_manager", None), "current_project", None)
        if project is not None:
            candidates.insert(0, os.path.join(project.layout.meteorology_dir, os.path.basename(met_name)))
        for met_path in candidates:
            if os.path.exists(met_path):
                try:
                    app.meteorology_service.load_series(met_path, timezone=app._timezone_actual())
                    app.meteorology_series_path = met_path
                    break
                except Exception:
                    pass
    try:
        app._refresh_meteorology_status()
    except Exception:
        pass

    try:
        app._toggle_modelo_mode()
    except Exception:
        pass


def cargar_excel(vars, filepath=None):
    """Carga geometría y, si existen, parámetros térmicos del Excel.

    Compatibilidad:
    - archivos nuevos: restauran escena + condiciones de cálculo;
    - archivos viejos sin ``Parametros``: cargan la escena y conservan los
      parámetros actuales de la UI;
    - hojas ``Estructuras``/``Árboles`` vacías sin encabezados: se aceptan
      como listas vacías en vez de producir KeyError.
    """
    if filepath is None:
        filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not filepath:
        return None
    try:
        libro = load_scene_excel(filepath)

        vars['arboles'] = []
        for _, row in libro.arboles.iterrows():
            arbol = Arbol(
                row['X'], row['Y'], row['Altura (m)'],
                row['Densidad_copa (0-1)'], row['Radio_copa (m)'],
                forma_copa=row.get('Forma_copa', DEFAULT_CANOPY_SHAPE)
            )
            especie = row.get('Especie', '')
            if pd.notna(especie) and str(especie).strip():
                arbol.especie = str(especie).strip()
            vars['arboles'].append(arbol)

        vars['estructuras'] = []
        for _, row in libro.estructuras.iterrows():
            vars['estructuras'].append(Estructura(
                tipo=row['Tipo'],
                x1=row['X_inicial'], y1=row['Y_inicial'],
                x2=row['X_final'], y2=row['Y_final'],
                altura=row['Altura (m)'],
                opacidad=row['Opacidad (0-1)'],
                material=row['Material'],
            ))

        if libro.parametros:
            apply_parameters_to_vars(vars, libro.parametros)
            _aplicar_parametros_app_desde_excel(vars, libro.parametros)

        messagebox.showinfo(
            "Éxito",
            "Datos cargados correctamente" +
            (" con sus parámetros de cálculo." if libro.parametros else
             ". Archivo antiguo: se conservaron los parámetros actuales del modelo.")
        )
        vars['_update_required'] = True
        return filepath
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
        return None


def guardar_excel(vars, filepath=None, app=None, notify=True):
    """Guarda el estado ACTUAL del modelo, no una mera copia del Excel fuente."""
    if app is None and isinstance(vars, dict):
        app = vars.get('_app_instance')

    if filepath is None:
        project = getattr(getattr(app, "project_manager", None), "current_project", None) if app is not None else None
        if project is not None:
            filepath = project.layout.model_excel
        else:
            filepath = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel files', '*.xlsx')],
            )
    if not filepath:
        return None

    try:
        modo = vars.get('_modo_modelo', 'advanced') if isinstance(vars, dict) else 'advanced'
        if hasattr(modo, 'get'):
            modo = modo.get()
        if app is not None and hasattr(app, 'modo_modelo'):
            modo = app.modo_modelo.get()
        modo = str(modo or 'advanced').lower()
        if modo not in {'simple', 'advanced'}:
            modo = 'advanced'

        save_scene_excel(
            filepath,
            vars.get('arboles', []),
            vars.get('estructuras', []),
            vars,
            calculation_mode=modo,
            origin='modelo',
            app=app,
            extra_parameters={
                'modo_ui_origen': modo,
                'surface_model_mode': _surface_model_mode(vars),
                'ground_vegetation_fraction': getattr(app, 'settings', {}).get('ground_vegetation_fraction', 0.50) if app else 0.50,
                'vegetation_water_availability': getattr(app, 'settings', {}).get('vegetation_water_availability', 0.75) if app else 0.75,
                'canopy_water_availability': getattr(app, 'settings', {}).get('canopy_water_availability', 0.75) if app else 0.75,
                'radiation_source_mode': getattr(getattr(app, 'radiation_source_mode', None), 'get', lambda: 'clear_sky')() if app else 'clear_sky',
                'radiation_source_label': (getattr(app, 'last_meteorology_data', None) or {}).get('source_label', '' ) if app else '',
                'radiation_quality': (getattr(app, 'last_meteorology_data', None) or {}).get('quality', '' ) if app else '',
                'meteorology_csv': os.path.basename(getattr(app, 'meteorology_series_path', '') or '') if app else '',
                'ghi_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('ghi', '' ) if app else '',
                'dni_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('dni', '' ) if app else '',
                'dhi_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('dhi', '' ) if app else '',
            },
        )
        if notify:
            messagebox.showinfo(
                'Modelo',
                'Excel guardado con la escena y los parámetros actuales del cálculo.'
            )
        return filepath
    except Exception as e:
        messagebox.showerror('Error', f'Error al guardar archivo:\n{str(e)}')
        return None

def generar_grafico(vars, frame):
    if '_update_required' not in vars or not vars['_update_required']:
        return

    for widget in frame.winfo_children():
        widget.destroy()

    # FIX (bug #8, parte 1): cerrar cualquier figura anterior antes de crear
    # una nueva, para no acumular figuras de matplotlib en memoria en
    # sesiones largas de uso de la GUI.
    fig_anterior = vars.get('_current_fig')
    if fig_anterior is not None:
        plt.close(fig_anterior)

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    vars['_current_fig'] = fig
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Configuración del espacio
    x = y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)

    # Cálculos principales
    huso_var = vars.get("huso_horas")
    huso_horas = huso_var.get() if hasattr(huso_var, "get") else huso_var
    tz_var = vars.get("timezone")
    timezone_name = tz_var.get() if hasattr(tz_var, "get") else tz_var
    if timezone_name:
        huso_tz = _huso_desde_timezone(timezone_name, vars["dia"].get(), vars["hora"].get())
        if huso_tz is not None:
            huso_horas = huso_tz
    theta_sol = angulo_solar(vars["lat"].get(), vars["lon"].get(), vars["dia"].get(), vars["hora"].get(), huso_horas)
    azimut_sol = azimut_solar(vars["lat"].get(), vars["lon"].get(), vars["dia"].get(), vars["hora"].get(), theta_sol, huso_horas)
    # v29: metadatos SOLO visuales para orientar la iluminación VTK.
    vars["_render_solar_altitude_deg"] = float(np.degrees(theta_sol))
    vars["_render_solar_azimuth_deg"] = float(np.degrees(azimut_sol))
    # v14: radiación observada/manual puede entrar como GHI del instante.
    # Si no hay override, se conserva EXACTAMENTE el comportamiento legacy
    # del Panel 4: I_sol_base * sin(elevación).
    _rad_override = vars.get("_radiation_override_ghi")
    if hasattr(_rad_override, "get"):
        _rad_override = _rad_override.get()
    if _rad_override is None or _rad_override == "":
        I_sol = vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
        radiation_source = "legacy_panel4"
        radiation_quality = "legacy_configured"
    else:
        I_sol = max(0.0, float(_rad_override))
        radiation_source = str(vars.get("_radiation_source_label", "Radiación externa"))
        radiation_quality = str(vars.get("_radiation_quality", "external"))

    vars["_scene_objects"] = adaptar_objetos_escena(vars.get("arboles", []), vars.get("estructuras", []))
    debug_flag = vars.get("debug", False)
    debug = bool(debug_flag.get()) if hasattr(debug_flag, "get") else bool(debug_flag)

    # Temperatura del aire del instante. Una Ta observada tiene prioridad
    # porque corresponde exactamente al instante de la serie; si no existe,
    # modo simple usa T_amb_base y modo detallado conserva el ciclo Tmin/Tmax.
    modo_modelo = vars.get("_modo_modelo", "advanced")
    if hasattr(modo_modelo, "get"):
        modo_modelo = modo_modelo.get()
    air_override = vars.get("_air_temp_override_k")
    if hasattr(air_override, "get"):
        air_override = air_override.get()
    if air_override not in (None, ""):
        T_amb = float(air_override)
    elif str(modo_modelo).lower() == "simple":
        T_amb = float(vars["T_amb_base"].get())
    else:
        T_amb = temperatura_ambiente(vars["hora"].get(), vars["T_min"].get(), vars["T_max"].get())

    thermal = calcular_campo_termico_superficie(
        vars, X, Y, theta_sol, azimut_sol, I_sol, T_amb, debug=debug
    )
    T = thermal["T"]
    sombra_total = thermal["tau"]
    q_solar = thermal["q_solar"]
    h_c = thermal["h_c"]
    h_r = thermal["h_r"]
    surface_mode = thermal["model"]
    surface_model_label = thermal["model_label"]
    surface_diag = thermal.get("diagnostics", {})

    # Guardar datos para 3D
    vars["X"] = X
    vars["Y"] = Y
    vars["T"] = T

    app_instance = vars.get('_app_instance')
    temp_unit = app_instance.get_temperature_unit_symbol() if app_instance else "K"
    distance_unit = app_instance.get_distance_unit() if app_instance else "m"
    T_display = app_instance.convert_temperature_for_display(T) if app_instance else T

    # Configuración del gráfico. Edición y Modelo deben usar exactamente
    # el mismo rango visual: mínimo/máximo reales de la matriz, sin sumar
    # márgenes arbitrarios que hacían parecer distintos dos cálculos iguales.
    tmin = float(np.nanmin(T_display))
    tmax = float(np.nanmax(T_display))

    if debug:
        print("T min/max:", tmin, tmax)
        print("Sombra total min/max:", np.min(sombra_total), np.max(sombra_total))
        print("Radiación efectiva min/max:", np.min(q_solar), np.max(q_solar))

    if not np.isfinite(tmin) or not np.isfinite(tmax):
        tmin, tmax = 290.0, 310.0
    if np.isclose(tmin, tmax):
        niveles = np.linspace(tmin - 0.5, tmax + 0.5, 3)
    else:
        niveles = np.linspace(tmin, tmax, 20)
    niveles = np.sort(np.unique(niveles))

    contorno = ax.contourf(X, Y, T_display, niveles, cmap=CMAP_TEMPERATURA, alpha=0.8)
    ax.contour(X, Y, T_display, niveles, colors='k', linewidths=0.5)
    fig.colorbar(contorno, ax=ax, orientation='horizontal', pad=0.12).set_label(f'Temperatura superficial ({temp_unit})')
    add_solar_indicator_2d(
        ax, vars.get("_render_solar_azimuth_deg"), vars.get("_render_solar_altitude_deg"),
        corner="upper-right",
    )
    ax.set_xlabel(f'Distancia ({distance_unit})')
    ax.set_ylabel(f'Distancia ({distance_unit})')

    if debug:
        print(f"Min T: {np.nanmin(T)}, Max T: {np.nanmax(T)}")

    # Dibujar los objetos con la misma convención visual que Edición.
    if vars.get('arboles'):
        for idx, arbol in enumerate(vars['arboles']):
            draw_canopy_2d(
                ax, arbol, facecolor=color_copa(getattr(arbol, "especie", "")),
                edgecolor="darkgreen", alpha=0.68, zorder=6,
                label="Árboles" if idx == 0 else None,
            )
    for estructura in vars.get('estructuras', []):
        if estructura.tipo == 'Sendero':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1, estructura.y2 - estructura.y1,
                color='gray', alpha=0.3, label=f"Sendero ({estructura.material})",
            ))
        elif estructura.tipo == 'Pared':
            ax.plot(
                [estructura.x1, estructura.x2], [estructura.y1, estructura.y2],
                color='black', linewidth=2, label=f"Pared ({estructura.material})",
            )
        elif estructura.tipo == 'Galeria':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1, estructura.y2 - estructura.y1,
                color='saddlebrown', alpha=0.35, hatch='//',
                label=f"Galería ({estructura.material})",
            ))

    ax.set_title(f'Distribución de temperatura superficial\n{surface_model_label} · fuente radiativa: {radiation_source}')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        vistos = dict(zip(labels, handles))
        ax.legend(vistos.values(), vistos.keys(), loc='upper right', fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.5)

    # Función para manejar clics
    def on_click(event):
        if event.inaxes != ax:
            return

        if 'arboles' in vars:
            for arbol in vars['arboles']:
                if math.dist((event.xdata, event.ydata), (arbol.x, arbol.y)) < 5:
                    editar_elemento(vars, arbol=arbol)
                    temp_sombra = T[int(arbol.y), int(arbol.x)]
                    temp_sombra_display = app_instance.convert_temperature_for_display(temp_sombra) if app_instance else temp_sombra
                    detalles = (
                        f"Árbol en ({arbol.x}, {arbol.y})\n"
                        f"Temperatura: {temp_sombra_display:.2f} {temp_unit}\n"
                        f"Altura: {arbol.h} m\n"
                        f"Densidad copa: {arbol.rho_copa}\n"
                        f"Forma de copa: {normalize_canopy_shape(getattr(arbol, 'forma_copa', DEFAULT_CANOPY_SHAPE))}"
                    )
                    ax.set_title(detalles)
                    fig.canvas.draw_idle()
                    return

        if 'estructuras' in vars:
            for estructura in vars['estructuras']:
                if (estructura.x1 <= event.xdata <= estructura.x2 and estructura.y1 <= event.ydata <= estructura.y2):
                    editar_elemento(vars, estructura=estructura)
                    return

        if surface_mode in {"advanced", "advanced_vegetation"}:
            info_text = (
                f"Balance avanzado:\n"
                f"SW absorbida: {np.mean(surface_diag.get('q_shortwave_absorbed', q_solar)):.1f} W/m²\n"
                f"LW cielo: {surface_diag.get('longwave_down_wm2', 0.0):.1f} W/m²\n"
                f"Emisividad cielo: {surface_diag.get('sky_emissivity', 0.0):.3f}\n"
                f"Coef. convección: {h_c:.1f} W/m²K\n"
                f"LE suelo medio: {np.mean(surface_diag.get('q_latent', 0.0)):.1f} W/m²\n"
                f"Residuo máx.: {np.max(np.abs(surface_diag.get('residual_wm2', 0.0))):.3g} W/m²"
            )
        else:
            info_text = (
                f"Balance estándar:\n"
                f"Radiación solar absorbida: {q_solar.mean():.1f} W/m²\n"
                f"Coef. convección: {h_c:.1f} W/m²K\n"
                f"Coef. radiativo: {h_r.mean():.1f} W/m²K"
            )
        ax.text(0.05, 0.95, info_text, transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8), verticalalignment='top')

    canvas.mpl_connect('button_press_event', on_click)
    canvas.draw()

    # FIX (bug #8, parte 2): se eliminó el bloque que volvía a destruir los
    # widgets del frame y recreaba un segundo FigureCanvasTkAgg del mismo
    # `fig` justo después de dibujar el primero (código residual de un
    # refactor anterior). Con el fix de arriba queda un único canvas por
    # llamada, ya conectado a `on_click`.
    vars['_update_required'] = True

    return {
        "T": T,
        "shadow": sombra_total,
        "meta": {
            "hora": vars["hora"].get() if hasattr(vars.get("hora"), "get") else vars.get("hora"),
            "dia": vars["dia"].get() if hasattr(vars.get("dia"), "get") else vars.get("dia"),
            "lat": vars["lat"].get() if hasattr(vars.get("lat"), "get") else vars.get("lat"),
            "lon": vars["lon"].get() if hasattr(vars.get("lon"), "get") else vars.get("lon"),
            "I_sol": float(I_sol),
            "radiation_source": radiation_source,
            "radiation_quality": radiation_quality,
            "radiation_dni": vars.get("_radiation_override_dni"),
            "radiation_dhi": vars.get("_radiation_override_dhi"),
            "cloud_fraction": vars.get("_cloud_fraction_override"),
            "surface_model": surface_mode,
            "surface_model_label": surface_model_label,
            "sky_emissivity": (float(surface_diag.get("sky_emissivity")) if surface_mode in {"advanced", "advanced_vegetation"} else None),
            "energy_residual_max_wm2": (float(np.max(np.abs(surface_diag.get("residual_wm2", 0.0)))) if surface_mode in {"advanced", "advanced_vegetation"} else None),
            "latent_heat_mean_wm2": (float(np.mean(surface_diag.get("q_latent", 0.0))) if surface_mode == "advanced_vegetation" else 0.0),
        },
    }


def editar_elemento(vars, arbol=None, estructura=None):
    """Editor del Modelo con el mismo lenguaje visual que Edición (v35.6)."""
    app = vars.get("_app_instance") if isinstance(vars, dict) else None
    parent = getattr(app, "root", None)
    dialog = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
    dialog.title("Editar elemento")
    prepare_dialog(dialog, parent, modal=True, resizable=False)

    cont = ttk.Frame(dialog, padding=(18, 16, 18, 16))
    cont.pack(fill="both", expand=True)
    cont.columnconfigure(0, weight=1)
    es_arbol = arbol is not None
    dialog_header(
        cont,
        "Editar árbol" if es_arbol else "Editar estructura",
        "Ajustá los datos del elemento y guardá para regenerar el Modelo.",
        layout="grid",
    )
    form = ttk.Frame(cont)
    form.grid(row=1, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)
    entries = {}

    if es_arbol:
        fields = [
            ("X", arbol.x), ("Y", arbol.y), ("Altura (m)", arbol.h),
            ("Densidad Copa", arbol.rho_copa), ("Radio Copa", arbol.radio_copa),
        ]
    else:
        fields = [
            ("X1", estructura.x1), ("Y1", estructura.y1),
            ("X2", estructura.x2), ("Y2", estructura.y2),
            ("Altura (m)", estructura.altura), ("Opacidad", estructura.opacidad),
            ("Material", estructura.material),
        ]

    for i, (label, value) in enumerate(fields):
        ttk.Label(form, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=(0, 14), pady=6)
        if label == "Material":
            entry = ttk.Combobox(form, values=MATERIAL_CHOICES, state="readonly", width=32)
            entry.set(material_display_name(value))
        else:
            entry = ttk.Entry(form, width=34)
            entry.insert(0, str(value))
        entry.grid(row=i, column=1, sticky="ew", pady=6)
        entries[label] = entry

    combo_forma = None
    if es_arbol:
        row_forma = len(fields)
        ttk.Label(form, text="Forma de copa:").grid(row=row_forma, column=0, sticky="w", padx=(0, 14), pady=6)
        combo_forma = ttk.Combobox(form, values=CANOPY_SHAPES, state="readonly", width=32)
        combo_forma.set(normalize_canopy_shape(getattr(arbol, "forma_copa", DEFAULT_CANOPY_SHAPE)))
        combo_forma.grid(row=row_forma, column=1, sticky="ew", pady=6)

    def guardar_cambios():
        try:
            if es_arbol:
                x = float(entries["X"].get()); y = float(entries["Y"].get())
                h = float(entries["Altura (m)"].get())
                rho = float(entries["Densidad Copa"].get())
                radio = float(entries["Radio Copa"].get())
                if h <= 0 or radio <= 0:
                    raise ValueError("altura_radio")
                if not 0 <= rho <= 1:
                    raise ValueError("densidad")
                arbol.x, arbol.y, arbol.h = x, y, h
                arbol.rho_copa, arbol.radio_copa = rho, radio
                if combo_forma is not None:
                    arbol.forma_copa = normalize_canopy_shape(combo_forma.get())
            else:
                x1 = float(entries["X1"].get()); y1 = float(entries["Y1"].get())
                x2 = float(entries["X2"].get()); y2 = float(entries["Y2"].get())
                altura = float(entries["Altura (m)"].get())
                opacidad = float(entries["Opacidad"].get())
                if altura < 0:
                    raise ValueError("altura")
                if not 0 <= opacidad <= 1:
                    raise ValueError("opacidad")
                estructura.x1, estructura.y1, estructura.x2, estructura.y2 = x1, y1, x2, y2
                estructura.altura, estructura.opacidad = altura, opacidad
                estructura.material = entries["Material"].get()
            dialog.destroy()
            vars["_update_required"] = True
            generar_grafico(vars, vars["graph_frame"])
            if app is not None and hasattr(app, "mark_dirty"):
                app.mark_dirty()
        except ValueError as exc:
            msg = {
                "altura_radio": "La altura y el radio de copa deben ser mayores que cero.",
                "densidad": "La densidad de copa debe estar entre 0 y 1.",
                "altura": "La altura no puede ser negativa.",
                "opacidad": "La opacidad debe estar entre 0 y 1.",
            }.get(str(exc), "Revisá los valores numéricos ingresados.")
            messagebox.showerror("Valores inválidos", msg, parent=dialog)

    actions = ttk.Frame(cont)
    actions.grid(row=2, column=0, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancelar", command=dialog.destroy).pack(side="left", padx=(0, 8))
    ttk.Button(actions, text="Guardar cambios", command=guardar_cambios, style="DialogPrimary.TButton").pack(side="left")
    dialog.bind("<Return>", lambda _e: guardar_cambios())
    next(iter(entries.values())).focus_set()


def generar_3d(vars, frame=None):
    """Renderiza la escena 3D del Modelo en el contenedor compartido.

    Usa VTK embebido cuando está disponible y Matplotlib embebido como
    fallback. X/Y/T provienen del cálculo 2D ya ejecutado.
    """
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return None

    app = vars.get("_app_instance")
    if frame is None and app is not None and hasattr(app, "_get_scene_view_frames"):
        _view2d, frame, notebook = app._get_scene_view_frames("modelo")
        notebook.select(frame)
    if frame is None:
        messagebox.showerror(
            "Vista 3D",
            "No se encontró el contenedor 3D embebido. Regenere el gráfico desde el Panel Modelo.",
        )
        return None

    try:
        return render_scene_3d(vars, frame, title="Vista 3D — Modelo · sombra y temperatura")
    except Exception as exc:
        messagebox.showerror("Vista 3D", f"No se pudo generar la vista 3D:\n{exc}")
        return None

def cargar_preset(config, vars):
    """Aplica configuraciones rápidas coherentes con hemisferio y nubosidad."""
    config = str(config or "").strip().lower()
    lat_value = vars.get("lat", 0.0) if isinstance(vars, dict) else 0.0
    if hasattr(lat_value, "get"):
        try:
            lat_value = lat_value.get()
        except Exception:
            lat_value = 0.0
    try:
        southern = float(lat_value) < 0.0
    except (TypeError, ValueError):
        southern = False

    # 21 Jun ~= día 172; 21 Dic ~= día 355.
    summer_day = 355 if southern else 172
    winter_day = 172 if southern else 355
    presets = {
        "verano": {"T_min": 298, "T_max": 315, "I_sol_base": 1000, "dia": summer_day},
        "invierno": {"T_min": 275, "T_max": 290, "I_sol_base": 600, "dia": winter_day},
        "soleado": {"I_sol_base": 1200, "nubosidad": "Despejado"},
        "nublado": {"I_sol_base": 300, "nubosidad": "Nublado"},
    }
    if config not in presets:
        raise ValueError(f"Preset desconocido: {config}")

    for key, value in presets[config].items():
        target = vars.get(key) if isinstance(vars, dict) else None
        if hasattr(target, "set"):
            target.set(value)
        elif isinstance(vars, dict):
            vars[key] = value

    # Mantener la fecha ISO sincronizada: _fecha_modelo_actual prioriza este
    # campo sobre el día juliano y de otro modo un preset estacional podía
    # quedar visualmente cambiado pero calcular con una fecha anterior.
    if isinstance(vars, dict) and config in {"verano", "invierno"}:
        year_value = vars.get("_year", datetime.now().year)
        if hasattr(year_value, "get"):
            try:
                year_value = year_value.get()
            except Exception:
                year_value = datetime.now().year
        try:
            year = int(year_value)
        except (TypeError, ValueError):
            year = datetime.now().year
        day_value = vars.get("dia")
        day = int(day_value.get() if hasattr(day_value, "get") else day_value)
        date_value = (datetime(year, 1, 1) + timedelta(days=max(1, day) - 1)).date()
        vars["_date_iso"] = date_value.isoformat()
        vars["_year"] = year

    if isinstance(vars, dict):
        vars["_update_required"] = True
