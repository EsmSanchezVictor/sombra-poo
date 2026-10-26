from test.source_helpers import app_source, scene_source
from pathlib import Path


def test_2d_edicion_y_modelo_muestran_indicador_solar():
    diseno = Path('diseno.py').read_text(encoding='utf-8')
    modelo = Path('modelo_con_excel.py').read_text(encoding='utf-8')
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in diseno
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in modelo
    assert 'add_solar_indicator_2d(' in diseno
    assert 'add_solar_indicator_2d(' in modelo
    assert 'vars.get("_render_solar_azimuth_deg")' in diseno
    assert 'vars.get("_render_solar_altitude_deg")' in modelo


def test_scene3d_representa_sol_en_vtk_y_fallback():
    scene = scene_source()
    assert 'vtkLineSource' in scene
    assert 'vtkTubeFilter' in scene
    assert 'solar_summary = ""' in scene
    assert 'sun_distance = span * 0.45' in scene
    assert 'guide_tube.SetRadius(max(0.03, span * 0.0035))' in scene
    fallback = Path('ui/scene3d_fallback.py').read_text(encoding='utf-8')
    assert 'sun_distance = span * 0.45' in fallback
    assert 'ax.scatter([sun_x], [sun_y], [sun_z], s=220' in fallback


def test_app_ui_preserva_metadatos_solares_para_overlay_2d():
    app_ui = app_source()
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in app_ui
    photo = Path('ui/photo_analysis.py').read_text(encoding='utf-8')
    assert 'resultado_mapa["Solar_azimuth"] = solar_data.get("azimuth")' in photo
    assert 'resultado_mapa.get("Solar_azimuth")' in photo
    assert 'resultado_mapa.get("Solar_altitude")' in photo
