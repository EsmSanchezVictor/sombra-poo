"""Índices de confort térmico y conversión de instrumentos.

Lo que ofrece (todas fórmulas publicadas, reproducibles):

1. `globo_negro_a_tmrt()` — conversión de temperatura de globo negro
   (Tg, termómetro de globo de 150 mm) a temperatura media radiante
   Tmrt, ISO 7726. Es el paso obligado para usar una medición de campo
   como dato de calibración (el globo no mide Tmrt directo).

2. `indice_calor()` — Heat Index del NWS (Rothfusz, 1990), el índice
   operativo más usado en clima urbano. Exacto dentro de su rango de
   validez (T ≥ 26.7 °C); por debajo devuelve la temperatura del aire.

3. `temperatura_aparente()` — Apparent Temperature de Steadman (1984),
   versión del Bureau of Meteorology de Australia: combina T, humedad
   y viento. Válida en todo el rango de temperaturas.

4. `categoria_estres()` — clasificación del NWS por bandas.

5. `grados_hora()` — integral temporal del exceso (o déficit) sobre un
   umbral, en °C·h — el "cuánto calor acumula el día" que sirve para
   comparar escenarios de arbolado.

LIMITACIÓN DOCUMENTADA: el UTCI completo (Universal Thermal Climate
Index, Bröde et al. 2012) es un polinomio de ~40 términos calibrado
sobre el modelo fisiológico de Fiala; NO se reimplementa acá — se
delega en la librería `pythermalcomfort` (dependencia opcional, la
misma que usa el clima urbano para reportar UTCI oficial). Si la
librería no está instalada, `utci()` devuelve None y la UI lo indica
en lugar de fabricar un valor.
"""
from __future__ import annotations

import math

UTCI_DISPONIBLE = False
try:  # dependencia opcional — la app funciona sin ella
    from pythermalcomfort.models import utci as _utci_pkg  # type: ignore

    UTCI_DISPONIBLE = True
except ImportError:
    _utci_pkg = None

# ---------------------------------------------------------------- instrumentos

def globo_negro_a_tmrt(tg: float, ta: float, v: float,
                       diametro: float = 0.15, emisividad: float = 0.97) -> float:
    """Temperatura media radiante desde globo negro (ISO 7726, globo de
    150 mm):

        Tmrt = [ (Tg+273)^4 + (1.1e8 · v^0.6 / (ε · D^0.4)) · (Tg − Ta) ]^0.25 − 273

    con Tg, Ta en °C, v en m/s (medida a la altura del globo), D en m.
    Para globo de 150 mm: D^0.4 ≈ 0.4715.
    """
    if tg is None or ta is None or v is None:
        raise ValueError("Tg, Ta y v son obligatorios para convertir el globo.")
    if v < 0:
        raise ValueError("La velocidad del viento no puede ser negativa.")
    if diametro <= 0 or emisividad <= 0:
        raise ValueError("Diámetro y emisividad deben ser positivos.")
    globo_k = tg + 273.15
    termino_viento = (1.1e8 * (v ** 0.6)) / (emisividad * (diametro ** 0.4))
    tmrt_k = (globo_k ** 4 + termino_viento * (tg - ta)) ** 0.25
    return tmrt_k - 273.15


# ---------------------------------------------------------------- humedad

def presion_vapor(ta: float, rh: float) -> float:
    """Presión de vapor real en hPa (fórmula de Magnus)."""
    return rh / 100.0 * 6.105 * math.exp(17.27 * ta / (237.7 + ta))


# ---------------------------------------------------------------- índices

def indice_calor(ta: float, rh: float) -> float:
    """Heat Index del NWS (Rothfusz 1990), válido para T ≥ 26.7 °C.

    T en °C, RH en %. Debajo de 26.7 °C devuelve T (el índice no se
    define). Incluye los dos ajustes del NWS (aire seco/caluroso y
    húmedo/cálido).
    """
    if rh < 0 or rh > 100:
        raise ValueError("RH debe estar entre 0 y 100.")
    if ta < 26.7:
        return ta
    t = 9.0 / 5.0 * ta + 32.0  # a °F (la fórmula del NWS es en °F)
    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    if rh < 13 and 80 <= t <= 112:
        hi -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t - 95.0)) / 17.0)
    elif rh > 85 and 80 <= t <= 87:
        hi += ((rh - 85.0) / 10.0) * ((87.0 - t) / 5.0)
    return (hi - 32.0) * 5.0 / 9.0


