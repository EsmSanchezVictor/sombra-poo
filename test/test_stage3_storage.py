"""Recuperación de fallos y corrupción reales sobre carpetas temporales."""
from pathlib import Path
from types import SimpleNamespace
import json
import logging
import os
import sqlite3
import subprocess
import sys
import zipfile
import numpy as np
import pytest
import openpyxl
from core.project import Project
from core.project_lock import project_lock, ProjectBusyError
from core.project_schema import migrate_payload, UnsupportedSchemaError
from core.project_integrity import IntegrityTracker, verify_inventory, sha256_file
from core.safe_io import atomic_output, atomic_write_json
from services.project_storage import ProjectStorage, read_json
from services.analysis_record_store import AnalysisRecordStore
from core.project_manager import ProjectManager
from services.project_copy import copy_project


def payload(tag='old'):
    return {'version':1,'layout_version':2,'next_n':1,'meta':{'name':'Plaza','saved_at':tag},
            'vars':{},'scene':{},'ui':{},'paths':{},'snapshots':[],'tag':tag}


def writer(tag):
    def write(kind,path):
        book=openpyxl.Workbook();book.active.append([kind,tag]);book.save(path);book.close()
    return write

@pytest.fixture
def project(tmp_path):
    project=Project(str(tmp_path/'Plaza'))
    project.ensure_structure()
    (Path(project.layout.images_dir)/'foto.jpg').write_bytes(b'foto original')
    records=AnalysisRecordStore(project.root_path)
    records.upsert({'analysis_id':'tree1','n':1,'label':'old','image':'entradas/imagenes/foto.jpg'})
    project.storage.commit(project.state_path,payload(),scene_writer=writer('old'))
    return project


def generation(project):
    pointer=read_json(project.storage.head)
    return Path(project.storage._generation(pointer['transaction_id']))


def test_cohort_has_same_state_sqlite_scenes_and_inventory(project):
    state=read_json(project.state_path);mirror=read_json(project.config_path)
    assert state==mirror and state['state_schema_version']==2
    assert read_json(project.layout.inventory_manifest)['transaction_id']==state['save_transaction_id']
    assert verify_inventory(project.root_path,read_json(project.layout.inventory_manifest))==[]
    book = openpyxl.load_workbook(project.layout.edit_excel)
    try:
        assert list(book.active.values)[0]==('edit','old')
    finally:
        book.close()


def test_preparation_failure_keeps_previous_state_and_scenes(project):
    old={p:Path(p).read_bytes() for p in (project.state_path,project.config_path,project.layout.edit_excel,project.layout.model_excel)}
    def fail(kind,path):
        if kind=='model':raise OSError('disco lleno simulado')
        writer('new')(kind,path)
    with pytest.raises(OSError):project.storage.commit(project.state_path,payload('new'),scene_writer=fail)
    assert all(Path(p).read_bytes()==value for p,value in old.items())
    assert not Path(project.storage.journal).exists()

@pytest.mark.parametrize('stop_after',[1,2,3,4,5])
def test_partial_publication_is_completed_at_next_open(project,monkeypatch,stop_after):
    import services.project_storage as module
    original=module.atomic_copy;count=0
    def fail(source,target):
        nonlocal count
        count+=1
        original(source,target)
        if count==stop_after:raise OSError('interrupción simulada')
    monkeypatch.setattr(module,'atomic_copy',fail)
    with pytest.raises(OSError):project.storage.commit(project.state_path,payload('new'),scene_writer=writer('new'))
    assert Path(project.storage.journal).exists()
    monkeypatch.setattr(module,'atomic_copy',original)
    state,recovered,issues=ProjectStorage(project.root_path).load(project.state_path)
    assert state['tag']=='new' and recovered['reason']=='interrupted_save' and issues==[]
    assert read_json(project.config_path)['tag']=='new'
    assert not Path(project.storage.journal).exists()


