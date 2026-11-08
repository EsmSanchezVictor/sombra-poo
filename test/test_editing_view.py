"""Editar la escena conserva las pestañas y descarta la vista 3D anterior."""
from types import SimpleNamespace
from unittest.mock import Mock

import diseno
from ui import app_ui


def test_edicion_redraws_inside_current_2d_tab_and_invalidates_previous_3d(monkeypatch):
    view2d, view3d, notebook = Mock(), Mock(), Mock()
    app = SimpleNamespace(vars={}, frame7=object())
    app._get_scene_view_frames = Mock(return_value=(view2d, view3d, notebook))
    app.render_grafico_en_frame = Mock(return_value=(object(), object(), object()))
    app.actualizar_grafico_diseno = lambda: app_ui.SombraApp.actualizar_grafico_diseno(app)
    empty = Mock()
    monkeypatch.setattr(app_ui, "show_empty_3d_view", empty)
    controller = view3d._sombra_scene3d_controller = Mock()
    old_image = Mock()
    view3d.winfo_children.return_value = [old_image]

    diseno._redibujar_escena(app.vars, app)

    app._get_scene_view_frames.assert_called_once_with("diseno")
    assert app.render_grafico_en_frame.call_args.args[0] is view2d
    controller.close.assert_called_once_with()
    old_image.destroy.assert_called_once_with()
    empty.assert_called_once_with(view3d)
    notebook.select.assert_called_once_with(view2d)
    notebook.destroy.assert_not_called()
