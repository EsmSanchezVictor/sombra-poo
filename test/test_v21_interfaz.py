from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")


def test_carrusel_v21_no_renderiza_nombre_bajo_miniatura():
    src = _source()
    start = src.index("    def _carrusel_actualizar")
    end = src.index("    def _carrusel_marcar", start)
    bloque = src[start:end]
    assert 'text=etiqueta' not in bloque
    assert 'etiqueta +=' not in bloque
    assert 'lbl_img.pack(padx=2, pady=2)' in bloque


def test_paneles_v21_reservan_columna_exclusiva_para_scrollbar():
    src = _source()
    start = src.index("    def _crear_panel_desplazable")
    end = src.index("    def toggle_panel", start)
    bloque = src[start:end]
    assert 'canvas.grid(row=0, column=0, sticky="nsew")' in bloque
    assert 'scrollbar.grid(row=0, column=1, sticky="ns")' in bloque
    assert 'calcular_geometria_contenido_panel' in bloque
    assert 'PANEL_CONTENT_RATIO' in bloque
