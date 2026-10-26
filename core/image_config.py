"""Resoluciones fotográficas compartidas sin interfaz ni OpenCV."""
# Resoluciones cuadradas permitidas para el análisis fotográfico/térmico.
# v20: el valor de trabajo predeterminado baja a 128x128 para equilibrar
# detalle espacial, RAM y latencia de Confort. El modo avanzado permite
# seleccionar cualquier múltiplo de 32 entre 64 y 640.
MATRIX_SIZE_MIN = 64
MATRIX_SIZE_MAX = 640
MATRIX_SIZE_STEP = 32
DEFAULT_MATRIX_SIZE = 128
MATRIX_SIZE_OPTIONS = tuple(range(MATRIX_SIZE_MIN, MATRIX_SIZE_MAX + 1, MATRIX_SIZE_STEP))


def normalize_matrix_size(value, default=DEFAULT_MATRIX_SIZE):
    """Normaliza una resolución de matriz al rango admitido.

    Se usa al recuperar proyectos previos o valores editados externamente.
    Si el valor no es un múltiplo exacto de 32, se aproxima al más cercano.
    """
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = int(default)
    n = max(MATRIX_SIZE_MIN, min(MATRIX_SIZE_MAX, n))
    n = int(round(n / MATRIX_SIZE_STEP) * MATRIX_SIZE_STEP)
    return max(MATRIX_SIZE_MIN, min(MATRIX_SIZE_MAX, n))

