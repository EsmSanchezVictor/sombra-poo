"""Integración de recuperación, copias y diagnóstico sin iniciar Tk/VTK en pantalla."""
from pathlib import Path
from types import SimpleNamespace
import json
import logging
import sqlite3
import numpy as np
import pytest
from core.project import Project
from core.safe_io import atomic_write_json
from core.project_schema import UnsupportedSchemaError
from services.project_storage import read_json
from services.analysis_record_store import AnalysisRecordStore
from services.project_copy import copy_project


def create_project(tmp_path):
    project = Project(str(tmp_path/'Plaza'))
    project.ensure_structure()
    store = AnalysisRecordStore(project.root_path)
    store.upsert({'analysis_id':'a1','n':1})
    project.storage.commit(project.state_path, {'version':1,'next_n':2,'tag':'old'})
    return project


def test_commit_does_not_replace_future_recovery_protocol(tmp_path):
    project = create_project(tmp_path)
    before = Path(project.state_path).read_bytes()
    atomic_write_json(project.storage.head, {'protocol_version':99,'transaction_id':'f'*32})
    with pytest.raises(ValueError):
        project.storage.commit(project.state_path, {'version':1,'tag':'new'})
    assert Path(project.state_path).read_bytes() == before


def test_live_future_database_not_treated_as_corruption(tmp_path):
    project = create_project(tmp_path)
    path = Path(project.layout.analysis_db)
    connection = sqlite3.connect(path)
    try:
        connection.execute('PRAGMA user_version=99'); connection.commit()
    finally:
        connection.close()
    before = path.read_bytes()
    with pytest.raises(UnsupportedSchemaError):
        project.storage.load(project.state_path)
    assert path.read_bytes() == before
    assert not (Path(project.storage.home)/'quarantine').exists()


def test_commit_future_sqlite_does_not_publish_new_state(tmp_path):
    project = create_project(tmp_path)
    connection = sqlite3.connect(project.layout.analysis_db)
    try:
        connection.execute('PRAGMA user_version=99'); connection.commit()
    finally:
        connection.close()
    before = Path(project.state_path).read_bytes()
    database = Path(project.layout.analysis_db).read_bytes()
    with pytest.raises(UnsupportedSchemaError):
        project.storage.commit(project.state_path, {'version':1,'tag':'new'})
    assert Path(project.state_path).read_bytes() == before
    assert Path(project.layout.analysis_db).read_bytes() == database


@pytest.mark.parametrize('directory',[False,True])
def test_copy_rejects_external_symlinks(tmp_path,directory):
    project = create_project(tmp_path)
    outside = tmp_path/'externo'
    if directory:
        outside.mkdir(); (outside/'privado.txt').write_bytes(b'private')
    else:
        outside.write_bytes(b'private')
    try:
        (Path(project.root_path)/'enlace').symlink_to(outside,target_is_directory=directory)
    except OSError as exc:
        pytest.skip(f'El sistema no permite crear symlinks en este entorno: {exc}')
    destination = tmp_path/'Copia'
    with pytest.raises(ValueError):copy_project(project,destination)
    assert not destination.exists()


def test_load_rejects_state_outside_project(tmp_path):
    project = Project(str(tmp_path/'Empty')); project.ensure_structure()
    external = tmp_path/'other.json'; atomic_write_json(external, {'version':1})
    with pytest.raises(ValueError):project.storage.load(external)


def test_logging_is_idempotent_rotates_and_closes_handles(tmp_path):
    from core.app_logging import configure_logging
    logger = logging.getLogger('sombra')
    old_level = logger.level
    before = list(logger.handlers)
    try:
        assert configure_logging(tmp_path) is configure_logging(tmp_path)
        handlers = [h for h in logger.handlers if h not in before]
        assert len(handlers) == 1
        handler = handlers[0]; handler.maxBytes = 160
        logger.getChild('storage').info('Primer guardado confirmado')
        logger.getChild('storage').info('Segundo guardado confirmado con registro más largo para rotación')
        handler.flush()
        text = ''.join(f.read_text() for f in tmp_path.glob('sombra.log*'))
        assert 'guardado confirmado' in text and (tmp_path/'sombra.log.1').exists()
    finally:
        for handler in list(logger.handlers):
            if handler not in before:
                logger.removeHandler(handler); handler.close()
        logger.setLevel(old_level)


def test_tk_callback_handler_reports_and_logs_actual_exception(monkeypatch,caplog):
    from ui.error_handlers import install_tk_error_handler
    from tkinter import messagebox
    shown = []
    monkeypatch.setattr(messagebox,'showerror',lambda *args:shown.append(args))
    root = SimpleNamespace(); install_tk_error_handler(root,logging.getLogger('sombra'))
    try:
        raise RuntimeError('fallo de callback simulado')
    except RuntimeError as exc:
        root.report_callback_exception(type(exc),exc,exc.__traceback__)
    assert shown and 'fallo de callback simulado' in caplog.text


