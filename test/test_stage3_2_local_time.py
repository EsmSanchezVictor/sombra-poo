"""Instantes difíciles, motores y meteorología observada: sin ventanas."""
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
import json
import pytest
from core.local_time import resolve_local_datetime, local_instant, instant_metadata, LocalTimeError
from core.solar_math import timezone_offset_hours
from core.meteorology import MeteorologicalSeries
from core.effective_scenario import EffectiveScenarioConfig
from core.validation import _offset_timezone, _elevacion_solar
from services.solar_engine import SolarEngine
from services.meteorology_service import MeteorologyService
from services.scenario_service import prepare_surface_scenario
from test.test_stage2_science import app, mapping

NY='America/New_York'

@pytest.mark.parametrize('zone,wall,kind',[
    (NY,datetime(2024,3,10,2,30),'inexistente'),
    (NY,datetime(2024,11,3,1,30),'ambigua'),
    ('Australia/Lord_Howe',datetime(2024,10,6,2,15),'inexistente'),
    ('Australia/Lord_Howe',datetime(2024,4,7,1,45),'ambigua'),
    ('Pacific/Apia',datetime(2011,12,30,12),'inexistente'),
])
def test_strict_wall_clock_never_guesses(zone,wall,kind):
    with pytest.raises(LocalTimeError,match=kind):resolve_local_datetime(wall,zone)

@pytest.mark.parametrize('fold,offset,utc_hour',[(0,-4,5),(1,-5,6)])
def test_explicit_fold_preserves_each_occurrence(fold,offset,utc_hour):
    local=resolve_local_datetime(datetime(2024,11,3,1,30),NY,fold=fold)
    meta=instant_metadata(local)
    assert local.fold==fold and meta['utc_offset_hours']==offset
    assert local.astimezone(timezone.utc)==datetime(2024,11,3,utc_hour,30,tzinfo=timezone.utc)
    assert resolve_local_datetime(datetime.fromisoformat(meta['instant_local_iso']),NY)==local
    assert json.loads(json.dumps(meta))==meta

@pytest.mark.parametrize('bad',[True,-1,2,'1'])
def test_invalid_fold_rejected(bad):
    with pytest.raises(ValueError,match='fold'):resolve_local_datetime(datetime(2024,1,1),NY,fold=bad)

@pytest.mark.parametrize('fold',[0,1])
def test_aware_zoneinfo_gap_not_made_valid_by_attaching_zone(fold):
    dt=datetime(2024,3,10,2,30,tzinfo=ZoneInfo(NY),fold=fold)
    with pytest.raises(LocalTimeError,match='inexistente'):resolve_local_datetime(dt,NY)

@pytest.mark.parametrize('wall,offset',[(datetime(2024,3,10,1,59),-5),(datetime(2024,3,10,3),-4),
                                        (datetime(2024,11,3,0,59),-4),(datetime(2024,11,3,2),-5)])
def test_transition_boundaries_valid(wall,offset):
    assert instant_metadata(resolve_local_datetime(wall,NY))['utc_offset_hours']==offset

@pytest.mark.parametrize('zone,offset',[(NY,-5),('America/Argentina/Buenos_Aires',-3),('Asia/Kathmandu',5.75)])
def test_hour_24_rolls_calendar_before_zone_resolution(zone,offset):
    local=local_instant(date(2023,12,31),24,zone)
    assert local.date()==date(2024,1,1) and local.hour==0
    assert local.utcoffset().total_seconds()/3600==offset

@pytest.mark.parametrize('hour',[-1,24.001,float('nan'),float('inf')])
def test_invalid_hour_rejected(hour):
    with pytest.raises(ValueError):local_instant(date(2024,1,1),hour,NY)

@pytest.mark.parametrize('pvlib',[False,True])
@pytest.mark.parametrize('wall',[datetime(2024,3,10,2,30),datetime(2024,11,3,1,30)])
def test_solar_paths_same_temporal_rejection(pvlib,wall):
    engine=SolarEngine(tz=NY,use_pvlib=pvlib)
    if pvlib and not engine.pvlib_available:pytest.skip('pvlib no disponible')
    for method in (engine.get_solar_position,engine.get_radiation,engine.get_solar_data):
        with pytest.raises(LocalTimeError):method(40.7,-74,wall)
    with pytest.raises(LocalTimeError):
        timezone_offset_hours(NY,wall.timetuple().tm_yday,wall.hour+wall.minute/60,year=wall.year)

@pytest.mark.parametrize('pvlib',[False,True])
def test_engine_explicit_offsets_provenance_and_position(pvlib):
    engine=SolarEngine(tz=NY,use_pvlib=pvlib)
    if pvlib and not engine.pvlib_available:pytest.skip('pvlib no disponible')
    a=engine.get_solar_data(40.7,-74,datetime.fromisoformat('2024-11-03T01:30:00-04:00'))
    b=engine.get_solar_data(40.7,-74,datetime.fromisoformat('2024-11-03T01:30:00-05:00'))
    assert a['instant_utc_iso']!=b['instant_utc_iso'] and a['azimuth']!=b['azimuth']
    assert a['utc_offset_hours']==-4 and b['utc_offset_hours']==-5
    assert a['time_fold']==0 and b['time_fold']==1


