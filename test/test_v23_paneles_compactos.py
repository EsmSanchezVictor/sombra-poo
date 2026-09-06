"""Pruebas de compatibilidad del hito v23, actualizado por v24.

v24 reemplaza la compactación volumétrica de v23 por compactación horizontal.
Se conservan aquí sólo invariantes que siguen siendo válidas.
"""
from ui.layout import PANEL_HORIZONTAL_SCALE, calcular_ancho_sidebar_abierto


def test_v23_escala_30_por_ciento_se_conserva_en_eje_horizontal():
    assert PANEL_HORIZONTAL_SCALE == 0.70


def test_v23_sidebar_sigue_acotado_y_util_tras_v24():
    ancho = calcular_ancho_sidebar_abierto(1400)
    assert 240 <= ancho <= 300
