"""Regresión de configuración efectiva y dominios físicos; sin ventanas Tk."""
from dataclasses import replace
from datetime import date, datetime
from types import SimpleNamespace, MethodType
import json
import numpy as np
import pytest
from core.effective_scenario import EffectiveScenarioConfig, scenario_date, effective_model
from core.climate_profile import viento_categoria_a_ms, descomponer_radiacion, velocidad_viento
from core.vegetation import wind_speed_mps
from core.solar_math import timezone_offset_hours
from core.surface_energy import solve_surface_energy_balance, SurfaceEnergyConfig, surface_diagnostics_summary
from core import thermal_comfort as tc
from core.scenario import mapa_estres, escenario_horario, resumen_escenario
from services.solar_engine import SolarEngine
from services.meteorology_service import MeteorologyService
from services.scenario_service import prepare_surface_scenario
from services.analysis_service import curva_sensibilidad, exportar_tabla_excel
from core.excel_scene import save_scene_excel, load_scene_excel, apply_parameters_to_vars
from modelo_con_excel import calcular_coeficiente_conveccion
from shadow_temp import Temperatura
from ui.app_ui import SombraApp

class Var:
    def __init__(self, value): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


def mapping():
    return {k: Var(v) for k, v in dict(hora=12.5, dia=196, lat=-31.4, lon=-64.2,
        T_amb_base=300., T_min=290., T_max=308., I_sol_base=650., humedad=60., viento='moderado',
        timezone='America/Argentina/Buenos_Aires', nubosidad='Despejado', debug=False).items()} | dict(_year=2024, _date_iso='2024-07-14', arboles=[], estructuras=[], _update_required=True)


def app(mode='simple', radiation='manual_scenario'):
    obj = SombraApp.__new__(SombraApp)
    obj.modo_temperatura = Var(mode)
    obj.tmrt_model_mode = Var('advanced')
    obj.modo_modelo = Var(mode)
    obj.modo_edicion = Var(mode)
    obj.surface_model_mode = Var('advanced_vegetation')
    obj.radiation_source_mode = Var(radiation)
    obj.use_pvlib_engine = Var(True)
    obj.manual_ghi, obj.manual_dni, obj.manual_dhi = Var('700'), Var(''), Var('')
    obj.solar_engine = SolarEngine()
    obj.meteorology_service = MeteorologyService()
    obj.settings = {}
    obj.simple_rh = Var(65)
    obj.k_factor = .04
    obj.vars_modelo = mapping()
    obj.vars = mapping()
    obj.vars_modelo['_app_instance'] = obj
    obj.vars['_app_instance'] = obj
    obj._timezone_actual = lambda: 'America/Argentina/Buenos_Aires'
    obj._construir_instante = lambda fecha, hora: datetime.combine(fecha, datetime.min.time()).replace(hour=int(hora), minute=int((hora%1)*60))
    obj.get_temperature_unit_symbol = lambda: '°C'
    obj.get_distance_unit = lambda: 'm'
    obj.convert_temperature_for_display = lambda x: x - 273.15
    return obj


def resolved(input_mode='advanced', selected_model='advanced', **overrides):
    solar = SolarEngine().get_solar_data(-31.4, -64.2, datetime(2024, 1, 15, 13))
    solar.update(source_mode='manual_scenario', source_label='Escenario manual', quality='prescribed_scenario', source_detail='manual')
    solar.update(overrides)
    return EffectiveScenarioConfig.from_resolved(input_mode=input_mode, selected_model=selected_model,
        fecha=date(2024,1,15), hour=13, lat=-31.4, lon=-64.2, timezone='America/Argentina/Buenos_Aires',
        ta=30, rh=60, wind='3,2', k_factor=.04, solar=solar)

@pytest.mark.parametrize('value,speed',[('nulo',.5),('moderado',4),('fuerte',10),('3.2',3.2),('3,2',3.2),(0,0),('desconocida',4)])
def test_one_wind_parser(value,speed):
    assert viento_categoria_a_ms(value) == wind_speed_mps(value) == speed
    assert calcular_coeficiente_conveccion(value) == pytest.approx(5.7+3.8*speed)

@pytest.mark.parametrize('value',['nan', 'inf', '-1', float('nan'), float('inf'), -2])
def test_invalid_numeric_wind_rejected(value):
    for function in (viento_categoria_a_ms, wind_speed_mps, calcular_coeficiente_conveccion):
        with pytest.raises(ValueError): function(value)

@pytest.mark.parametrize('year,day,expected',[(2024,60,'2024-02-29'),(2024,366,'2024-12-31'),(2025,365,'2025-12-31')])
def test_scenario_date_visible_day_wins_over_stale_iso(year,day,expected):
    assert scenario_date({'_year':year,'_date_iso':f'{year}-01-01','dia':Var(day)}).isoformat() == expected

