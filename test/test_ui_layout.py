from ui.layout import calcular_ancho_panel


def test_panel_usa_solo_una_fraccion_en_ventana_angosta():
    assert calcular_ancho_panel(600) == 240


def test_panel_respeta_el_ancho_preferido_en_ventana_grande():
    assert calcular_ancho_panel(1920) == 360


def test_panel_siempre_devuelve_un_ancho_valido():
    assert calcular_ancho_panel(0) == 1
from ui.layout import PANEL_CONTENT_RATIO, calcular_geometria_contenido_panel


def test_v24_contenido_panel_usa_96_por_ciento():
    assert PANEL_CONTENT_RATIO == 0.96
    x, ancho = calcular_geometria_contenido_panel(400)
    assert (x, ancho) == (8, 384)


def test_v24_contenido_panel_centrado_en_ancho_impar():
    x, ancho = calcular_geometria_contenido_panel(301)
    assert ancho == 289
    assert x == 6
    assert x + ancho <= 301
