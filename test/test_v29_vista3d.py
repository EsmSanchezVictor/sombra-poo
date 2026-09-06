import inspect
from pathlib import Path
import numpy as np

import diseño
import modelo_con_excel as modelo
from ui.scene3d import scene_data_from_vars, vtk_backend_available


class _AppTemperature:
    def convert_temperature_for_display(self, value):
        return np.asarray(value) - 273.15

    def get_temperature_unit_symbol(self):
        return "°C"


def test_scene3d_reuses_existing_results_without_mutating_t():
    X, Y = np.meshgrid(np.linspace(0, 2, 4), np.linspace(0, 1, 3))
    T = np.linspace(293.15, 303.15, X.size, dtype=np.float32).reshape(X.shape)
    before = T.copy()
    vars_dict = {
        "X": X,
        "Y": Y,
        "T": T,
        "_app_instance": _AppTemperature(),
        "arboles": [],
        "estructuras": [],
        "_render_solar_altitude_deg": 40.0,
        "_render_solar_azimuth_deg": 310.0,
    }

    scene = scene_data_from_vars(vars_dict, "prueba")

    np.testing.assert_array_equal(T, before)
    np.testing.assert_allclose(scene.temperature, before - 273.15, rtol=0, atol=2e-5)
    assert scene.temperature_unit == "°C"
    assert scene.solar_altitude_deg == 40.0
    assert scene.solar_azimuth_deg == 310.0


def test_design_and_model_3d_no_longer_open_toplevel_windows():
    assert "tk.Toplevel(" not in inspect.getsource(diseño.generar_3d)
    assert "tk.Toplevel(" not in inspect.getsource(modelo.generar_3d)
    assert "render_scene_3d" in inspect.getsource(diseño.generar_3d)
    assert "render_scene_3d" in inspect.getsource(modelo.generar_3d)


def test_shared_container_has_2d_and_3d_notebook_tabs():
    source = Path("ui/app_ui.py").read_text(encoding="utf-8")
    assert 'notebook.add(view2d, text="Vista 2D")' in source
    assert 'notebook.add(view3d, text="Vista 3D")' in source
    assert "mostrar_vista_3d_diseno" in source
    assert "mostrar_vista_3d_modelo" in source


def test_vtk_backend_probe_is_boolean():
    assert isinstance(vtk_backend_available(), bool)