@pytest.mark.parametrize('year,day',[(2025,366),(2024,367),(2024,0)])
def test_invalid_day_does_not_roll_to_another_year(year,day):
    with pytest.raises(ValueError): scenario_date({'_year':year,'dia':day})


def test_actual_year_changes_dst_offset():
    # 10 March is before DST in 2023 and after transition in 2024 at noon.
    a=date(2023,3,10); b=date(2024,3,10)
    assert timezone_offset_hours('America/New_York',a.timetuple().tm_yday,12,year=a.year)==-5
    assert timezone_offset_hours('America/New_York',b.timetuple().tm_yday,12,year=b.year)==-4


def test_scene_excel_keeps_year_and_leap_date(tmp_path):
    source=mapping(); source['dia'].set(60)
    file=tmp_path/'leap.xlsx'; save_scene_excel(file,[],[],source)
    workbook=load_scene_excel(file)
    target=mapping(); target.pop('_year'); target.pop('_date_iso')
    apply_parameters_to_vars(target,workbook.parametros)
    assert scenario_date(target)==date(2024,2,29)


@pytest.mark.parametrize('radiation',['manual_measured','manual_scenario','observed_series','clear_sky'])
def test_simple_hidden_advanced_controls_cannot_affect_temperature(radiation):
    obj=app('simple',radiation)
    obj.manual_ghi.set('invalid hidden text'); obj.manual_dni.set('invalid'); obj.manual_dhi.set('invalid')
    first,_=obj._resolve_temperature_scenario(30,13,date(2024,1,15),-31.4,-64.2)
    obj.tmrt_model_mode.set('standard'); obj.use_pvlib_engine.set(False)
    second,_=obj._resolve_temperature_scenario(30,13,date(2024,1,15),-31.4,-64.2)
    assert first.to_dict()==second.to_dict()
    assert first.tmrt_model=='standard' and first.source_mode=='clear_sky' and first.source_detail=='fallback'
    assert first.rh_pct==65

@pytest.mark.parametrize('selected',['standard','advanced'])
def test_point_map_sensitivity_agree_on_same_effective_inputs(tmp_path, selected):
    config=resolved(selected_model=selected, ghi=600, dni=650, dhi=100)
    calc=config.calculator(); kw=config.calculation_kwargs()
    coverage=np.array([[0,50,100]],dtype=np.float32)
    point=calc.calculate_tmrt(config.air_temp_c,50,**kw)
    grid=calc.calculate_tmrt_map(config.air_temp_c,coverage,**kw)
    _,ps,ys=curva_sensibilidad(Temperatura(0,0),-5,date(2026,1,1),0,str(tmp_path/'curve.png'),scenario_config=config)
    assert point['Tmrt_sombra']==pytest.approx(grid['Tmrt_map'][0,1], abs=.0051)
    assert point['Tmrt_sombra']==pytest.approx(ys[np.flatnonzero(ps==50)[0]])
    assert config.calculator().model_mode==selected
    assert json.loads(json.dumps(config.to_dict()))['date_iso']=='2024-01-15'


def test_observed_weather_and_fallback_sources_recorded():
    config=resolved(source_mode='observed_series',ta_c=33,rh_pct=0,wind_m_s=2.7)
    assert (config.air_temp_c,config.rh_pct,config.wind_ref_10m_m_s)==(33,0,2.7)
    assert dict(config.weather_sources)['rh_pct']=='observed_series'
    assert resolved(source_mode='observed_series',ta_c=33).rh_pct==60
    assert dict(resolved(source_mode='observed_series',ta_c=33).weather_sources)['rh_pct']=='user_input'
    assert config.wind_2m_m_s==pytest.approx(velocidad_viento(2,2.7))


def test_scene_observed_values_do_not_mutate_controls_or_leak_back_to_simple():
    obj=app('advanced','observed_series')
    data=SolarEngine().get_solar_data(-31.4,-64.2,datetime(2024,7,14,12,30))
    data.update(source_mode='observed_series',source_label='Serie',quality='measured',ta_c=34,rh_pct=0,wind_m_s=1.2)
    obj._obtener_datos_solares=lambda *a,**k:data
    scenario=prepare_surface_scenario(obj.vars_modelo)
    assert scenario['air_temp_k']==307.15 and scenario['rh_pct']==0
    assert obj.vars_modelo['humedad'].get()==60 and obj.vars_modelo['viento'].get()=='moderado'
    obj.modo_modelo.set('simple')
    simple=prepare_surface_scenario(obj.vars_modelo)
    assert simple['surface_model']=='standard' and simple['wind_ref_10m_m_s']==4
    assert simple['air_temp_k']==300 and obj.vars_modelo['_radiation_override_ghi'] is None


