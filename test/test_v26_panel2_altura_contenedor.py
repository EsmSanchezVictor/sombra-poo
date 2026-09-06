from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")


def test_v26_frame1_abarca_fila_del_carrusel_panel2():
    src = _source()
    assert 'self.frame1.grid(row=1, column=0, rowspan=4, sticky="nsew")' in src
    assert 'self.frame15.grid(row=4, column=1, columnspan=2, sticky="ew")' in src


def test_v26_panel2_no_usa_relleno_vertical_artificial_v25():
    src = _source()
    start = src.index("    def setup_panel_2(self):")
    end = src.index("    def setup_panel_3(self):", start)
    bloque = src[start:end]
    assert "panel.grid_rowconfigure(2, weight=1)" not in bloque
    assert "selection_frame.grid_rowconfigure(2, weight=1)" not in bloque
    assert 'process_frame.grid(row=3, column=0, sticky="sew"' not in bloque
    assert '.pack(' in bloque
