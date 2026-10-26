"""Boundary tests: no import of Tk/UI anywhere in the numerical core."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
BLOCK='''
import sys,importlib.abc
class NoGui(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tkinter','_tkinter','ui'):
            raise ImportError('GUI import forbidden: '+fullname)
sys.meta_path.insert(0,NoGui())
'''

def test_every_core_module_imports_with_tk_and_ui_forbidden():
    code=BLOCK+'''
import importlib,pkgutil,core
modules=list(pkgutil.walk_packages(core.__path__,'core.'))
for module in modules:importlib.import_module(module.name)
assert len(modules)>35
print('core-headless-ok',len(modules))
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'core-headless-ok' in result.stdout


def test_physics_suite_runs_with_tk_and_ui_forbidden():
    code=BLOCK+"\nimport pytest\nraise SystemExit(pytest.main(['-q','test/test_physics.py','-p','no:cacheprovider']))"
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=120,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg'))
    assert result.returncode==0,result.stdout+result.stderr


def test_legacy_numerical_api_reexports_identical_classes_and_kernels():
    import modelo_con_excel as legacy
    from core import surface_model
    for name in ('Arbol','Estructura','Material','materiales','calcular_sombra_arboles','calcular_campo_termico_superficie'):
        assert getattr(legacy,name) is getattr(surface_model,name)


def test_headless_project_requests_require_explicit_adapter():
    from core.project_manager import ProjectManager
    from core.interaction import InteractionRequiredError
    manager=ProjectManager(SimpleNamespace(settings={}))
    with pytest.raises(InteractionRequiredError):manager._select_project_path()


def test_project_interaction_is_injected_not_a_global_tk_dependency(tmp_path):
    from core.project_manager import ProjectManager
    class Adapter:
        def askopenfilename(self,**kwargs):return str(tmp_path/'Plaza.sombra')
    manager=ProjectManager(SimpleNamespace(settings={}),interaction=Adapter())
    assert manager._select_project_path()==str(tmp_path/'Plaza.sombra')


class Var:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


def state_app(project):
    return SimpleNamespace(vars={},vars_modelo={},current_location={},active_panel=0,
        modo_modelo=Var('simple'),simple_city=Var('Paraná'),simple_country=Var('Argentina'),
        simple_cloudiness=Var('Despejado'),simple_temp_air_c=Var(25),simple_rh=Var(50),
        last_image_path=None,last_mask_path=None,last_histogram_path=None,last_curve_path=None,
        last_matrix_path=None,last_edit_excel_path=None,last_model_excel_path=None,tmrt_result=None,
        project_manager=SimpleNamespace(current_project=project),locations_data={},panel_frames=[],
        _build_vars=lambda:{},_toggle_modelo_mode=lambda:None,update_status_saved_time=lambda _:None,
        restore_project_artifacts=lambda:None)


def test_state_build_and_apply_never_create_a_tk_variable(tmp_path):
    from core.project import Project
    from core.app_state import AppState
    project=Project(str(tmp_path/'Plaza'));project.ensure_structure()
    app=state_app(project);app.vars['example']=Var(12);app.shadow_coverage_fraction=.3
    payload=AppState(app).build_payload(project)
    assert payload['ui']['matrix_size']==128 and payload['vars']['example']==12
    assert payload['last_results_meta']['shadow_coverage_fraction']==.3
    assert 'shadow_quality' not in payload['last_results_meta']
    app2=state_app(project);AppState(app2).apply_payload(payload)
    assert app2.shadow_coverage_fraction==.3


def test_legacy_shadow_quality_is_read_without_reinterpreting_as_thermal_quality(tmp_path):
    from core.project import Project
    from core.app_state import AppState
    project=Project(str(tmp_path/'Legacy'));project.ensure_structure();app=state_app(project)
    AppState(app).apply_payload({'version':1,'last_results_meta':{'shadow_quality':.42}})
    assert app.shadow_coverage_fraction==.42


def test_state_rejects_unsupported_payload_before_changing_application():
    from core.app_state import AppState
    app=SimpleNamespace(marker='preserved')
    with pytest.raises(ValueError):AppState(app).apply_payload({'version':99})
    assert vars(app)=={'marker':'preserved'}