def test_solar_aware_instant_matches_local_instant():
    from zoneinfo import ZoneInfo
    engine=SolarEngine(tz='America/New_York')
    utc=datetime(2024,7,1,16,tzinfo=ZoneInfo('UTC'))
    assert engine.get_solar_position(40.7,-74,utc)==pytest.approx(engine.get_solar_position(40.7,-74,datetime(2024,7,1,12)))

@pytest.mark.parametrize('elev',[0,-5,.01,.4,10,60,90])
def test_radiation_fallback_shared_and_energy_conserved(elev):
    rad=SolarEngine.fallback_radiation(elev)
    assert rad['ghi']==Temperatura(-31.4,-64.2).clear_sky_radiation(elev)
    assert rad['ghi']==pytest.approx(rad['dni']*max(0,np.sin(np.radians(elev)))+rad['dhi'])
    parts=descomponer_radiacion(rad['ghi'],elev,'Parcial')
    assert rad['ghi']==pytest.approx(parts['dni_normal']*max(0,np.sin(np.radians(elev)))+parts['dhi'])

@pytest.mark.parametrize('ta,tr,v,rh,valid',[(-50,-80,.5,0,True),(50,120,17,100,True),(-51,0,1,50,False),(51,60,1,50,False),(30,-1,1,50,False),(30,101,1,50,False),(30,40,.49,50,False),(30,40,17.1,50,False),(30,40,1,float('nan'),False)])
def test_utci_explicit_domain(ta,tr,v,rh,valid):
    assert bool(tc.utci_domain_mask(ta,tr,v,rh)) is valid

@pytest.mark.parametrize('invalid',[float('nan'),float('inf'),float('-inf')])
def test_invalid_utci_never_labeled_extreme(invalid):
    assert tc.categoria_utci(invalid)=='Fuera de dominio UTCI'


def test_utci_real_package_domain_and_map_coverage():
    pytest.importorskip('pythermalcomfort')
    assert np.isfinite(tc.utci(30,45,1,60))
    assert np.isnan(tc.utci(30,120,1,60))
    map_=mapa_estres(np.array([[40,120],[50,np.nan]]),30,60,v_ms=1)
    assert map_['n_pixeles']==3 and map_['n_pixeles_validos_indice']==2
    assert map_['por_area']['Fuera de dominio UTCI']==33.3
    all_invalid=mapa_estres(np.array([[120,150]]),30,60,v_ms=1)
    assert all_invalid['por_area']=={'Fuera de dominio UTCI':100.0}


def test_utci_array_masks_even_legacy_package_without_limits(monkeypatch):
    monkeypatch.setattr(tc,'_utci_pkg',lambda **kwargs:{'utci':np.full(np.asarray(kwargs['tr']).shape,35)})
    array=tc.utci_array(30,np.array([[40,120]]),1,60)
    assert array[0,0]==35 and np.isnan(array[0,1])

@pytest.mark.parametrize('kwargs',[{'tg':float('nan')},{'ta':float('inf')},{'v':-1},{'diametro':0},{'emisividad':1.1},{'tg':-274},{'tg':0,'ta':80,'v':100}])
def test_globe_rejects_invalid_physics(kwargs):
    inputs=dict(tg=35,ta=30,v=1); inputs.update(kwargs)
    with pytest.raises(ValueError):tc.globo_negro_a_tmrt(**inputs)


def test_globe_at_zero_wind_matches_globe_temperature():
    assert tc.globo_negro_a_tmrt(35,30,0)==pytest.approx(35)


def energy(**overrides):
    inputs=dict(air_temp_k=300,incident_shortwave_wm2=700,solar_absorptance=.8,longwave_emissivity=.95,
        convective_coefficient_wm2k=10,thermal_conductivity_wmk=1,coupling_depth_m=.2)
    inputs.update(overrides); return solve_surface_energy_balance(**inputs)


def test_solver_clipped_not_converged_exposed():
    outcome=energy(incident_shortwave_wm2=1e6)
    status=surface_diagnostics_summary(outcome)
    assert status['boundary_clipped'] and not status['converged'] and status['warnings']
    assert status['max_abs_residual_wm2']>1e4
    assert surface_diagnostics_summary(energy())['status']=='ok'

@pytest.mark.parametrize('field',['incident_shortwave_wm2','solar_absorptance','longwave_emissivity','rh_pct','cloud_fraction','convective_coefficient_wm2k','substrate_temp_k'])
def test_solver_rejects_nonfinite(field):
    with pytest.raises(ValueError):energy(**{field:float('nan')})


def test_saved_map_load_has_no_scope_error(tmp_path):
    obj=SombraApp.__new__(SombraApp); file=tmp_path/'map.npz'
    np.savez(file,tmrt=np.ones((2,3))*34,air_temp=30)
    assert obj._load_tmrt_bundle(file)
    assert obj.tmrt_map.shape==(2,3)


