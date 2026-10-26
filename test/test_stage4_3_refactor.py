"""Contratos de los componentes extraídos: IO real y ciclo de datos VTK sin OpenGL."""
from types import SimpleNamespace
import numpy as np
import pytest


def test_model_facade_roundtrips_scene_and_parameters_without_a_window(tmp_path, monkeypatch):
    import modelo_con_excel as model
    from ui import model_excel
    from core.surface_model import Arbol, Estructura
    messages = []
    monkeypatch.setattr(model_excel.messagebox, 'showinfo', lambda *args, **kwargs: messages.append(args))
    monkeypatch.setattr(model_excel.messagebox, 'showerror', lambda *args, **kwargs: pytest.fail(str(args)))
    tree = Arbol(2., 3., 6., .8, 2., forma_copa='columnar')
    tree.especie = 'Lapacho'
    wall = Estructura('Pared', 1., 1., 4., 1., 2., .9, 'Ladrillo')
    variables = dict(arboles=[tree], estructuras=[wall], hora=14., dia=100, _year=2024,
        lat=-31.7, lon=-60.5, T_amb_base=300., T_min=290., T_max=310., I_sol_base=700.,
        humedad=50., viento='moderado', _modo_modelo='simple')
    target = tmp_path/'escena.xlsx'
    assert model.guardar_excel(variables, str(target), notify=False) == str(target)
    restored = {'hora': 0.}
    assert model.cargar_excel(restored, str(target)) == str(target)
    assert restored['_update_required'] is True
    assert len(restored['arboles']) == len(restored['estructuras']) == 1
    assert restored['arboles'][0].forma_copa == tree.forma_copa
    assert restored['arboles'][0].especie == tree.especie
    assert restored['estructuras'][0].altura == wall.altura
    assert restored['hora'] == variables['hora']
    assert len(messages) == 1


def test_vtk_animation_changes_data_and_reuses_overlay_without_moving_camera():
    vtk = pytest.importorskip('vtk')
    from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
    from ui.scene3d import _VTKOffscreenSceneController
    from core.scene3d_data import scene_data_from_vars
    x, y = np.meshgrid(np.arange(3.), np.arange(2.))
    data = scene_data_from_vars(dict(X=x, Y=y, T=np.full_like(x, 300.)), 'Prueba')
    controller = _VTKOffscreenSceneController.__new__(_VTKOffscreenSceneController)
    controller._closed = False
    controller._data = data
    controller._grid = vtk.vtkStructuredGrid()
    controller._grid.SetDimensions(3, 2, 1)
    points = vtk.vtkPoints()
    points.SetData(numpy_to_vtk(np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)]), deep=True))
    controller._grid.SetPoints(points)
    controller._renderer = vtk.vtkRenderer()
    controller._renderer.GetActiveCamera().SetPosition(11., 12., 13.)
    controller._contours = None
    controller._shadow_grid = controller._shadow_actor = controller._shadow_mapper = controller._shadow_lut = None
    controller._scene_center = (1., .5, .35)
    controller._scene_span = 3.
    controller._key_light = vtk.vtkLight()
    controller._sun_source = vtk.vtkSphereSource()
    controller._guide_source = vtk.vtkLineSource()
    labels = []
    controller._solar_status_label = SimpleNamespace(configure=lambda **kwargs: labels.append(kwargs))
    renders = []
    controller._render_to_tk = lambda **kwargs: renders.append(kwargs)
    frame = dict(T_display=np.full_like(x, 305.), shadow=np.full_like(x, .25),
                 solar_altitude_deg=50., solar_azimuth_deg=190.)
    before = controller._renderer.GetActiveCamera().GetPosition()
    controller.update_animation_frame(frame)
    overlay = controller._shadow_actor
    controller.update_animation_frame(dict(frame, T_display=np.full_like(x, 306.)))
    assert controller._renderer.GetActiveCamera().GetPosition() == before
    assert controller._shadow_actor is overlay
    assert controller._renderer.GetActors().GetNumberOfItems() == 1
    np.testing.assert_array_equal(vtk_to_numpy(controller._grid.GetPointData().GetScalars()), np.full(x.size, 306.))
    np.testing.assert_array_equal(vtk_to_numpy(controller._shadow_grid.GetPointData().GetScalars()), np.full(x.size, .75))
    assert len(renders) == len(labels) == 2
    with pytest.raises(ValueError, match='resolución'):
        controller.update_animation_frame(dict(frame, T_display=np.zeros((1, 1))))


def test_scene_facade_disposes_old_controller_before_successful_render(monkeypatch):
    from ui import scene3d
    events = []
    old = SimpleNamespace(close=lambda: events.append('close'))
    widget = SimpleNamespace(destroy=lambda: events.append('destroy'))
    host = SimpleNamespace(_sombra_scene3d_controller=old, winfo_children=lambda: [widget])
    created = []
    def make(parent, data):
        assert events == ['close', 'destroy']
        controller = object()
        created.append(controller)
        return controller
    monkeypatch.setattr(scene3d, 'vtk_backend_available', lambda: True)
    monkeypatch.setattr(scene3d, '_VTKOffscreenSceneController', make)
    x, y = np.meshgrid([0., 1.], [0., 1.])
    assert scene3d.render_scene_3d(dict(X=x, Y=y, T=x+300.), host, title='Control') == 'VTK'
    assert host._sombra_scene3d_controller is created[0]


def test_scene_facade_keeps_real_error_when_constructor_fails(monkeypatch):
    from ui import scene3d
    error = RuntimeError('No hay contexto OpenGL')
    host = SimpleNamespace(winfo_children=lambda: [])
    def fail(*args):
        raise error
    received = []
    monkeypatch.setattr(scene3d, 'vtk_backend_available', lambda: True)
    monkeypatch.setattr(scene3d, '_VTKOffscreenSceneController', fail)
    monkeypatch.setattr(scene3d, '_render_matplotlib_fallback', lambda *args, **kwargs: received.append(kwargs['vtk_error']))
    x, y = np.meshgrid([0., 1.], [0., 1.])
    assert scene3d.render_scene_3d(dict(X=x, Y=y, T=x+300.), host, title='Control') == 'Matplotlib (fallback)'
    assert received == [error]


def test_desktop_check_cannot_credit_windows_when_running_elsewhere(monkeypatch):
    from services import desktop_check
    monkeypatch.setattr(desktop_check.platform, 'system', lambda: 'Linux')
    result = desktop_check.run_desktop_check(require_windows=True)
    assert result['status'] == 'failed'
    assert result['windows_native_execution'] is False
    assert result['human_visual_review'] is False
    assert result['full_app_workflow_tested'] is False


def test_desktop_parent_reports_native_process_failure(tmp_path, monkeypatch):
    import json
    from tools import check_desktop
    output = tmp_path/'desktop.json'
    monkeypatch.setattr(check_desktop.sys, 'argv', ['check_desktop', '--report', str(output), '--vtk'])
    monkeypatch.setattr(check_desktop.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=-11))
    assert check_desktop.main() == 1
    result = json.loads(output.read_text())
    assert result['status'] == 'failed' and result['human_visual_review'] is False
    assert '-11' in result['checks'][0]['error']