def test_hard_process_exit_releases_lock_and_recovers(project):
    code='''import os
from services.project_storage import ProjectStorage
import services.project_storage as module
original=module.atomic_copy
def crash(source,target):
    original(source,target)
    os._exit(77)
module.atomic_copy=crash
store=ProjectStorage(os.environ['TEST_PROJECT_ROOT'])
store.commit(os.environ['TEST_STATE_PATH'],{'version':1,'tag':'after_crash','next_n':1})
'''
    env=dict(os.environ,TEST_PROJECT_ROOT=project.root_path,TEST_STATE_PATH=project.state_path,PYTHONDONTWRITEBYTECODE='1')
    process=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True)
    assert process.returncode==77,process.stderr.decode()
    state,recovered,_=ProjectStorage(project.root_path).load(project.state_path)
    assert state['tag']=='after_crash' and recovered['reason']=='interrupted_save'


def test_primary_corruption_restores_and_preserves_bad_original(project):
    Path(project.state_path).write_bytes(b'archivo cortado')
    state,recovered,issues=project.storage.load(project.state_path)
    assert state['tag']=='old' and issues==[]
    preserved=Path(project.root_path)/recovered['preserved_at']/Path(project.state_path).name
    assert preserved.read_bytes()==b'archivo cortado'
    assert read_json(project.state_path)==read_json(project.config_path)


def test_sqlite_divergence_preserved_when_recovering_consistent_cohort(project):
    store=AnalysisRecordStore(project.root_path)
    store.upsert({'analysis_id':'tree2','n':2,'label':'uncommitted'})
    _,recovered,_=project.storage.load(project.state_path)
    assert 'analisis/analisis.sqlite3' in recovered['files']
    assert AnalysisRecordStore(project.root_path).count()==1
    conn=sqlite3.connect(str(Path(project.root_path)/recovered['preserved_at']/'analisis/analisis.sqlite3'))
    try:assert conn.execute('SELECT count(*) FROM analysis_records').fetchone()[0]==2
    finally:conn.close()


def test_corrupt_current_generation_uses_previous_verified_generation(project):
    project.storage.commit(project.state_path,payload('new'),scene_writer=writer('new'))
    (generation(project)/Path(project.state_path).name).write_bytes(b'corrupt generation')
    state,recovered,_=project.storage.load(project.state_path)
    assert state['tag']=='old' and recovered['reason']=='previous_generation'


def test_two_committed_generations_retained_and_orphan_removed(project):
    folder=Path(project.storage._generation('f'*32));folder.mkdir()
    (folder/'partial').write_bytes(b'incomplete')
    for tag in ('one','two','three'):
        project.storage.commit(project.state_path,payload(tag),scene_writer=writer(tag))
    parents=Path(project.storage.home)/'generations'
    assert len(list(parents.iterdir()))==2
    assert not folder.exists()


def test_head_future_protocol_is_rejected_without_restore(project):
    before=Path(project.state_path).read_bytes()
    atomic_write_json(project.storage.head,{'protocol_version':99,'transaction_id':'f'*32})
    with pytest.raises(ValueError):project.storage.load(project.state_path)
    assert Path(project.state_path).read_bytes()==before


def test_forged_journal_traversal_is_rejected(project,tmp_path):
    outside=tmp_path/'outside';outside.write_bytes(b'protected')
    atomic_write_json(project.storage.journal,{'protocol_version':1,'transaction_id':'../outside'})
    with pytest.raises(ValueError):project.storage.recover()
    assert outside.read_bytes()==b'protected'


def test_missing_staged_file_never_publishes(project,monkeypatch):
    import services.project_storage as module
    original=module.atomic_copy
    monkeypatch.setattr(module,'atomic_copy',lambda *args:(_ for _ in ()).throw(OSError('stop')))
    with pytest.raises(OSError):project.storage.commit(project.state_path,payload('new'))
    tid=read_json(project.storage.journal)['transaction_id']
    (Path(project.storage._generation(tid))/'config/project.json').unlink()
    monkeypatch.setattr(module,'atomic_copy',original)
    before=Path(project.state_path).read_bytes()
    with pytest.raises(ValueError):project.storage.recover()
    assert Path(project.state_path).read_bytes()==before


