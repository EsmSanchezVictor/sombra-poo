from pathlib import Path

from ui.layout import (
    PANEL_CONTENT_RATIO,
    PANEL_HORIZONTAL_SCALE,
    calcular_ancho_sidebar_abierto,
    calcular_geometria_contenido_panel,
)


def _source():
    return (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")


def test_v24_reduccion_horizontal_real_cerca_30_por_ciento_en_1400():
    # v23 reservaba 364 px en 1400; v24 debe quedar alrededor del 70 %.
    ancho = calcular_ancho_sidebar_abierto(1400)
    assert ancho == 255
    assert abs(ancho / 364 - 0.70) < 0.02


def test_v24_reduccion_horizontal_real_cerca_30_por_ciento_en_1920():
    # v23 reservaba 499 px en 1920.
    ancho = calcular_ancho_sidebar_abierto(1920)
    assert 345 <= ancho <= 350
    assert abs(ancho / 499 - 0.70) < 0.02


def test_v24_margenes_internos_mas_ajustados():
    assert PANEL_CONTENT_RATIO == 0.96
    x, ancho = calcular_geometria_contenido_panel(240)
    assert ancho == 230
    assert x == 5


def test_v24_compactacion_es_horizontal_no_vertical():
    assert PANEL_HORIZONTAL_SCALE == 0.70
    src = _source()
    start = src.index("        def _compactar_widget_horizontal")
    end = src.index("        def _compactar_arbol_horizontal", start)
    bloque = src[start:end]
    assert 'widget.cget("width")' in bloque
    assert 'widget.cget("height")' not in bloque
    assert 'for clave in ("padx", "ipadx")' in bloque
    assert '"pady"' not in bloque
    assert 'widget.cget("font")' not in bloque


def test_v24_sticky_ew_tambien_se_achica_por_sidebar():
    src = _source()
    assert "grid_columnconfigure(0, weight=0, minsize=ancho)" in src
    assert "self._reservar_ancho_sidebar(self.panel_width)" in src
