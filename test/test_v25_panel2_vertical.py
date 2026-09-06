from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")


def test_v25_panel2_tiene_fila_vertical_flexible():
    src = _source()
    start = src.index("    def setup_panel_2(self):")
    end = src.index("    def setup_panel_3(self):", start)
    bloque = src[start:end]
    assert "panel.grid_rowconfigure(2, weight=1)" in bloque
    assert 'selection_frame.grid(row=2, column=0, sticky="nsew"' in bloque
    assert 'process_frame.grid(row=3, column=0, sticky="sew"' in bloque


def test_v25_panel2_deja_de_apilar_todo_con_pack():
    src = _source()
    start = src.index("    def setup_panel_2(self):")
    end = src.index("    def setup_panel_3(self):", start)
    bloque = src[start:end]
    assert ".pack(" not in bloque