def test_inventory_detects_artifact_modification_and_retains_incident(project):
    (Path(project.layout.images_dir)/'foto.jpg').write_bytes(b'fotografia distinta')
    state,recovered,issues=project.storage.load(project.state_path)
    assert recovered is None
    assert issues[0]['path']=='entradas/imagenes/foto.jpg'
    assert state['integrity_events'][0]['issues']==issues
    with pytest.raises(ValueError):project.storage.export(Path(project.root_path)/'export.3es')
    project.storage.commit(project.state_path,state,scene_writer=writer('old'))
    saved,_,fresh=project.storage.load(project.state_path)
    assert not fresh and saved['integrity_events']


def test_inventory_hash_cache_does_not_trust_previous_file_manifest(project,monkeypatch):
    import core.project_integrity as module
    tracker=IntegrityTracker();calls=[];real=module.sha256_file
    def capture(path):calls.append(path);return real(path)
    monkeypatch.setattr(module,'sha256_file',capture)
    one=tracker.inventory(project.root_path);first=len(calls)
    assert tracker.inventory(project.root_path)['files']==one['files']
    assert len(calls)==first
    photo=Path(project.layout.images_dir)/'foto.jpg';photo.write_bytes(b'new')
    tracker.inventory(project.root_path)
    assert len(calls)==first+1

@pytest.mark.parametrize('rel',['../escape','/absolute','config/../escape','C:/escape'])
def test_forged_inventory_cannot_read_external_file(project,rel):
    with pytest.raises(ValueError):verify_inventory(project.root_path,{'integrity_schema_version':1,'files':[{'path':rel,'sha256':'0'*64}]})

@pytest.mark.parametrize('field,value',[('version',2),('state_schema_version',99),('layout_version',99),('state_schema_version','2'),('next_n',0),('vars',[]),('paths',[]),('snapshots',[None]),('integrity_events',{})])
def test_unknown_or_invalid_schema_rejected(field,value):
    original=payload();original[field]=value
    with pytest.raises(ValueError):migrate_payload(original)


def test_schema_migration_idempotent_and_preserves_custom_fields():
    original=payload();original['custom']={'a':[1,2]}
    new=migrate_payload(original)
    assert 'state_schema_version' not in original
    assert new['custom']==original['custom'] and new['state_schema_version']==2
    assert migrate_payload(new)==new

@pytest.mark.parametrize('via',['pragma','metadata','invalid_metadata'])
def test_future_sqlite_schema_not_overwritten(project,via):
    conn=sqlite3.connect(project.layout.analysis_db)
    try:
        if via=='pragma':conn.execute('PRAGMA user_version=99')
        else:conn.execute("UPDATE metadata SET value=? WHERE key='schema_version'",('99' if via=='metadata' else 'invalid',))
        conn.commit()
    finally:conn.close()
    before=Path(project.layout.analysis_db).read_bytes()
    with pytest.raises(ValueError):AnalysisRecordStore(project.root_path)
    assert Path(project.layout.analysis_db).read_bytes()==before


def test_lock_reentrant_and_other_process_cannot_write(project):
    code='''import os
from core.project_lock import project_lock,ProjectBusyError
try:
    with project_lock(os.environ['TEST_PROJECT_ROOT']):print('free')
except ProjectBusyError:print('busy')
'''
    env=dict(os.environ,TEST_PROJECT_ROOT=project.root_path)
    with project_lock(project.root_path):
        with project_lock(project.root_path):
            child=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
            assert child.stdout.strip()=='busy'
    child=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert child.stdout.strip()=='free'


