from pathlib import Path

from ui.layout import calcular_ancho_sidebar_abierto


def _source():
    return (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")


def test_v22_sidebar_abierto_conserva_ancho_minimo_operativo_tras_v24():
    # v24 lo reduce horizontalmente, pero no puede colapsar.
    assert calcular_ancho_sidebar_abierto(1366) >= 250


def test_v22_sidebar_no_invade_mas_de_45_por_ciento_en_ventana_angosta():
    width = calcular_ancho_sidebar_abierto(800)
    assert width <= round(800 * 0.45)


def test_v22_sidebar_limita_ancho_en_pantalla_grande_tras_v24():
    assert calcular_ancho_sidebar_abierto(1920) <= 365


def test_v22_reserva_columna_cero_con_minsize():
    src = _source()
    start = src.index("    def _reservar_ancho_sidebar")
    end = src.index("    def _recalcular_ancho_sidebar_abierto", start)
    bloque = src[start:end]
    assert "grid_columnconfigure(0, weight=0, minsize=ancho)" in bloque
    assert "self.frame1.configure(width=ancho)" in bloque


def test_v22_frame1_no_delega_su_ancho_a_hijos():
    src = _source()
    assert "self.frame1.grid_propagate(False)" in src
