"""Real JSON/NPZ/SQLite/archive flows; widgets are replaced by stateful test doubles."""
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pytest
from PIL import Image
from core.app_state import AppState
from core.photo_exclusions import decode_state
from core.project import Project
from services.photo_selection import analyze_selection
from image_processor import ImageProcessor
from ui.photo_analysis import PhotoAnalysisMixin
from ui.snapshot_restoration import SnapshotRestorationMixin
from test.test_stage4_headless import state_app


class Label:
    def __init__(self):self.options={};self.destroyed=False
    def config(self,**kwargs):self.options.update(kwargs)
    configure=config
    def cget(self,key):return self.options.get(key,'')
    def destroy(self):self.destroyed=True


class PhotoApp(PhotoAnalysisMixin,SnapshotRestorationMixin,SimpleNamespace):pass


def app_fixture(project):
    app=PhotoApp(**vars(state_app(project)))
    area=np.tile([40,40,200,200],(4,1)).astype(np.uint8);reference=np.full((2,2),200,dtype=np.uint8)
    app.image_processor=ImageProcessor()
    app.shape_selector=SimpleNamespace(area_seleccionada=area,area_referencia=reference,
        area_seleccionada_mask=np.ones((4,4),dtype=bool),area_referencia_mask=np.ones((2,2),dtype=bool),
        mask_calculo_full=np.ones((8,8),dtype=bool),mask_referencia_full=np.ones((8,8),dtype=bool),
        shape_patch_calculo=None,shape_patch_referencia=None)
    app.shadow_photo_analysis=analyze_selection(app.image_processor,area,reference)
    app.photo_exclusions_pending=False;app.dirty_count=0
    app.mark_dirty=lambda:setattr(app,'dirty_count',app.dirty_count+1)
    app._clear_temperature_graph=lambda:None
    app.lbl_porcentaje_sombra=Label();app.lbl_atenuacion_sombra=Label();app.lbl_transmitancia_sombra=Label()
    app.curve_button=Label();app.save_dataset_button=Label();app.photo_exclusion_button=Label()
    app.last_temp_graph_path=None;app.last_shadow_classification_path=None
    app.current_analysis_id='tree1';app.settings={};app.last_meteorology_data=None;app.ref_gray_mean=None
    app.poblar_lista_snapshots=lambda **kwargs:None
    return app


