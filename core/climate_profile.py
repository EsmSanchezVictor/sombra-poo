"""Perfil de viento y descomposición de la radiación solar.

Perfil logarítmico de viento (capa límite atmosférica neutra,
Stull 1988):

    u(z) = u_ref · ln(z/z0) / ln(z_ref/z0)

con z0 la rugosidad aerodinámica del terreno (tabla de Davenport/
Wieringa). El viento que "siente" un cuerpo debajo de una copa se
reduce según la densidad de copa (atenuación empírica documentada).

Descomposición de la radiación: el GHI (que ya calcula SolarEngine o
el modelo interno) se reparte en directa + difusa según la nubosidad
(fracción difusa por rango de nube, rango de Reindl 1990) y la
reflejada se estima con el albedo de la superficie (onda corta).
"""
from __future__ import annotations

import math

# Rugosidad aerodinámica z0 (m) por tipo de superficie (Wieringa 1992).
Z0_SUPERFICIES = {
    "cesped": 0.03,      # césped corto
    "suelo": 0.05,       # suelo desnudo / tierra
    "asfalto": 0.50,     # superficie urbana lisa (estacionamiento, calle)
    "parque": 0.40,      # parque con vegetación baja dispersa
    "arbolado": 1.00,    # bosque / arbolado denso
    "urbano": 2.00,      # zona urbana densa (edificios bajos)
}

# Velocidad de referencia (m/s) a 10 m para las categorías cualitativas
# de viento que ya usa la app (coincide con McAdams en modelo_con_excel:
# "moderado" = 4 m/s).
VIENTO_CATEGORIA_MS = {
    "nulo": 0.5,
    "moderado": 4.0,
    "fuerte": 10.0,
}


def z0_superficie(clase: str) -> float:
    """Rugosidad aerodinámica de una superficie conocida (m)."""
    return Z0_SUPERFICIES.get(clase, Z0_SUPERFICIES["cesped"])


def velocidad_viento(z: float, u_ref: float, z_ref: float = 10.0,
                     z0: float = 0.03) -> float:
    """Perfil logarítmico: u(z) a partir de u_ref medido a z_ref.

    Si z <= z0 devuelve 0 (estamos dentro del dosel de rugosidad,
    donde el perfil logarítmico no aplica).
    """
    if z_ref <= z0 or z <= z0:
        return 0.0
    return u_ref * math.log(z / z0) / math.log(z_ref / z0)


def atenuacion_copa(rho_copa: float) -> float:
    """Factor (0-1) por el que la copa reduce el viento a nivel de
    persona bajo el árbol. Empírico documentado: copa densa (~0.9)
    corta ~55% de la velocidad; copa abierta (~0.3) corta ~20%."""
    rho = min(max(rho_copa, 0.0), 1.0)
    return 1.0 - 0.6 * rho


def viento_categoria_a_ms(categoria: str) -> float:
    """Mapea las categorías cualitativas de la app a m/s a 10 m."""
    return VIENTO_CATEGORIA_MS.get(categoria, 4.0)


# ---------------------------------------------------------------- radiación

def fraccion_difusa(nubosidad: str) -> float:
    """Fracción difusa del GHI según nubosidad (rango de Reindl 1990,
    simplificado a 3 estados operativos)."""
    return {
        "Despejado": 0.15,
        "Parcial": 0.35,
        "Nublado": 0.65,
    }.get(nubosidad, 0.15)


def descomponer_radiacion(ghi: float, elevacion: float, nubosidad: str = "Despejado",
                          albedo: float = 0.20) -> dict:
    """Descompone GHI (W/m²) en directa, difusa y reflejada.

        DHI  = kd · GHI
        DNI  = (GHI − DHI) / sin(elev)      (normal a los rayos)
        Gref = GHI · albedo                  (onda corta reflejada)

    Devuelve W/m² sobre superficie horizontal (dni se devuelve
    proyectado: dni_horizontal = GHI − DHI, y también normal al haz).
    """
    ghi = max(0.0, ghi)
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