def csv(tmp_path,body):
    f=tmp_path/'meteo.csv';f.write_text('timestamp,ghi,ta_c\n'+body,encoding='utf-8');return f

@pytest.mark.parametrize('timestamp,kind',[('2024-03-10T02:30:00','inexistente'),('2024-11-03T01:30:00','ambigua')])
def test_csv_dst_error_reports_actual_row_and_keeps_previous_series(tmp_path,timestamp,kind):
    service=MeteorologyService()
    service.load_series(csv(tmp_path,'2024-01-01T12:00:00,500,20\n'),timezone=NY)
    previous=service.series
    with pytest.raises(ValueError,match=f'Fila 3.*{kind}'):
        service.load_series(csv(tmp_path,f'2024-01-01T12:00:00,500,20\n{timestamp},600,25\n'),timezone=NY)
    assert service.series is previous


def test_csv_offsets_keep_repeated_measurements_and_interpolate_in_utc(tmp_path):
    series=MeteorologicalSeries.from_csv(csv(tmp_path,'2024-11-03T01:30:00-04:00,100,20\n2024-11-03T01:30:00-05:00,300,30\n'),timezone=NY)
    assert series.n==2 and (series.end-series.start).total_seconds()==3600
    assert series.sample_at(datetime.fromisoformat('2024-11-03T01:30:00-04:00')).get('ghi')==100
    assert series.sample_at(datetime.fromisoformat('2024-11-03T01:30:00-05:00')).get('ghi')==300
    middle=series.sample_at(datetime.fromisoformat('2024-11-03T06:00:00+00:00'))
    assert middle.status=='interpolated' and middle.get('ghi')==200 and middle.get('ta_c')==25
    assert series.sample_at(datetime.fromisoformat('2024-11-03T06:00:00+00:00'),max_gap_minutes=30) is None
    with pytest.raises(LocalTimeError,match='ambigua'):series.sample_at(datetime(2024,11,3,1,30))


def test_csv_naive_and_offset_mixture_not_assumed_utc(tmp_path):
    with pytest.raises(ValueError,match='mezcla horas'):
        MeteorologicalSeries.from_csv(csv(tmp_path,'2024-01-01T12:00:00,500,20\n2024-01-01T13:00:00-05:00,600,25\n'),timezone=NY)


def test_csv_local_dates_and_malformed_rows_compatible(tmp_path):
    f=tmp_path/'local.csv';f.write_text('fecha,hora,ghi\n31/01/2024,12:00,500\n31/01/2024,13:00,600\nerror,error,700\n')
    series=MeteorologicalSeries.from_csv(f,timezone=NY)
    assert series.n==2 and series.start.day==31


def test_service_uses_engine_local_day_when_input_is_utc():
    service=MeteorologyService();engine=SolarEngine(tz='America/Argentina/Buenos_Aires')
    utc=datetime(2024,1,16,0,30,tzinfo=timezone.utc)
    local=datetime.fromisoformat('2024-01-15T21:30:00-03:00')
    a=service.resolve(mode='manual_scenario',solar_engine=engine,lat=-31.4,lon=-64.2,dt=utc,manual_ghi=50)
    b=service.resolve(mode='manual_scenario',solar_engine=engine,lat=-31.4,lon=-64.2,dt=local,manual_ghi=50)
    assert a==b and a['instant_local_iso'].startswith('2024-01-15')

@pytest.mark.parametrize('fold,offset',[(0,-4),(1,-5)])
def test_effective_scenario_keeps_explicit_instant_in_calculator(fold,offset):
    dt=resolve_local_datetime(datetime(2024,11,3,1,30),NY,fold=fold)
    solar=SolarEngine(tz=NY).get_solar_data(40.7,-74,dt)
    config=EffectiveScenarioConfig.from_resolved(input_mode='advanced',selected_model='advanced',
        fecha=dt.date(),hour=1.5,lat=40.7,lon=-74,timezone=NY,ta=20,rh=60,wind=2,k_factor=.04,solar=solar)
    assert config.utc_offset_hours==offset and config.time_fold==fold and config.schema_version==2
    calc=config.calculator()
    assert calc.solar_altitude(dt.timetuple().tm_yday,1.5)==pytest.approx(solar['elevation'])
    assert EffectiveScenarioConfig(**json.loads(json.dumps(config.to_dict()))).calculator().model_mode=='advanced'


def test_scenario_rejects_solar_instant_from_different_date():
    solar=SolarEngine().get_solar_data(-31.4,-64.2,datetime(2024,1,15,13))
    with pytest.raises(ValueError,match='no coincide'):
        EffectiveScenarioConfig.from_resolved(input_mode='simple',selected_model='standard',fecha=date(2024,1,16),
            hour=13,lat=-31.4,lon=-64.2,timezone='America/Argentina/Buenos_Aires',ta=30,rh=50,wind=2,k_factor=.04,solar=solar)