def test_edit_invalidates_old_results_is_idempotent_and_invalid_masks_do_not_mutate_state(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    old=app.shadow_photo_analysis;app.tmrt_result={'old':42};app.tmrt_map=np.ones((4,4));app.last_curve_path='old.png'
    with pytest.raises(ValueError):app._apply_photo_exclusions(np.ones((4,4)))
    assert app.shadow_photo_analysis is old and app.last_curve_path=='old.png'
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True
    assert app._apply_photo_exclusions(mask)
    assert app.tmrt_result is None and app.tmrt_map is None and app.last_curve_path is None
    assert app.photo_exclusions_pending and app.save_dataset_button.options['state']=='disabled'
    assert app.dirty_count==1
    assert not app._apply_photo_exclusions(mask) and app.dirty_count==1


def test_pending_edit_survives_project_json_and_archive_import(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    payload=AppState(app).build_payload(project)
    packed=payload['last_results_meta']['photo_exclusions'];assert decode_state(packed)[2]
    project.storage.commit(project.state_path,payload)
    archive=tmp_path/'Project.3es';project.storage.export(archive)
    from core.project_manager import ProjectManager
    manager=ProjectManager(SimpleNamespace(settings={}));manager.projects_root=str(tmp_path/'imported')
    state_path=manager.import_archive(str(archive));imported=Project.from_config_path(state_path)
    loaded,_,_=imported.storage.load(state_path)
    restored=app_fixture(imported);AppState(restored).apply_payload(loaded)
    assert restored.photo_exclusions_pending
    assert np.array_equal(restored.shadow_photo_analysis['exclusion_mask'],mask)
    assert restored.cobertura_sombra==pytest.approx(100/3)


def test_clearing_existing_exclusions_remains_a_persistable_pending_operation(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    app.photo_exclusions_pending=False
    app._apply_photo_exclusions(np.zeros((4,4),dtype=bool))
    payload=AppState(app).build_payload(project);state=payload['last_results_meta']['photo_exclusions']
    restored_mask,_,pending=decode_state(state)
    assert pending and not restored_mask.any()
    assert app.shadow_photo_analysis['exclusion_mask'] is None


def test_npz_sqlite_roundtrip_restores_corrections_and_signature(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    paths=project.layout.element_paths(app.current_analysis_id)
    for name in ('curve','histogram'):Path(paths[name]).write_bytes(b'fixture-artifact')
    image=Path(project.layout.images_dir)/'photo.png';Image.fromarray(np.full((8,8,3),100,dtype=np.uint8)).save(image)
    app.current_image_path=str(image);app.last_image_path=str(image);app.current_image_stem='photo'
    app.last_curve_path=paths['curve'];app.last_histogram_path=paths['histogram'];app.ref_gray_mean=200.
    app.tmrt_hover_data={'tmrt':np.full((4,4),30.),'air_temp':25.}
    from services.snapshot_service import SnapshotService
    service=SnapshotService(app,app.project_manager)
    entry=service.capture_analysis_record(auto=True)
    assert entry['photo_excluded_pixels']==4 and entry['photo_input_signature']
    from services.analysis_record_store import AnalysisRecordStore
    stored=AnalysisRecordStore(project.root_path).get(entry['analysis_id'])
    restored=app_fixture(project)
    restored.shadow_photo_analysis=restored._load_photo_analysis_bundle(paths['photo_analysis_data'],stored)
    computed=restored._analizar_seleccion_fotografica()
    assert np.array_equal(computed['exclusion_mask'],mask)
    assert computed['coverage_pct']==pytest.approx(100/3)


def test_editor_cancel_and_undo_do_not_modify_applied_mask():
    from ui.photo_exclusion_editor import PhotoExclusionEditor
    editor=PhotoExclusionEditor.__new__(PhotoExclusionEditor)
    original=np.ones((2,2),dtype=bool);editor.mask=original.copy();editor.history=[];editor.draw=lambda:None
    editor.clear();assert not editor.mask.any();editor.undo();assert editor.mask.all()
    editor.photo=object();editor.top=Label();editor.close()
    assert editor.top.destroyed and editor.photo is None and original.all()


def test_snapshot_reset_does_not_erase_restored_detector_metadata(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    app.snapshots=[dict(analysis_id='tree1',complete=True,deteccion_candidatos={'coverage_fraction':.3})]
    app.shape_selector.area_seleccionada=None;app.shape_selector.area_referencia=None
    app._reset_panel2_for_new_image=lambda:setattr(app,'shadow_detection_meta',None)
    from test.test_stage4_headless import Var
    app.matriz_size=Var(128);app.panel2_advanced_mode=Var(False)
    app._toggle_panel2_advanced=lambda:None;app.ax1=None;app.img_rgb=None
    app._carrusel_marcar=lambda i:None
    app.cargar_snapshot(0)
    assert app.shadow_detection_meta=={'coverage_fraction':.3} and app.shadow_coverage_fraction==.3


def test_editor_widget_flow_maps_a_drag_applies_a_copy_and_rejects_an_empty_domain(monkeypatch):
    import ui.photo_exclusion_editor as module
    class Widget:
        def __init__(self,*args,**kwargs):self.options=kwargs;self.destroyed=False
        def title(self,*args):pass
        def pack(self,**kwargs):pass
        def bind(self,*args):pass
        def protocol(self,*args):pass
        def config(self,**kwargs):self.options.update(kwargs)
        def delete(self,*args):pass
        def create_image(self,*args,**kwargs):return 1
        def create_rectangle(self,*args,**kwargs):return 2
        def destroy(self):self.destroyed=True
    monkeypatch.setattr(module.tk,'Toplevel',Widget);monkeypatch.setattr(module.tk,'Canvas',Widget)
    for name in ('Label','Button','Frame'):monkeypatch.setattr(module.ttk,name,Widget)
    monkeypatch.setattr(module,'prepare_dialog',lambda *a,**k:None)
    monkeypatch.setattr(module.ImageTk,'PhotoImage',lambda image:object())
    applied=[];area=np.full((4,4),100);valid=np.ones((4,4),dtype=bool)
    editor=module.PhotoExclusionEditor(None,area,valid,np.zeros((4,4)),lambda mask:applied.append(mask))
    editor.start(SimpleNamespace(x=0,y=0));editor.finish(SimpleNamespace(x=editor.size[0]/4,y=editor.size[1]))
    editor.apply()
    assert len(applied)==1 and applied[0][:,0].all() and not applied[0][:,1:].any()
    assert editor.top.destroyed and editor.photo is None
    blocked=module.PhotoExclusionEditor(None,area,valid,valid.copy(),lambda mask:applied.append(mask))
    blocked.apply()
    assert not blocked.top.destroyed and len(applied)==1 and blocked.error.options['text']
    blocked.close()


def test_only_corrected_projects_require_new_schema_and_old_readers_refuse_them(tmp_path,monkeypatch):
    from core import project_schema
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    assert AppState(app).build_payload(project)['state_schema_version']==2
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    payload=AppState(app).build_payload(project)
    assert payload['state_schema_version']==3
    project.storage.commit(project.state_path,payload)
    monkeypatch.setattr(project_schema,'STATE_SCHEMA_VERSION',2)
    with pytest.raises(project_schema.UnsupportedSchemaError):project.storage.load(project.state_path)
    monkeypatch.setattr(project_schema,'STATE_SCHEMA_VERSION',3)
    app._apply_photo_exclusions(np.zeros((4,4),dtype=bool));app.photo_exclusions_pending=False
    assert AppState(app).build_payload(project)['state_schema_version']==3


def test_pending_correction_reopens_the_selected_element_instead_of_the_last_one(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    app.snapshots=[dict(analysis_id='tree1'),dict(analysis_id='tree2')]
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    payload=AppState(app).build_payload(project)
    assert payload['ui']['active_analysis_id']=='tree1'
    restored=app_fixture(project)
    restored.current_analysis_id='tree2'
    restored._recargar_analisis_desde_base=lambda **kwargs:None
    restored._restore_excel_files=lambda:None
    loaded=[]
    def load(index):
        loaded.append(index);restored.current_analysis_id=restored.snapshots[index]['analysis_id']
    restored.cargar_snapshot=load
    # Use the real orchestration; its widget operations are separately exercised.
    restored.restore_project_artifacts=lambda:SnapshotRestorationMixin.restore_project_artifacts(restored)
    AppState(restored).apply_payload(payload)
    assert loaded==[0] and restored.current_analysis_id=='tree1'
    assert restored.photo_exclusions_pending and np.array_equal(restored.shadow_photo_analysis['exclusion_mask'],mask)


def test_a_missing_selected_element_cannot_receive_another_elements_pending_mask(tmp_path):
    project=Project(str(tmp_path/'P'));project.ensure_structure();app=app_fixture(project)
    mask=np.zeros((4,4),dtype=bool);mask[:,0]=True;app._apply_photo_exclusions(mask)
    payload=AppState(app).build_payload(project)
    restored=app_fixture(project);restored.current_analysis_id='other'
    with pytest.raises(ValueError,match='análisis asociado'):AppState(restored).apply_payload(payload)
