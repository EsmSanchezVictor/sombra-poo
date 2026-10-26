"""Regresión de EBADF de Windows simulando su requisito de descriptor escribible."""
import builtins
import errno
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import pytest
from core.safe_io import atomic_output
from core.excel_scene import save_scene_excel, load_scene_excel
from core.project import Project
from services.analysis_record_store import AnalysisRecordStore
from services.project_storage import backup_sqlite, read_json
from services.project_copy import copy_project


@pytest.fixture
def windows_file_sync_rule(monkeypatch):
    """Sólo simula el rechazo de archivos de lectura; no simula todo Windows."""
    real_open, real_fsync = builtins.open, os.fsync
    handles, synced = {}, []
    def tracked_open(*args, **kwargs):
        handle = real_open(*args, **kwargs)
        handles[handle.fileno()] = handle
        return handle
    def strict_fsync(descriptor):
        handle = handles.get(descriptor)
        if handle is not None and not handle.closed:
            if not handle.writable():
                raise OSError(errno.EBADF, 'Bad file descriptor')
            synced.append(str(handle.name))
        return real_fsync(descriptor)
    monkeypatch.setattr(builtins, 'open', tracked_open)
    monkeypatch.setattr(os, 'fsync', strict_fsync)
    return synced, handles


def variables():
    return {'hora':12,'dia':15,'_year':2024,'lat':-31.4,'lon':-64.2,'T_amb_base':300.,
            'T_min':290.,'T_max':308.,'I_sol_base':700.,'humedad':60.,'viento':'moderado',
            'timezone':'America/Argentina/Buenos_Aires','arboles':[],'estructuras':[]}


def test_binary_publication_with_windows_sync_rule(tmp_path, windows_file_sync_rule):
    target=tmp_path/'map.npz';target.write_bytes(b'old file')
    with atomic_output(target) as temporary:
        Path(temporary).write_bytes(b'new complete map')
    assert target.read_bytes()==b'new complete map'
    synced,_=windows_file_sync_rule
    assert synced


def test_real_excel_writer_with_windows_sync_rule(tmp_path, windows_file_sync_rule):
    target=tmp_path/'scene.xlsx'
    save_scene_excel(target,[],[],variables())
    workbook=load_scene_excel(target)
    assert workbook.parametros['ano_escenario']==2024
    assert not list(tmp_path.glob('.sombra-write-*'))


def test_sqlite_backup_with_windows_sync_rule(tmp_path, windows_file_sync_rule):
    source=tmp_path/'source.sqlite3';target=tmp_path/'copy.sqlite3'
    conn=sqlite3.connect(source)
    try:
        conn.execute('CREATE TABLE example(value TEXT)')
        conn.execute("INSERT INTO example VALUES('preserved')");conn.commit()
    finally:conn.close()
    before=source.read_bytes()
    backup_sqlite(source,target)
    conn=sqlite3.connect(target)
    try:
        assert conn.execute('SELECT value FROM example').fetchone()[0]=='preserved'
        assert conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    finally:conn.close()
    assert source.read_bytes()==before


def test_project_save_reopen_export_and_copy_with_windows_sync_rule(tmp_path, windows_file_sync_rule):
    from core.project_manager import ProjectManager
    import core.project_manager as manager_module
    # No se abre Tk: se ejecutan los servicios y el flujo de guardado real.
    project=Project(str(tmp_path/'Plaza'));project.ensure_structure()
    records=AnalysisRecordStore(project.root_path)
    records.upsert({'analysis_id':'tree1','n':1,'label':'Arbol 1'})
    app=SimpleNamespace(vars=variables(),vars_modelo=variables(),settings={},is_dirty=True,
        project_integrity_events=[],last_edit_excel_path=None,last_model_excel_path=None,
        update_status_saved_time=lambda value:None)
    state=SimpleNamespace(build_payload=lambda project:{'version':1,'next_n':2,'tag':'new'})
    manager=ProjectManager(app,state);manager.current_project=project
    # Se conserva la función UI: un fallo de guardado no debe disparar un diálogo Tk.
    errors=[]
    original=manager_module.HeadlessInteraction.__dict__["showerror"]
    manager_module.HeadlessInteraction.showerror=staticmethod(lambda *args:errors.append(args))
    try:
        assert manager.save_project(), errors
    finally:manager_module.HeadlessInteraction.showerror=original
    assert not app.is_dirty
    saved,recovered,issues=project.storage.load(project.state_path)
    assert saved['tag']=='new' and recovered is None and not issues
    assert read_json(project.config_path)==read_json(project.state_path)
    assert list(Path(project.layout.backups_dir).glob('*.3es'))
    copied=copy_project(project,tmp_path/'Copia')
    assert Path(copied).is_file() and AnalysisRecordStore(str(tmp_path/'Copia')).count()==1
    _,handles=windows_file_sync_rule
    assert all(handle.closed for handle in handles.values())


def test_binary_sync_failure_keeps_previous_file(tmp_path,monkeypatch):
    target=tmp_path/'file.zip';target.write_bytes(b'previous complete archive')
    def fail(descriptor):raise OSError(errno.EIO,'simulated disk failure')
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises(OSError):
        with atomic_output(target) as temporary:Path(temporary).write_bytes(b'new archive')
    assert target.read_bytes()==b'previous complete archive'
    assert not list(tmp_path.glob('.sombra-write-*'))


def test_sqlite_sync_failure_does_not_publish_new_project(tmp_path,monkeypatch):
    import services.project_storage as storage
    project=Project(str(tmp_path/'Plaza'));project.ensure_structure()
    AnalysisRecordStore(project.root_path).upsert({'analysis_id':'tree1','n':1})
    project.storage.commit(project.state_path,{'version':1,'tag':'old'})
    before=Path(project.state_path).read_bytes();database=Path(project.layout.analysis_db).read_bytes()
    def fail(path):raise OSError(errno.EIO,'simulated disk failure')
    # El backup debe sincronizar correctamente antes de publicar un journal.
    monkeypatch.setattr(storage,'fsync_file',fail,raising=False)
    with pytest.raises(OSError):project.storage.commit(project.state_path,{'version':1,'tag':'new'})
    assert Path(project.state_path).read_bytes()==before
    assert Path(project.layout.analysis_db).read_bytes()==database
    assert not Path(project.storage.journal).exists()