def test_export_atomic_and_excludes_private_recovery_and_lock(project,tmp_path,monkeypatch):
    target=tmp_path/'project.3es'
    project.storage.export(target);before=target.read_bytes()
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any('.sombra-recovery' in name or name.endswith('save.lock') for name in archive.namelist())
    real=zipfile.ZipFile.write
    monkeypatch.setattr(zipfile.ZipFile,'write',lambda *args,**kwargs:(_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):project.storage.export(target)
    assert target.read_bytes()==before


def test_copy_is_prepared_and_remains_portable(project,tmp_path):
    target=tmp_path/'OtraPlaza';state=copy_project(project,target)
    assert Path(state).name=='OtraPlaza.sombra'
    assert read_json(state)['meta']['cloned_from']=='Plaza'
    assert not (target/'.sombra-recovery').exists()
    assert verify_inventory(target,read_json(target/'config/inventario.json'))==[]
    assert AnalysisRecordStore(str(target)).count()==1


def test_copy_failure_leaves_no_destination(project,tmp_path,monkeypatch):
    import services.project_copy as module
    target=tmp_path/'failed'
    monkeypatch.setattr(module.shutil,'copytree',lambda *args,**kwargs:(_ for _ in ()).throw(OSError('error')))
    with pytest.raises(OSError):copy_project(project,target)
    assert not target.exists()
    assert read_json(project.state_path)['tag']=='old'


def test_copy_into_original_rejected(project):
    with pytest.raises(ValueError):copy_project(project,Path(project.root_path)/'nested')


def test_json_legacy_secondary_recovered_without_inventing_content(tmp_path):
    root=tmp_path/'Legacy';(root/'config').mkdir(parents=True)
    state=root/'Legacy.sombra';state.write_bytes(b'broken')
    atomic_write_json(root/'config/project.json',payload())
    saved,recovery,issues=ProjectStorage(root).load(state)
    assert saved['tag']=='old' and recovery['reason']=='secondary_state' and issues==[]


def test_bad_legacy_secondary_does_not_replace_bad_primary(tmp_path):
    root=tmp_path/'Legacy';(root/'config').mkdir(parents=True)
    state=root/'Legacy.sombra';state.write_bytes(b'broken')
    (root/'config/project.json').write_bytes(b'also broken')
    with pytest.raises(ValueError):ProjectStorage(root).load(state)
    assert state.read_bytes()==b'broken'


def test_future_legacy_state_does_not_fallback_to_old_secondary(tmp_path):
    root=tmp_path/'Future';(root/'config').mkdir(parents=True)
    state=root/'Future.sombra';atomic_write_json(state,dict(payload(),state_schema_version=99))
    atomic_write_json(root/'config/project.json',payload())
    with pytest.raises(UnsupportedSchemaError):ProjectStorage(root).load(state)
    assert read_json(state)['state_schema_version']==99


def test_npz_failure_keeps_old_map(tmp_path,monkeypatch):
    from services.snapshot_service import SnapshotService
    target=tmp_path/'map.npz';np.savez_compressed(target,tmrt=np.ones((2,2)))
    old=target.read_bytes()
    service=SnapshotService(SimpleNamespace(tmrt_hover_data={'tmrt':np.zeros((2,2))}),None)
    def fail(path,**kwargs):Path(path).write_bytes(b'partial');raise OSError('interrupted')
    monkeypatch.setattr(np,'savez_compressed',fail)
    with pytest.raises(OSError):service._save_tmrt_hover(target)
    assert target.read_bytes()==old


def test_excel_failure_keeps_previous_workbook(tmp_path,monkeypatch):
    import pandas as pd
    from core.excel_scene import save_scene_excel
    target=tmp_path/'scene.xlsx';save_scene_excel(target,[],[],{'dia':1,'_year':2024})
    before=target.read_bytes()
    monkeypatch.setattr(pd.DataFrame,'to_excel',lambda *a,**k:(_ for _ in ()).throw(OSError('writer failed')))
    with pytest.raises(Exception):save_scene_excel(target,[],[],{'dia':2,'_year':2024})
    assert target.read_bytes()==before


def variables():
    return {'hora':12,'dia':15,'_year':2024,'lat':-31.4,'lon':-64.2,'T_amb_base':300,'T_min':290,'T_max':308,
            'I_sol_base':700,'humedad':60,'viento':'moderado','timezone':'America/Argentina/Buenos_Aires','arboles':[],'estructuras':[]}


def manager(tmp_path,monkeypatch):
    from core import project_manager as module
    messages=[]
    for method in ('showerror','showwarning','showinfo'):
        monkeypatch.setattr(module.messagebox,method,lambda *args:messages.append(args))
    saved=[]
    app=SimpleNamespace(vars=variables(),vars_modelo=variables(),settings={},is_dirty=True,
        update_status_saved_time=lambda stamp:saved.append(stamp),project_integrity_events=[],
        last_edit_excel_path=None,last_model_excel_path=None)
    state=SimpleNamespace(build_payload=lambda project:payload())
    pm=ProjectManager(app,state);pm.current_project=Project(str(tmp_path/'Manager'))
    return pm,messages,saved


def test_manager_failure_does_not_mark_saved_or_update_scene_paths(tmp_path,monkeypatch):
    pm,messages,saved=manager(tmp_path,monkeypatch)
    import services.scene_persistence as module
    monkeypatch.setattr(module,'write_scene',lambda *a:(_ for _ in ()).throw(OSError('Excel failed')))
    assert not pm.autosave_project()
    assert pm.app.is_dirty and not saved and pm.app.last_edit_excel_path is None
    assert messages and not Path(pm.current_project.state_path).exists()


def test_manager_commits_both_scene_paths_then_marks_saved(tmp_path,monkeypatch):
    pm,messages,saved=manager(tmp_path,monkeypatch)
    assert pm.autosave_project()
    state=read_json(pm.current_project.state_path)
    assert state['paths']['edit_excel']=='escena/edicion.xlsx'
    assert state['paths']['model_excel']=='escena/modelo.xlsx'
    assert pm.app.last_edit_excel_path==pm.current_project.layout.edit_excel
    assert not pm.app.is_dirty and saved and not messages


def test_backup_failure_reported_even_when_core_was_saved(tmp_path,monkeypatch):
    pm,messages,saved=manager(tmp_path,monkeypatch)
    monkeypatch.setattr(pm,'_create_backup',lambda:None)
    assert not pm.save_project()
    assert Path(pm.current_project.state_path).is_file() and not pm.app.is_dirty
    assert messages


def test_save_as_aborts_when_consolidation_failed(tmp_path,monkeypatch):
    pm,messages,saved=manager(tmp_path,monkeypatch)
    import core.project_manager as module
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **kwargs:str(tmp_path/'dest.sombra'))
    monkeypatch.setattr(pm,'autosave_project',lambda:False)
    assert not pm.save_project_as() and not (tmp_path/'dest').exists()


