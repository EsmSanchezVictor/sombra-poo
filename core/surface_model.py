"""Modelo de superficies y geometría solar sin dependencias de interfaz.

Extraído de modelo_con_excel.py, conservando las ecuaciones y tablas.
"""
from core.climate_profile import velocidad_viento, viento_categoria_a_ms, temperatura_diurna_ciclo, VIENTO_CATEGORIA_MS
import numpy as np
import math
from core.effective_scenario import effective_model
from core.scene_objects import adaptar_objetos_escena
from core.species import propiedades_especie
from core.crown_shapes import DEFAULT_CANOPY_SHAPE, normalize_canopy_shape
from core.solar_math import (solar_declination_deg, equation_of_time_degrees, standard_meridian_deg,
    timezone_offset_hours, solar_elevation_deg, solar_azimuth_deg)
from core.materials import get_surface_material, effective_structure_transmittance
from core.surface_energy import solve_surface_energy_balance, cloud_fraction_from_label, downwelling_longwave
from core.vegetation import (VegetationConfig, phenology_factor, ground_latent_heat_flux_wm2, species_canopy_latent_flux_wm2)
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


def _huso_desde_timezone(timezone_name, dia_del_año, hora_local=12.0, year=None):
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
    from core.climate_profile import viento_categoria_a_ms
    v = viento_categoria_a_ms(viento)
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
            air_temp_k=float(T_amb), rh_pct=rh, wind=velocidad_viento(2.0, viento_categoria_a_ms(viento)),
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
    app = vars.get('_app_instance') if isinstance(vars, dict) else None
    mode = _var_value(vars, '_modo_modelo', 'advanced')
    selected = _var_value(vars, '_surface_model_mode', 'standard')
    if app is not None:
        if vars is getattr(app, 'vars_modelo', None):
            mode = app.modo_modelo.get()
        elif vars is getattr(app, 'vars', None):
            mode = app.modo_edicion.get()
        if hasattr(app, 'surface_model_mode'):
            selected = app.surface_model_mode.get()
    return effective_model(mode, selected, surface=True)


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
    if not np.isfinite(float(T_amb)) or float(T_amb) <= 0 or not np.isfinite(float(I_sol)) or float(I_sol) < 0:
        raise ValueError('Temperatura Kelvin o radiación superficial inválida')
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
    h_c = calcular_coeficiente_conveccion(_var_value(vars, "_effective_wind_ref_10m", _var_value(vars, "viento", "moderado")))

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
    rh = float(_var_value(vars, "_effective_rh_pct", _var_value(vars, "humedad", 50.0)))
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
            wind=velocidad_viento(2.0, viento_categoria_a_ms(_var_value(vars, "_effective_wind_ref_10m", _var_value(vars, "viento", "moderado")))),
            incident_shortwave_wm2=incident_sw,
            longwave_down_wm2=lw_local,
            vegetation_fraction=veg_fraction,
            water_availability=cfg.water_availability,
            config=cfg,
        )
        latent_ground = ground_et["latent_heat_flux_wm2"]
        canopy_field, canopy_rows = _canopy_et_diagnostics(
            X, Y, arboles, T_amb, rh, _var_value(vars, "_effective_wind_ref_10m", _var_value(vars, "viento", "moderado")),
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