@pytest.mark.parametrize('day,hour',[(70,2.5),(308,1.5)])
def test_surface_simple_and_advanced_reject_dst_without_mutating_overrides(day,hour):
    for mode in ('simple','advanced'):
        values=mapping();values['_modo_modelo']=mode;values['dia'].set(day);values['hora'].set(hour);values['timezone'].set(NY)
        values['_radiation_override_ghi']=123
        with pytest.raises(LocalTimeError):prepare_surface_scenario(values)
        assert values['_radiation_override_ghi']==123


def test_validation_midnight_and_next_day_offsets():
    assert _offset_timezone({'timezone':NY},date(2024,3,10),0)==-5
    assert _offset_timezone({'timezone':NY},date(2024,3,10),24)==-4
    a=_elevacion_solar({'fecha':date(2024,12,31),'hora':24,'lat':40.7,'lon':-74,'timezone':NY})
    b=_elevacion_solar({'fecha':date(2025,1,1),'hora':0,'lat':40.7,'lon':-74,'timezone':NY})
    assert a==b and a[1]=='calculada'
    elev,reason=_elevacion_solar({'fecha':date(2024,3,10),'hora':2.5,'lat':40.7,'lon':-74,'timezone':NY})
    assert elev is None and 'inexistente' in reason


def test_invalid_iana_not_silently_replaced_by_longitude():
    with pytest.raises(ValueError,match='IANA'):SolarEngine(tz='Invalid/Zone')
    with pytest.raises(ValueError,match='IANA'):timezone_offset_hours('Invalid/Zone',1,12,year=2024)

@pytest.mark.parametrize('day,year',[(366,2025),(0,2024),(367,2024),(60.5,2024),(float('nan'),2024)])
def test_solar_offset_helper_does_not_roll_invalid_day(day,year):
    with pytest.raises(ValueError,match='Día del año'):timezone_offset_hours(NY,day,12,year=year)


def test_tk_error_handler_explains_time_error_and_keeps_log(monkeypatch):
    from types import SimpleNamespace
    from ui.error_handlers import install_tk_error_handler
    recorded=[];messages=[]
    root=SimpleNamespace();logger=SimpleNamespace(error=lambda *a,**k:recorded.append((a,k)))
    monkeypatch.setattr('tkinter.messagebox.showerror',lambda title,text:messages.append((title,text)))
    install_tk_error_handler(root,logger)
    error=LocalTimeError('Hora local ambigua: elija otro horario.')
    root.report_callback_exception(type(error),error,None)
    assert len(recorded)==1 and messages==[('Fecha y hora del escenario',str(error))]


def test_map_time_error_shown_before_photo_analysis(monkeypatch):
    from types import SimpleNamespace
    from ui.app_ui import SombraApp
    obj=app();obj.require_project=lambda _:True
    obj.shape_selector=SimpleNamespace(area_seleccionada=object())
    obj._leer_parametros_tmrt=lambda:(30,2.5,date(2024,3,10),40.7,-74)
    obj._timezone_actual=lambda:NY
    errors=[]
    monkeypatch.setattr('ui.app_ui.messagebox.showerror',lambda title,text:errors.append((title,text)))
    SombraApp.mostrar_curvas_nivel(obj)
    assert len(errors)==1 and 'inexistente' in errors[0][1]
    assert not hasattr(obj,'image_processor')  # No se intenta analizar/publicar otro mapa.


def test_captured_offset_reproduced_without_reinterpreting_zone_rules(monkeypatch):
    from test.test_stage2_science import resolved
    config=resolved()
    def unavailable(*args,**kwargs):raise AssertionError('No reinterpretar el instante capturado')
    monkeypatch.setattr('core.effective_scenario.local_instant',unavailable)
    monkeypatch.setattr('core.effective_scenario.resolve_local_datetime',unavailable)
    calc=config.calculator()
    day=date.fromisoformat(config.date_iso).timetuple().tm_yday
    assert calc.solar_altitude(day,config.hour_local)==pytest.approx(config.solar_elevation)

@pytest.mark.parametrize('changes',[
    {'instant_local_iso':'2024-01-15T13:00:00'},
    {'instant_utc_iso':'2024-01-15T18:00:00+00:00'},
    {'utc_offset_hours':-5},
    {'date_iso':'2024-01-16'},
])
def test_corrupt_captured_temporal_metadata_rejected(changes):
    from dataclasses import replace
    from test.test_stage2_science import resolved
    with pytest.raises(ValueError):replace(resolved(),**changes).calculator()


def test_old_scenario_without_captured_instant_keeps_ordinary_calculation():
    from dataclasses import replace
    from test.test_stage2_science import resolved
    new=resolved()
    legacy=replace(new,schema_version=1,instant_local_iso='',instant_utc_iso='',utc_offset_hours=None,time_policy='')
    day=date.fromisoformat(new.date_iso).timetuple().tm_yday
    assert legacy.calculator().solar_altitude(day,new.hour_local)==new.calculator().solar_altitude(day,new.hour_local)