def temperatura_aparente(ta: float, rh: float, v: float) -> float:
    """Apparent Temperature de Steadman (1984), versión BoM Australia:

        AT = Ta + 0.33·e − 0.70·v − 4.00     (e en hPa, v en m/s)

    El término −0.70·v modela el enfriamiento por viento (efecto
    "wind chill" sobre piel húmeda) y 0.33·e el efecto de la humedad.
    """
    if v < 0:
        raise ValueError("La velocidad del viento no puede ser negativa.")
    e = presion_vapor(ta, rh)
    return ta + 0.33 * e - 0.70 * v - 4.00


def utci(ta: float, tmrt: float, v: float, rh: float) -> float | None:
    """UTCI oficial (Bröde et al. 2012, modelo de Fiala) delegado en
    `pythermalcomfort`. Devuelve None si la librería no está instalada
    (la app funciona sin ella y la UI lo informa)."""
    if _utci_pkg is None:
        return None
    if v < 0:
        raise ValueError("La velocidad del viento no puede ser negativa.")
    if rh < 0 or rh > 100:
        raise ValueError("RH debe estar entre 0 y 100.")
    resultado = _utci_pkg(tdb=float(ta), tr=float(tmrt), v=float(v), rh=float(rh))
    # pythermalcomfort 4.x devuelve un objeto UTCI (atributo `.utci`);
    # las 3.x devolvían un DataFrame — se aceptan todos para no romper
    # con ninguna versión instalada.
    if hasattr(resultado, "utci"):
        return float(resultado.utci)
    if hasattr(resultado, "iloc"):
        return float(resultado["utci"].iloc[0])
    return float(resultado)


def categoria_utci(valor: float | None) -> str:
    """Banda de estrés del UTCI (Bröde et al. 2012)."""
    if valor is None:
        return "UTCI no disponible"
    if valor <= 9:
        return "Sin estrés térmico" if valor >= 0 else "Estrés por frío"
    if valor < 26:
        return "Sin estrés térmico"
    if valor < 32:
        return "Estrés de calor moderado"
    if valor < 38:
        return "Estrés de calor fuerte"
    if valor < 46:
        return "Estrés de calor muy fuerte"
    return "Estrés de calor extremo"


# ---------------------------------------------------------------- categorías

def categoria_estres(valor: float, indice: str = "heat") -> str:
    """Banda de estrés del NWS (Heat Index en °C)."""
    if indice == "heat":
        if valor < 26.7:
            return "Sin estrés"
        if valor < 32.2:
            return "Precaución"
        if valor < 39.5:
            return "Mucha precaución"
        if valor < 51.1:
            return "Peligro"
        return "Peligro extremo"
    # temperatura aparente: bandas más suaves (es un índice de todo el año)
    if valor < 24:
        return "Confortable"
    if valor < 27:
        return "Ligeramente cálido"
    if valor < 32:
        return "Cálido"
    if valor < 38:
        return "Muy cálido"
    return "Calor extremo"


# ---------------------------------------------------------------- integrales

def grados_hora(series, umbral: float, por_encima: bool = True) -> float:
    """Integral temporal de la diferencia contra un umbral (°C·h).

    `series` es una lista de (hora, valor). Si por_encima=True suma
    (valor − umbral) solo donde valor > umbral; si False suma
    (umbral − valor) donde valor < umbral. La suma usa el promedio
    entre muestras consecutivas (regla del trapecio), así no depende
    del espaciado horario.
    """
    if not series:
        return 0.0
    total = 0.0
    for (h1, v1), (h2, v2) in zip(series, series[1:]):
        dt = max(h2 - h1, 0.0)
        if dt <= 0:
            continue
        for v in (v1, v2):
            delta = (v - umbral) if por_encima else (umbral - v)
            total += max(delta, 0.0) * dt / 2.0
    return total