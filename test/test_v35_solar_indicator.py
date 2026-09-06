from pathlib import Path


def test_2d_edicion_y_modelo_muestran_indicador_solar():
    diseno = Path('diseño.py').read_text(encoding='utf-8')
    modelo = Path('modelo_con_excel.py').read_text(encoding='utf-8')
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in diseno
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in modelo
    assert 'add_solar_indicator_2d(' in diseno
    assert 'add_solar_indicator_2d(' in modelo
    assert 'vars.get("_render_solar_azimuth_deg")' in diseno
    assert 'vars.get("_render_solar_altitude_deg")' in modelo


def test_scene3d_representa_sol_en_vtk_y_fallback():
    scene = Path('ui/scene3d.py').read_text(encoding='utf-8')
    assert 'vtkLineSource' in scene
    assert 'vtkTubeFilter' in scene
    assert 'solar_summary = ""' in scene
    assert 'sun_distance = span * 2.15' in scene
    assert 'guide_tube.SetRadius(max(0.03, span * 0.0035))' in scene
    assert 'ax.scatter([sun_x], [sun_y], [sun_z], s=220' in scene


def test_app_ui_preserva_metadatos_solares_para_overlay_2d():
    app_ui = Path('ui/app_ui.py').read_text(encoding='utf-8')
    assert 'from ui.solar_indicator import add_solar_indicator_2d' in app_ui
    assert 'resultado_mapa["Solar_azimuth"] = solar_data.get("azimuth")' in app_ui
    assert 'resultado_mapa.get("Solar_azimuth")' in app_ui
    assert 'resultado_mapa.get("Solar_altitude")' in app_ui
