"""Inspección de implementación vigente sin depender de su archivo anterior."""
import inspect

def app_source():
    from ui import app_ui
    from ui.sidebar import SidebarMixin
    from ui.preferences import PreferencesMixin
    return '\n'.join(inspect.getsource(x) for x in (app_ui, SidebarMixin, PreferencesMixin))

def scene_source():
    from ui.scene3d import _VTKOffscreenSceneController
    from ui.scene3d_interaction import VTKInteractionMixin
    from ui import scene3d_backend, scene3d
    return '\n'.join(inspect.getsource(x) for x in (_VTKOffscreenSceneController, VTKInteractionMixin, scene3d_backend, scene3d))
