"""Integration guards specific to the current uploaded source, not the former delivery."""
from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace


def test_current_meteorology_delegation_is_preserved(monkeypatch):
    from ui.app_ui import SombraApp
    from services import meteorology_controller
    calls=[];marker=object()
    def resolve(*args,**kwargs):calls.append((args,kwargs));return marker
    monkeypatch.setattr(meteorology_controller,'resolve_solar_data',resolve)
    app=SimpleNamespace()
    result=SombraApp._obtener_datos_solares(app,-31.,-60.,'2026-10-25',12.,manual_ghi=500.,mode_override='manual_measured',use_pvlib_override=False)
    assert result is marker and calls[0][0][0] is app
    assert calls[0][1]==dict(manual_ghi=500.,mode_override='manual_measured',use_pvlib_override=False)


def test_field_report_uses_current_v2_label_and_keeps_original_registry(tmp_path):
    from test.test_stage4_field import campaign
    from services.field_validation import evaluate_campaign
    from core.model_registry import TMRT_MODELS
    report=evaluate_campaign(campaign(tmp_path/'synthetic.csv'))
    assert TMRT_MODELS['advanced']['version']=='advanced_radiative_v2'
    assert TMRT_MODELS['advanced']['label'] in report['metrics_by_model']
    assert 'Avanzado v1' not in report['metrics_by_model']
    from core.validation import leer_csv_mediciones, evaluar_modelos, dataframe_resultados
    evaluated=evaluar_modelos(leer_csv_mediciones(str(tmp_path/'synthetic.csv')))
    table=dataframe_resultados(evaluated)
    assert set(table['modelo_avanzado'])=={'advanced_radiative_v2'}
    assert table['tmrt_avanzado_c'].equals(table['tmrt_avanzado_v1_c'])


def test_current_installation_check_runs_with_tk_forbidden(tmp_path):
    root=Path(__file__).resolve().parents[1];report=tmp_path/'check.json'
    code='''import sys,importlib.abc,runpy
class NoGui(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('tkinter','_tkinter','ui'):raise ImportError('GUI forbidden '+fullname)
sys.meta_path.insert(0,NoGui())
sys.argv=['check_installation.py','--require-full','--report',sys.argv[1]]
runpy.run_path('tools/check_installation.py',run_name='__main__')
'''
    result=subprocess.run([sys.executable,'-c',code,str(report)],cwd=root,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    output=json.loads(report.read_text())
    from core.app_version import APP_RELEASE
    assert output['status']=='passed' and output['app_release']==APP_RELEASE
    assert output['methodology']['tmrt_models']['advanced']['version']=='advanced_radiative_v2'
