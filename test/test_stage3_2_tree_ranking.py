"""Ranking contra el motor Tmrt, geometría y aislamiento real de escena/modo."""
from datetime import date
import json
import numpy as np
import pytest
from core.scenario import ranking_arboles, ranking_export_payload
from services.tree_ranking_service import rank_app_trees
from core.safe_io import atomic_write_json
from modelo_con_excel import Arbol, calcular_sombra_arboles
from shadow_temp import Temperatura
from test.test_stage2_science import resolved, app

@pytest.mark.parametrize('model',['standard','advanced'])
def test_ranking_matches_effective_tmrt_maps(model):
    config=resolved(selected_model=model,ghi=500,dni=600,dhi=100)
    tree=Arbol(0,0,7,.7,4)
    result=ranking_arboles([tree],None,date(1999,1,1),0,extent=60,resolucion=60,scenario=config)[0]
    axis=-30+(np.arange(60)+.5);X,Y=np.meshgrid(axis,axis)
    tau=calcular_sombra_arboles(X,Y,[tree],np.radians(config.solar_elevation),np.radians(config.solar_azimuth))
    calc=config.calculator();kw=config.calculation_kwargs();zero=np.zeros_like(X)
    sun=calc.calculate_tmrt_map(config.air_temp_c,zero,transmittance_map_override=np.ones_like(X),**kw)['Tmrt_map']
    shade=calc.calculate_tmrt_map(config.air_temp_c,zero,transmittance_map_override=tau,**kw)['Tmrt_map']
    assert result['delta_tmrt_prom']==pytest.approx(np.mean(sun.astype(float)-shade),abs=1e-8)
    assert result['tmrt_model']==model and result['effective_scenario']==config.to_dict()
    assert result['method']=='individual_tree_tmrt_v2'


def test_manual_zero_ghi_not_replaced_with_clear_sky():
    config=resolved(ghi=0,dni=0,dhi=0)
    result=ranking_arboles([Arbol(0,0,7,.7,4)],None,None,None,scenario=config)[0]
    assert result['delta_tmrt_prom']==0 and result['categoria']=='Sin radiación solar'
    assert result['effective_scenario']['source_mode']=='manual_scenario'


def test_bounded_area_cell_centers_even_with_entire_domain_shaded():
    config=resolved(selected_model='standard')
    tree=Arbol(0,0,0,1,10000)
    result=ranking_arboles([tree],None,None,None,extent=10,resolucion=2,scenario=config)[0]
    assert result['area_sombra_m2']==100 and result['cobertura_frac']==1
    assert result['delta_tmrt_prom']==pytest.approx(config.k_factor*config.ghi,abs=1e-4)


def test_order_uses_precision_and_ids_remain_source_order():
    config=resolved(selected_model='standard',ghi=500,dni=600,dhi=100)
    # Geometría idéntica, diferencia térmica menor que el redondeo visible.
    a=Arbol(0,0,7,.5,4);b=Arbol(0,0,7,.500001,4)
    results=ranking_arboles([a,b],None,None,None,scenario=config)
    assert results[0]['arbol'] is b and results[0]['tree_index']==2
    assert results[1]['tree_index']==1
    assert round(results[0]['delta_tmrt_prom'],2)==round(results[1]['delta_tmrt_prom'],2)
    assert results[0]['delta_tmrt_prom']>results[1]['delta_tmrt_prom']


def test_individual_comparison_does_not_claim_overlap_attribution():
    config=resolved();a=Arbol(0,0,7,.7,4);b=Arbol(0,0,7,.7,4)
    result=ranking_arboles([a,b],None,None,None,scenario=config)
    assert result[0]['delta_tmrt_prom']==result[1]['delta_tmrt_prom']
    assert all(r['overlap_attribution'] is False for r in result)

