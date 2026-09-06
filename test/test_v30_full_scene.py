from pathlib import Path


def test_diseno_y_modelo_ocupan_bloque_central_completo():
    source = Path("ui/app_ui.py").read_text(encoding="utf-8")
    assert 'self.frame7.grid(row=1, column=1, rowspan=2, columnspan=2, sticky="nsew")' in source
    assert 'self.frame11.grid(row=1, column=1, rowspan=2, columnspan=2, sticky="nsew")' in source
    assert '[self.frame7],' in source
    assert '[self.frame11],' in source


def test_notebook_2d_3d_sigue_embebido_y_expandible():
    source = Path("ui/app_ui.py").read_text(encoding="utf-8")
    assert 'notebook.pack(fill="both", expand=True)' in source
    assert 'notebook.add(view2d, text="Vista 2D")' in source
    assert 'notebook.add(view3d, text="Vista 3D")' in source


def test_vtk_es_dependencia_principal_y_render_mejorado():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    scene = Path("ui/scene3d.py").read_text(encoding="utf-8")
    assert "vtk>=9.3,<10" in requirements
    assert "QUALITY_RENDER_SCALE = 1.35" in scene
    assert "MAX_RENDER_PIXELS = 2_600_000" in scene
    assert "lobe_specs = (" in scene
    assert "high_quality=False" in scene
