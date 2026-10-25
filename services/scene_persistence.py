"""Serialización común de escenas; no toca widgets, globals ni resultados."""
import os
from core.effective_scenario import value, effective_model
from core.excel_scene import save_scene_excel


def write_scene(kind, path, app, variables=None):
    if kind not in ('edit','model'):
        raise ValueError('Tipo de escena no soportado')
    variables = variables if variables is not None else (app.vars if kind == 'edit' else app.vars_modelo)
    mode_attr = 'modo_edicion' if kind == 'edit' else 'modo_modelo'
    mode = value(getattr(app,mode_attr,variables.get('_modo_modelo','advanced')))
    mode = str(mode or 'advanced')
    selected = value(getattr(app,'surface_model_mode',variables.get('_surface_model_mode','standard')))
    settings = getattr(app,'settings',{})
    captured = variables.get('_effective_scenario') or {}
    extra = {
        'modo_ui_origen':mode,'surface_model_mode':effective_model(mode,selected,surface=True),
        'ground_vegetation_fraction':settings.get('ground_vegetation_fraction',.5),
        'vegetation_water_availability':settings.get('vegetation_water_availability',.75),
        'canopy_water_availability':settings.get('canopy_water_availability',.75),
        'radiation_source_mode':value(getattr(app,'radiation_source_mode','clear_sky')) if mode == 'advanced' else 'clear_sky',
        'clear_sky_use_pvlib':bool(value(getattr(app,'use_pvlib_engine',False))) if mode == 'advanced' else False,
        'meteorology_csv':os.path.basename(getattr(app,'meteorology_series_path','') or '') if mode == 'advanced' else '',
        'radiation_source_label':captured.get('source_label',''),
        'radiation_quality':captured.get('quality',''),
        'ghi_wm2':captured.get('ghi',''),'dni_wm2':captured.get('dni',''),'dhi_wm2':captured.get('dhi',''),
    }
    return save_scene_excel(path,variables.get('arboles',[]),variables.get('estructuras',[]),variables,
                            calculation_mode=mode,origin='edicion' if kind == 'edit' else 'modelo',app=app,extra_parameters=extra)
