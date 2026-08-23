from ui.layout import calcular_ancho_panel


def test_panel_usa_solo_una_fraccion_en_ventana_angosta():
    assert calcular_ancho_panel(600) == 240


def test_panel_respeta_el_ancho_preferido_en_ventana_grande():
    assert calcular_ancho_panel(1920) == 360


def test_panel_siempre_devuelve_un_ancho_valido():
    assert calcular_ancho_panel(0) == 1