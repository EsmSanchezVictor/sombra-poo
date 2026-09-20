from pathlib import Path
import inspect

from ui.diurnal_animation import Diurnal3DAnimationPlayer
from ui.scene3d import _VTKOffscreenSceneController


def test_animacion_3d_tiene_un_solo_viewport_y_no_reencuadra_por_frame():
    src = inspect.getsource(_VTKOffscreenSceneController.update_animation_frame)
    assert 'self._renderer.ResetCamera()' not in src
    assert 'SetScalars' in src
    assert '_ensure_shadow_overlay' in src
    assert '_sun_source.SetCenter' in src


def test_reproductor_3d_persistente_existe_y_se_abre_por_defecto():
    src = Path('ui/app_ui.py').read_text(encoding='utf-8')
    assert 'Diurnal3DAnimationPlayer' in src
    assert 'notebook.select(view3d)' in src
    assert 'player3d.play()' in src
    tick = inspect.getsource(Diurnal3DAnimationPlayer._tick)
    assert 'render_frame' in tick
    assert 'calculate' not in tick.lower()


def test_2d_no_recrea_colorbars_en_cada_frame():
    src = Path('ui/diurnal_animation.py').read_text(encoding='utf-8')
    # Los ejes dedicados de colorbar se construyen una vez en __init__.
    assert 'self._shadow_cax = self.figure.add_subplot(grid[1, 0])' in src
    assert 'self._temp_cax = self.figure.add_subplot(grid[1, 1])' in src
    render = inspect.getsource(__import__('ui.diurnal_animation', fromlist=['DiurnalAnimationPlayer']).DiurnalAnimationPlayer.render_frame)
    assert '.colorbar(' not in render
    assert 'tight_layout' not in render