@pytest.mark.parametrize('extent,resolution',[(-1,60),(float('nan'),60),(float('inf'),60),(60,1),(60,641),(60,2.5),(60,True)])
def test_invalid_grid_rejected(extent,resolution):
    with pytest.raises(ValueError):ranking_arboles([],None,None,None,extent=extent,resolucion=resolution,scenario=resolved())

@pytest.mark.parametrize('name,value',[('radio_copa',0),('h',-1),('x',float('nan')),('rho_copa',2)])
def test_invalid_tree_geometry_rejected(name,value):
    tree=Arbol(0,0,7,.7,4);setattr(tree,name,value)
    with pytest.raises(ValueError,match='árbol 1'):ranking_arboles([tree],None,None,None,scenario=resolved())


def test_advanced_api_requires_actual_context():
    with pytest.raises(ValueError,match='escenario efectivo'):
        ranking_arboles([Arbol(0,0,7,.7,4)],Temperatura(-31.4,-64.2,model_mode='advanced'),date(2024,1,15),13)


def configured_app(mode):
    obj=app(mode,radiation='manual_scenario');obj.use_pvlib_engine.set(False)
    obj._leer_parametros_tmrt=lambda:(30,13,date(2024,1,15),-31.4,-64.2)
    obj.vars['arboles']=[Arbol(0,0,5,.6,2)]
    obj.vars_modelo['arboles']=[Arbol(0,0,12,.8,5)]
    return obj


def test_app_scene_selection_never_merges_trees():
    obj=configured_app('advanced')
    config,a=rank_app_trees(obj,'Edición',resolution=40)
    _,b=rank_app_trees(obj,'Modelo',resolution=40)
    assert len(a)==len(b)==1
    assert a[0]['arbol'] is obj.vars['arboles'][0]
    assert b[0]['arbol'] is obj.vars_modelo['arboles'][0]
    assert config.tmrt_model=='advanced' and config.ghi==700
    with pytest.raises(ValueError):rank_app_trees(obj,'Todo')


def test_simple_ranking_ignores_hidden_advanced_rad_and_model():
    obj=configured_app('simple')
    config,a=rank_app_trees(obj,'Edición',resolution=40)
    obj.manual_ghi.set('0');obj.tmrt_model_mode.set('standard');obj.radiation_source_mode.set('observed_series')
    config_b,b=rank_app_trees(obj,'Edición',resolution=40)
    assert config.to_dict()==config_b.to_dict()
    assert a[0]['delta_tmrt_prom']==b[0]['delta_tmrt_prom']
    assert config.tmrt_model=='standard' and config.source_mode=='clear_sky'


def test_observed_ranking_uses_measured_air_and_radiation(tmp_path):
    obj=configured_app('advanced');obj.radiation_source_mode.set('observed_series')
    f=tmp_path/'meteo.csv';f.write_text('timestamp,ghi,ta_c,rh_pct,wind_m_s\n2024-01-15T13:00:00-03:00,450,35,75,2\n')
    obj.meteorology_service.load_series(f,timezone=obj._timezone_actual())
    config,results=rank_app_trees(obj,'Modelo',resolution=40)
    assert config.air_temp_c==35 and config.ghi==450 and config.wind_ref_10m_m_s==2
    assert results[0]['effective_scenario']['source_mode']=='observed_series'


def test_export_preserves_scene_geometries_and_context_atomically(tmp_path):
    obj=configured_app('advanced');config,results=rank_app_trees(obj,'Modelo',resolution=40)
    payload=ranking_export_payload(results,scene_name='Modelo');f=tmp_path/'ranking.json';atomic_write_json(f,payload)
    stored=json.loads(f.read_text())
    assert stored['effective_scenario']['instant_utc_iso']==config.instant_utc_iso
    assert stored['methodology']['scientific_schema']=='sombra-science/1.2'
    assert stored['rows'][0]['tree']['radio_copa']==5 and stored['rows'][0]['tree_index']==1
    assert stored['scene_name']=='Modelo' and stored['rows'][0]['comparison']=='individual_tree_against_full_sun'