def test_import_checks_hashes_before_publishing(project,tmp_path):
    package=tmp_path/'export.3es';project.storage.export(package)
    app=SimpleNamespace(settings={});pm=ProjectManager(app);pm.projects_root=str(tmp_path/'imports')
    state=pm.import_archive(package)
    assert Path(state).exists()
    tampered=tmp_path/'changed.3es'
    with zipfile.ZipFile(package) as src,zipfile.ZipFile(tampered,'w') as dest:
        for name in src.namelist():dest.writestr(name,b'changed' if name.endswith('foto.jpg') else src.read(name))
    before=set(Path(pm.projects_root).iterdir())
    with pytest.raises(ValueError):pm.import_archive(tampered)
    assert set(Path(pm.projects_root).iterdir())==before


def test_import_rejects_recovery_commands(tmp_path):
    package=tmp_path/'malicious.3es'
    with zipfile.ZipFile(package,'w') as archive:
        archive.writestr('Plaza.sombra',json.dumps(payload()))
        archive.writestr('.sombra-recovery/journal.json','{}')
    pm=ProjectManager(SimpleNamespace(settings={}));pm.projects_root=str(tmp_path/'imports')
    with pytest.raises(ValueError):pm.import_archive(package)
    assert not list(Path(pm.projects_root).iterdir())
