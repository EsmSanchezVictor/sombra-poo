"""Cálculos de geometría de la interfaz, independientes de Tk."""


# v24: compactación HORIZONTAL real.
# El contenido usa casi todo el Canvas; la reducción visual proviene del
# ancho menor reservado al sidebar y de los widgets con ancho explícito,
# no de comprimir tipografías/alturas.
PANEL_CONTENT_RATIO = 0.96
PANEL_HORIZONTAL_SCALE = 0.70
PANEL_ELEMENT_SCALE = PANEL_HORIZONTAL_SCALE  # alias de compatibilidad
PANEL_MIN_FONT_SIZE = 7  # se conserva por compatibilidad; v24 no reduce fuentes


def calcular_ancho_panel(ancho_ventana, ancho_preferido=360, proporcion_maxima=0.4):
    """Calcula un ancho lateral contenido dentro del viewport disponible."""
    ancho_disponible = max(int(ancho_ventana), 1)
    return max(
        1,
        min(int(ancho_preferido), int(ancho_disponible * proporcion_maxima)),
    )


def calcular_geometria_contenido_panel(ancho_canvas, proporcion=PANEL_CONTENT_RATIO):
    """Devuelve ``(x, ancho)`` para un contenido centrado dentro del panel.

    v24: los controles usan por defecto el 96 % del ancho útil del Canvas.
    El margen queda reducido a ~2 % por lado. La reducción horizontal real
    se obtiene achicando el sidebar y los anchos explícitos de widgets, no
    dejando grandes márgenes vacíos. La scrollbar NO forma parte de
    ``ancho_canvas``:
    vive en una columna propia del contenedor, por lo que nunca se
    superpone al contenido.
    """
    ancho = max(int(ancho_canvas), 1)
    try:
        ratio = float(proporcion)
    except (TypeError, ValueError):
        ratio = PANEL_CONTENT_RATIO
    ratio = min(max(ratio, 0.10), 1.0)
    ancho_contenido = max(1, int(round(ancho * ratio)))
    x = max(0, (ancho - ancho_contenido) // 2)
    return x, ancho_contenido


# v24: aproximadamente 30 % menos ancho que la reserva segura de v22/v23.
# Sigue existiendo minsize real en grid, por lo que no reaparece el recorte.
SIDEBAR_MIN_WIDTH = 255
SIDEBAR_MAX_WIDTH = 365
SIDEBAR_VIEWPORT_RATIO = 0.18
SIDEBAR_MAX_VIEWPORT_RATIO = 0.36


def calcular_ancho_sidebar_abierto(
    ancho_ventana,
    proporcion=SIDEBAR_VIEWPORT_RATIO,
    minimo=SIDEBAR_MIN_WIDTH,
    maximo=SIDEBAR_MAX_WIDTH,
    proporcion_maxima=SIDEBAR_MAX_VIEWPORT_RATIO,
):
    """Ancho reservado para ``frame1`` cuando un panel está abierto.

    v24 reduce horizontalmente el lateral, manteniendo la reserva física
    de columna introducida en v22. El límite evita que el lateral domine
    ventanas angostas y el mínimo conserva una zona usable con scroll.
    """
    disponible = max(int(ancho_ventana), 1)
    objetivo = max(int(minimo), int(round(disponible * float(proporcion))))
    limite_ventana = max(1, int(round(disponible * float(proporcion_maxima))))
    return max(1, min(int(maximo), limite_ventana, objetivo))
