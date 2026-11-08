"""El escritorio solo se activa cuando el gestor confirma el proyecto."""
from types import SimpleNamespace
from unittest.mock import Mock

from ui.app_ui import SombraApp
from ui.menu_bar import MenuBar


class Surface:
    def __init__(self):
        self.visible = True

    def grid(self, **kwargs):
        self.visible = True

    def grid_remove(self):
        self.visible = False


def workspace():
    app = object.__new__(SombraApp)
    app.root = Mock()
    for index in range(16):
        setattr(app, f"frame{index}", Surface())
    app._workspace_frames = tuple(getattr(app, f"frame{i}") for i in range(16))
    app.startup_frame = Surface()
    app._welcome_primary = Mock()
    app._panel_anim_token = 1
    app._open_after_close = {1: 1}
    app._close_callbacks = {1: Mock()}
    app.panel_outer_frames = [Mock() for _ in range(4)]
    app.buttons = [Mock() for _ in range(4)]
    app.frame1.cget = Mock(return_value="#fff")
    app.palette = {"selected": "#def"}
    app.menu_bar = Mock()
    app.project_manager = SimpleNamespace(current_project=None)
    app._get_analysis_store = Mock()
    app.update_status_saved_time = Mock()
    app._register_project_session = Mock()
    app.current_location = None
    app._suspend_autosave_tracking = False
    app._reservar_ancho_sidebar = Mock()
    app.sidebar_closed_width = 48
    app._recalcular_ancho_sidebar_abierto = Mock()
    app.panel_width = 220
    app.animate_panel_open = Mock()
    app._get_scene_view_frames = Mock()
    return app


def visible_frames(app):
    return [i for i, frame in enumerate(app._workspace_frames) if frame.visible]


def test_welcome_hides_entire_workspace_even_when_restore_requests_frames():
    app = workspace()
    app.show_startup_screen()
    app.show_panel2_frames()
    app.show_diseno_frames()
    app.show_modelo_frames()
    app.open_panel(2)
    assert app.startup_frame.visible
    assert not visible_frames(app)
    assert not app._close_callbacks and not app._open_after_close
    app.menu_bar.set_project_enabled.assert_called_once_with(False)

    # Cargar datos no es confirmación: un fallo posterior deja la bienvenida.
    app.project_manager.current_project = object()
    app._suspend_autosave_tracking = True
    app.open_panel(3)
    assert app._pending_project_panel == 3
    assert app.active_panel is None
    assert not visible_frames(app)
    app.animate_panel_open.assert_not_called()
    app._get_scene_view_frames.assert_not_called()


def test_successful_open_activates_only_the_saved_view():
    app = workspace()
    app.show_startup_screen()
    app.project_manager.current_project = object()
    app._suspend_autosave_tracking = True
    app.open_panel(2)
    app._suspend_autosave_tracking = False
    app.on_project_loaded("opened")
    assert not app.startup_frame.visible
    assert visible_frames(app) == [0, 1, 6, 7]
    app._get_scene_view_frames.assert_called_once_with("diseno")
    assert app.active_panel == 2
    assert app._pending_project_panel is None
    app.animate_panel_open.assert_called_once_with(2, 0, app._panel_anim_token)
    app.menu_bar.set_project_enabled.assert_called_with(True)


def test_new_project_shows_base_view_with_sidebar_closed():
    app = workspace()
    app.show_startup_screen()
    app.project_manager.current_project = object()
    app.on_project_loaded("created")
    assert not app.startup_frame.visible
    assert visible_frames(app) == [0, 1, 2, 3, 4, 5, 6, 15]
    assert app.active_panel is None
    app.animate_panel_open.assert_not_called()
    app._reservar_ancho_sidebar.assert_called_once_with(48)


def test_project_shortcuts_do_not_run_from_welcome():
    bar = MenuBar(Mock())
    project_menu = Mock()
    bar._project_entries = ((project_menu, ("Modelo",)),)
    run = Mock()
    new = Mock()
    run_shortcut = bar._shortcut(run, requires_project=True)
    new_shortcut = bar._shortcut(new)
    assert run_shortcut(None) == new_shortcut(None) == "break"
    run.assert_not_called()
    new.assert_called_once_with()

    bar.set_project_enabled(True)
    run_shortcut(None)
    run.assert_called_once_with()
    project_menu.entryconfigure.assert_called_once_with("Modelo", state="normal")
