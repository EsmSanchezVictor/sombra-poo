from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "ui" / "scene3d.py").read_text(encoding="utf-8")


def test_windows_inicia_vtk_sin_msaa():
    assert 'SetMultiSamples(0 if self._platform_is_windows else 8)' in SRC


def test_primer_render_vtk_se_difiere_hasta_idle():
    assert 'after_idle(self._initial_render)' in SRC


def test_fallback_muestra_diagnostico_real():
    assert 'vtk_installation_info()' in SRC
    assert 'type(vtk_error).__name__' in SRC
