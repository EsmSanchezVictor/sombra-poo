"""Perfil climático simplificado: temperatura, viento y radiación.

Este módulo concentra relaciones que antes estaban duplicadas en distintas
partes de la aplicación. Las funciones son deliberadamente simples y deben
interpretarse como modelos operativos, no como sustitutos de una estación
meteorológica o de un modelo microclimático CFD.
"""
from __future__ import annotations

import math

# Rugosidad aerodinámica z0 (m), entendida como CLASE DEL ENTORNO y no como
# propiedad intrínseca del material. El valor de "asfalto" corresponde a una
# superficie muy lisa con fetch abierto; en una calle urbana debe elegirse
# "urbano" y en un parque, "parque", aunque el piso local sea asfalto.
Z0_SUPERFICIES = {
    "asfalto": 0.0002,
    "cesped": 0.03,
    "suelo": 0.01,
    "parque": 0.30,
    "arbolado": 1.00,
    "urbano": 1.00,
    "urbano_denso": 2.00,
}

VIENTO_CATEGORIA_MS = {
    "nulo": 0.5,
    "moderado": 4.0,
    "fuerte": 10.0,
}


def temperatura_diurna_ciclo(
    hora: float,
    t_min: float,
    t_max: float,
    hora_min: float = 6.0,
    hora_max: float = 15.0,
) -> float:
    """Ciclo continuo y periódico de temperatura del aire (24 h).

    Entre ``hora_min`` y ``hora_max`` usa media onda coseno de Tmin a Tmax.
    Desde Tmax hasta la Tmin del día siguiente usa otra media onda coseno.
    El resultado es continuo, 24-h periódico y queda acotado entre Tmin/Tmax.

    Es un perfil empírico de trabajo. Para reconstrucciones meteorológicas de
    alta precisión conviene reemplazarlo por datos horarios medidos.
    """
    hora = float(hora)
    t_min = float(t_min)
    t_max = float(t_max)
    hora_min = float(hora_min)
    hora_max = float(hora_max)

    if not math.isfinite(hora) or not math.isfinite(t_min) or not math.isfinite(t_max):
        raise ValueError("hora, t_min y t_max deben ser valores finitos.")
    if t_max < t_min:
        raise ValueError("t_max debe ser mayor o igual que t_min.")
    if not (0.0 <= hora_min < 24.0 and 0.0 <= hora_max < 24.0):
        raise ValueError("hora_min y hora_max deben estar entre 0 y 24 h.")

    dia_span = (hora_max - hora_min) % 24.0
    if not (0.0 < dia_span < 24.0):
        raise ValueError("hora_min y hora_max no pueden coincidir.")
    noche_span = 24.0 - dia_span

    if math.isclose(t_min, t_max):
        return t_min

    amplitud = (t_max - t_min) / 2.0
    media = (t_max + t_min) / 2.0
    h_rel = (hora - hora_min) % 24.0

    if h_rel <= dia_span:
        return media - amplitud * math.cos(math.pi * h_rel / dia_span)

    x = h_rel - dia_span
    return media + amplitud * math.cos(math.pi * x / noche_span)


def z0_superficie(clase: str) -> float:
    """Rugosidad aerodinámica del ENTORNO (m)."""
    return Z0_SUPERFICIES.get(str(clase).lower(), Z0_SUPERFICIES["cesped"])


def velocidad_viento(z: float, u_ref: float, z_ref: float = 10.0, z0: float = 0.03) -> float:
    """Perfil logarítmico neutro: u(z) desde u_ref medido a z_ref.

    No aplica dentro de la subcapa de rugosidad; si z <= z0 devuelve 0.
    """
    z = float(z)
    u_ref = max(0.0, float(u_ref))
    z_ref = float(z_ref)
    z0 = float(z0)
    if z0 <= 0 or z_ref <= z0 or z <= z0:
        return 0.0
    return u_ref * math.log(z / z0) / math.log(z_ref / z0)


def atenuacion_copa(rho_copa: float) -> float:
    """Factor empírico 0-1 de reducción de viento local bajo copa."""
    rho = min(max(float(rho_copa), 0.0), 1.0)
    return 1.0 - 0.6 * rho


def viento_categoria_a_ms(categoria: str) -> float:
    """Mapea categorías cualitativas o texto numérico a velocidad en m/s."""
    text = str(categoria).strip().lower().replace(",", ".")
    if text in VIENTO_CATEGORIA_MS:
        return VIENTO_CATEGORIA_MS[text]
    try:
        return max(0.0, float(text))
    except (TypeError, ValueError):
        return 4.0


# ---------------------------------------------------------------- radiación

def fraccion_difusa(nubosidad: str) -> float:
    """Fracción difusa operativa del GHI para tres estados cualitativos."""
    return {
        "Despejado": 0.15,
        "Parcial": 0.35,
        "Nublado": 0.65,
    }.get(nubosidad, 0.15)


def factor_ghi_nubosidad(nubosidad: str) -> float:
    """Factor empírico para convertir GHI de cielo claro en GHI escenario.

    Úsese SOLO cuando el GHI de entrada proviene de un modelo de cielo claro.
    Si el GHI es medido/observado, no debe volver a atenuarse.
    """
    return {
        "Despejado": 1.00,
        "Parcial": 0.65,
        "Nublado": 0.30,
    }.get(nubosidad, 1.00)


def descomponer_radiacion(
    ghi: float,
    elevacion: float,
    nubosidad: str = "Despejado",
    albedo: float = 0.20,
) -> dict:
    """Descompone un GHI YA DEFINIDO en directa, difusa y reflejada.

    Conserva la identidad horizontal::

        GHI = DNI * sin(elevacion) + DHI

    ``nubosidad`` modifica la fracción difusa, pero no atenúa otra vez el GHI.
    Para atenuar un GHI de cielo claro usar :func:`factor_ghi_nubosidad` antes.
    """
    ghi = max(0.0, float(ghi))
    elevacion = float(elevacion)
    albedo = min(max(float(albedo), 0.0), 1.0)
    kd = fraccion_difusa(nubosidad)
    dhi = kd * ghi
    directa_horizontal = max(0.0, ghi - dhi)
    seno = math.sin(math.radians(max(elevacion, 0.0)))
    dni_normal = directa_horizontal / seno if seno > 0.01 else 0.0
    return {
        "ghi": ghi,
        "dhi": dhi,
        "directa_horizontal": directa_horizontal,
        "dni_normal": dni_normal,
        "reflejada": ghi * albedo,
        "nubosidad": nubosidad,
        "albedo": albedo,
    }
