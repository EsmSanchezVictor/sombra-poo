"""Cálculos de geometría de la interfaz, independientes de Tk."""


def calcular_ancho_panel(ancho_ventana, ancho_preferido=360, proporcion_maxima=0.4):
    """Calcula un ancho lateral contenido dentro del viewport disponible."""
    ancho_disponible = max(int(ancho_ventana), 1)
    return max(
        1,
        min(int(ancho_preferido), int(ancho_disponible * proporcion_maxima)),
    )