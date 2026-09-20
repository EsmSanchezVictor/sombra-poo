from pathlib import Path
import inspect

import diseno
import ui.app_ui as app_ui


def test_frames_2_5_sin_borde_visible():
    source = Path('ui/app_ui.py').read_text(encoding='utf-8')
    for n in (2, 3, 4, 5):
        starts = []
        needle = f'self.frame{n} = tk.Frame('
        pos = source.find(needle)
        while pos >= 0:
            starts.append(pos)
            pos = source.find(needle, pos + 1)
        assert len(starts) >= 2
        block = source[starts[-1]:starts[-1] + 320]
        assert 'bd=0' in block
        assert 'relief="flat"' in block
        assert 'highlightthickness=0' in block


def test_ejecutar_abre_selector_con_animacion_por_defecto():
    source = Path('ui/app_ui.py').read_text(encoding='utf-8')
    assert '"Ejecutar", self.open_execution_dialog' in source
    assert 'mode = tk.StringVar(value="animation")' in source
    assert 'Animación diurna (sombra + temperatura)' in source
    assert 'values=(15, 30, 60)' in source


def test_reproduccion_usa_frames_precalculados():
    source = Path('ui/diurnal_animation.py').read_text(encoding='utf-8')
    assert 'class DiurnalAnimationPlayer' in source
    assert 'T_display' in source
    assert 'shadow' in source
    assert 'self.parent.after(delay, self._tick)' in source
    assert 'calculate' not in inspect.getsource(__import__('ui.diurnal_animation', fromlist=['DiurnalAnimationPlayer']).DiurnalAnimationPlayer._tick).lower()


def test_edicion_conserva_estado_para_animacion():
    source = inspect.getsource(diseno.actualizar_grafico)
    assert 'vars["_last_shadow"]' in source
    assert 'vars["_last_meta"]' in source


def test_indicador_solar_preservado_en_2d_y_3d():
    solar = Path('ui/solar_indicator.py').read_text(encoding='utf-8')
    scene = Path('ui/scene3d.py').read_text(encoding='utf-8')
    assert 'add_solar_indicator_2d' in solar
    assert 'sun_actor.SetUseBounds(False)' in scene
    assert 'guide_actor.SetUseBounds(False)' in scene