def test_excel_result_context_persists_as_json(tmp_path):
    import pandas as pd
    config=resolved().to_dict(); out=tmp_path/'result.xlsx'
    exportar_tabla_excel([{'effective_scenario_map':config,'effective_scenario_point':config}],out)
    result=pd.read_excel(out)
    assert json.loads(result.loc[0,'Escenario mapa JSON'])['tmrt_model']=='advanced'


def test_hourly_provider_changes_each_instant_and_records_source():
    seen=[]
    def provider(ta,hour,calc):
        seen.append(hour)
        from core.local_time import local_instant, instant_metadata
        base = resolved(ghi=hour*20,dni=0,dhi=hour*20)
        instant = local_instant(date.fromisoformat(base.date_iso),hour,base.timezone)
        return replace(base,hour_local=hour,air_temp_c=ta,**instant_metadata(instant))
    output=escenario_horario(Temperatura(-31.4,-64.2),date(2024,1,15),[8,12,16],20,34,60,4,50,scenario_provider=provider)
    assert seen==[8,12,16]
    assert [r['ghi'] for r in output]==[160,240,320]
    assert output[0]['effective_scenario']['source_mode']=='manual_scenario'
    bad=[dict(r,utci_sol=float('nan'),utci_sombra=float('nan')) for r in output]
    summary=resumen_escenario(bad)
    assert summary['utci_horas_fuera_dominio_sol']==3
    assert summary['utci_categoria_sol']=='Fuera de dominio UTCI'


def test_actual_renderers_agree_with_resolved_geometry_and_status(monkeypatch):
    import diseno, modelo_con_excel
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    class Canvas(FigureCanvasAgg):
        def __init__(self,figure,master=None):super().__init__(figure)
        def get_tk_widget(self):return SimpleNamespace(pack=lambda **kwargs:None)
    monkeypatch.setattr(diseno,'FigureCanvasTkAgg',Canvas)
    monkeypatch.setattr(modelo_con_excel,'FigureCanvasTkAgg',Canvas)
    obj=app('advanced','manual_scenario'); frame=SimpleNamespace(winfo_children=lambda:[])
    result=modelo_con_excel.generar_grafico(obj.vars_modelo,frame)
    diseno.actualizar_grafico(obj.vars,frame)
    assert result['meta']['surface_model']=='advanced_vegetation'
    assert result['meta']['surface_diagnostics']['converged']
    assert obj.vars['_last_meta']['effective_scenario']==result['meta']['effective_scenario']
    np.testing.assert_allclose(obj.vars['T'],result['T'])


def test_date_observers_receive_new_year_before_day_change():
    obj=app()
    observed=[]
    class ObservedVar(Var):
        def set(self,value):
            super().set(value)
            observed.append(obj.vars_modelo['_year'])
    day=ObservedVar(196); obj.vars_modelo['dia']=day
    obj.actualizar_dia('2028-02-29',day)
    assert observed==[2028]
    assert obj._fecha_modelo_actual()==date(2028,2,29)


def test_scene_hour_24_records_next_calendar_day():
    obj=app('simple'); obj.vars_modelo['hora'].set(24)
    obj.vars_modelo['_year']=2024; obj.vars_modelo['dia'].set(366)
    result=prepare_surface_scenario(obj.vars_modelo)
    assert (result['date_iso'],result['hour_local'])==('2025-01-01',0)

@pytest.mark.parametrize('field,value',[('solar_absorptance',1.1),('solar_absorptance',-.1),('longwave_emissivity',0),('thermal_conductivity_wmk',0),('coupling_depth_m',-1),('latent_heat_flux_wm2',-1),('rh_pct',-1),('cloud_fraction',1.1)])
def test_solver_invalid_physical_domain_rejected(field,value):
    with pytest.raises(ValueError):energy(**{field:value})


def test_utci_domain_presentation():
    assert tc.formato_utci(float('nan'))=='N/D (Fuera de dominio UTCI)'
    assert 'calor extremo' not in tc.formato_utci(float('nan'))


def test_standalone_simple_surface_ignores_hidden_advanced_selector():
    from modelo_con_excel import calcular_campo_termico_superficie
    variables=mapping(); variables['_modo_modelo']='simple'; variables['_surface_model_mode']='advanced_vegetation'
    x,y=np.meshgrid([0,1],[0,1])
    result=calcular_campo_termico_superficie(variables,x,y,1,0,600,300)
    assert result['model']=='standard'

@pytest.mark.parametrize('ta,ghi',[(float('nan'),600),(-1,600),(300,-1),(300,float('inf'))])
def test_standard_surface_rejects_invalid_inputs(ta,ghi):
    from modelo_con_excel import calcular_campo_termico_superficie
    x,y=np.meshgrid([0,1],[0,1])
    with pytest.raises(ValueError):calcular_campo_termico_superficie(mapping(),x,y,1,0,ghi,ta)
