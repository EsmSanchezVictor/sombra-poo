from datetime import datetime, date
import pytest
from services.solar_engine import SolarEngine
from core.meteorology import MeteorologicalSeries
from core.scenario import ranking_arboles
from shadow_temp import Temperatura
from modelo_con_excel import Arbol

@pytest.mark.parametrize('pvlib',[False,True])
@pytest.mark.parametrize('dt',[datetime(2024,3,10,2,30),datetime(2024,11,3,1,30)])
def test_invalid_local_time_not_silently_changed(dt,pvlib):
    engine=SolarEngine(tz='America/New_York',use_pvlib=pvlib)
    with pytest.raises(ValueError,match='inexistente|ambigua'):
        engine.get_solar_position(40.7,-74,dt)

def test_repeated_observations_preserved(tmp_path):
    f=tmp_path/'data.csv';f.write_text('timestamp,ghi\n2024-11-03T01:30:00-04:00,100\n2024-11-03T01:30:00-05:00,300\n')
    series=MeteorologicalSeries.from_csv(f,timezone='America/New_York')
    assert series.n==2
    assert series.sample_at(datetime.fromisoformat('2024-11-03T01:30:00-04:00')).get('ghi')==100
    assert series.sample_at(datetime.fromisoformat('2024-11-03T01:30:00-05:00')).get('ghi')==300

def test_advanced_ranking_needs_actual_context():
    calc=Temperatura(-31.4,-64.2,model_mode='advanced')
    with pytest.raises(ValueError,match='escenario efectivo'):
        ranking_arboles([Arbol(0,0,5,1,2)],calc,date(2024,1,15),13)