@pytest.mark.parametrize('vtk_error',[None,RuntimeError('motor no disponible')])
def test_extracted_matplotlib_backend_renders_scene_with_agg(monkeypatch,vtk_error):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import ui.scene3d_fallback as backend
    from ui.scene3d import Scene3DData, _render_matplotlib_fallback
    widgets = []; canvases = []
    class Widget:
        def __init__(self,*args,**kwargs): self.options=kwargs; self.destroyed=False; widgets.append(self)
        def pack(self,**kwargs):pass
        def destroy(self):self.destroyed=True
        def update(self):pass
    class Canvas(FigureCanvasAgg):
        def __init__(self,figure,master=None):super().__init__(figure);self.widget=Widget();canvases.append(self)
        def get_tk_widget(self):return self.widget
    monkeypatch.setattr(backend.tk,'Frame',Widget);monkeypatch.setattr(backend.tk,'Label',Widget)
    monkeypatch.setattr(backend,'FigureCanvasTkAgg',Canvas);monkeypatch.setattr(backend,'NavigationToolbar2Tk',Widget)
    x,y = np.meshgrid(np.arange(4.),np.arange(4.)); t = 25.+x+y
    tree=SimpleNamespace(x=1.,y=1.,h=3.,radio_copa=.7,especie='',forma_copa='esferica')
    structures=tuple(SimpleNamespace(tipo=kind,x1=0.,y1=0.,x2=2.,y2=2.,altura=2.) for kind in ('Pared','Galeria','Suelo'))
    scene=Scene3DData(x,y,t,(tree,),structures,'°C','Escena de prueba',45.,90.)
    parent=SimpleNamespace()
    _render_matplotlib_fallback(parent,scene,vtk_error)
    assert len(canvases)==1 and len(canvases[0].figure.axes)==2
    assert canvases[0].figure.axes[0].get_title() == 'Escena de prueba'
    assert any('Matplotlib' in w.options.get('text','') for w in widgets)
    parent._sombra_scene3d_controller.close()
    assert canvases[0].widget.destroyed and not canvases[0].figure.axes


def test_code_and_science_release_labels_current():
    from core.app_version import APP_RELEASE
    from core.model_registry import SCIENTIFIC_RELEASE
    assert APP_RELEASE == 'v35.6-etapa4.3' and SCIENTIFIC_RELEASE == 'v35.6-etapa3.2'


def test_snapshot_copy_failure_preserves_previous_artifact(tmp_path,monkeypatch):
    from services.snapshot_service import SnapshotService
    import shutil
    source=tmp_path/'source.png';source.write_bytes(b'new figure')
    target=tmp_path/'target.png';target.write_bytes(b'old figure')
    def fail(src,dst):Path(dst).write_bytes(b'partial');raise OSError('copy interrupted')
    monkeypatch.setattr(shutil,'copy2',fail)
    with pytest.raises(OSError):SnapshotService(None,None)._copy_if_exists(str(source),str(target))
    assert target.read_bytes()==b'old figure'


def test_input_import_failure_leaves_no_incomplete_input(tmp_path,monkeypatch):
    from core.project_layout import ProjectLayout
    import shutil
    project=ProjectLayout(str(tmp_path/'Project'));project.ensure()
    source=tmp_path/'foto.jpg';source.write_bytes(b'original image')
    def fail(src,dst):Path(dst).write_bytes(b'partial');raise OSError('copy interrupted')
    monkeypatch.setattr(shutil,'copy2',fail)
    with pytest.raises(OSError):project.import_input_file(str(source),project.images_dir)
    assert not list(Path(project.images_dir).iterdir())


@pytest.mark.parametrize('target',['primary','secondary','inventory'])
@pytest.mark.parametrize('operation',['load','commit'])
def test_future_live_json_is_never_overwritten(tmp_path,target,operation):
    project=create_project(tmp_path)
    path=Path(project.state_path if target=='primary' else project.config_path if target=='secondary' else project.layout.inventory_manifest)
    data=read_json(path)
    data['integrity_schema_version' if target=='inventory' else 'state_schema_version']=99
    atomic_write_json(path,data);before=path.read_bytes()
    with pytest.raises(UnsupportedSchemaError):
        if operation=='load':project.storage.load(project.state_path)
        else:project.storage.commit(project.state_path,{'version':1,'tag':'new'})
    assert path.read_bytes()==before


def test_copy_parent_alias_into_original_rejected(tmp_path):
    project=create_project(tmp_path)
    alias=tmp_path/'alias'
    try:alias.symlink_to(project.root_path,target_is_directory=True)
    except OSError as exc:pytest.skip(f'El sistema no permite symlinks en este entorno: {exc}')
    with pytest.raises(ValueError):copy_project(project,alias/'nested')
    assert not (Path(project.root_path)/'nested').exists()
