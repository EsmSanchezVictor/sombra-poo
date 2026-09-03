import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile

from core.project import Project
from core.project_layout import LAYOUT_VERSION
from services.analysis_record_store import AnalysisRecordStore


def test_v19_project_layout_is_created_with_stable_paths(tmp_path):
    project = Project(str(tmp_path / "demo"))
    project.ensure_structure()
    layout = project.layout
    expected_dirs = [
        layout.config_dir, layout.images_dir, layout.meteorology_dir,
        layout.validation_inputs_dir, layout.scene_dir, layout.analysis_dir,
        layout.analysis_elements_dir, layout.dataset_dir,
        layout.project_results_dir, layout.validation_results_dir,
        layout.reports_dir, layout.backups_dir,
    ]
    assert all(Path(p).is_dir() for p in expected_dirs)
    manifest = json.loads(Path(layout.structure_manifest).read_text(encoding="utf-8"))
    assert manifest["layout_version"] == LAYOUT_VERSION
    assert manifest["stable_files"]["edicion"] == "escena/edicion.xlsx"
    assert manifest["folders"]["analisis_elementos"] == "analisis/elementos/<analysis_id>"


def test_v18_basic_folders_migrate_without_data_loss(tmp_path):
    root = tmp_path / "legacy"
    (root / "imagenes").mkdir(parents=True)
    (root / "meteorologia").mkdir()
    (root / "datos").mkdir()
    (root / "imagenes" / "arbol.jpg").write_bytes(b"img")
    (root / "meteorologia" / "met.csv").write_text("timestamp,ghi\n", encoding="utf-8")
    # Crear una DB válida en la ruta antigua y luego migrarla.
    old_store = AnalysisRecordStore(str(root))
    # El constructor v19 crea la DB nueva, así que simulamos estrictamente una v18.
    Path(old_store.db_path).unlink()
    old_db = root / "datos" / "analisis.sqlite3"
    old_db.parent.mkdir(parents=True, exist_ok=True)
    old_db.write_bytes(b"legacy-db")

    project = Project(str(root))
    project.ensure_structure()
    assert (Path(project.layout.images_dir) / "arbol.jpg").exists()
    assert (Path(project.layout.meteorology_dir) / "met.csv").exists()
    assert Path(project.layout.analysis_db).read_bytes() == b"legacy-db"
    assert not (root / "imagenes").exists()
    assert not (root / "meteorologia").exists()


def test_analysis_artifacts_are_partitioned_by_analysis_id(tmp_path):
    project = Project(str(tmp_path / "p"))
    project.ensure_structure()
    aid = "abc-123"
    paths = project.layout.element_paths(aid)
    assert Path(paths["matrix"]).parts[-3:] == ("abc-123", "areas", "matriz_calculo.xlsx")
    assert Path(paths["curve"]).parent.name == "termico"
    assert Path(paths["histogram"]).parent.name == "sombra"
    assert Path(paths["dataset_mask"]).parent.name == "areas"


def test_guardar_respaldo_uses_internal_backups_without_dialog(tmp_path, monkeypatch):
    # Prueba _create_backup aislada: la copia local no anida respaldos previos.
    from core.project_manager import ProjectManager

    root = tmp_path / "p"
    project = Project(str(root))
    project.ensure_structure()
    Path(project.state_path).write_text('{"version":1}', encoding="utf-8")
    nested_old = Path(project.layout.backups_dir) / "old.3es"
    nested_old.write_bytes(b"old")
    app = SimpleNamespace(settings={}, root=None)
    manager = ProjectManager(app, app_state=None)
    manager.current_project = project
    out = manager._create_backup()
    assert out and Path(out).exists()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert all(not name.startswith("respaldos/") for name in names)


def test_legacy_scene_folders_are_archived_after_consolidation(tmp_path):
    from core.project_manager import ProjectManager

    root = tmp_path / "p"
    (root / "Planos").mkdir(parents=True)
    (root / "modelos").mkdir()
    (root / "Planos" / "viejo.xlsx").write_bytes(b"edit")
    (root / "modelos" / "viejo.xlsx").write_bytes(b"model")
    project = Project(str(root))
    project.ensure_structure()
    app = SimpleNamespace(settings={})
    manager = ProjectManager(app, app_state=None)
    payload = {"paths": {}}
    out = manager._prepare_payload_for_layout(project, payload)
    assert Path(project.layout.edit_excel).read_bytes() == b"edit"
    assert Path(project.layout.model_excel).read_bytes() == b"model"
    assert not (root / "Planos").exists()
    assert not (root / "modelos").exists()
    assert (root / "_legacy_v18" / "Planos" / "viejo.xlsx").exists()
    assert out["paths"]["edit_excel"] == os.path.join("escena", "edicion.xlsx")
    assert out["paths"]["model_excel"] == os.path.join("escena", "modelo.xlsx")


def test_inventory_manifest_lists_live_files_but_not_backups(tmp_path):
    project = Project(str(tmp_path / "inventory"))
    project.ensure_structure()
    Path(project.layout.images_dir, "tree.jpg").write_bytes(b"abc")
    Path(project.layout.backups_dir, "old.3es").write_bytes(b"backup")
    project.layout.write_inventory()
    payload = json.loads(Path(project.layout.inventory_manifest).read_text(encoding="utf-8"))
    paths = {item["path"] for item in payload["files"]}
    assert "entradas/imagenes/tree.jpg" in paths
    assert all(not p.startswith("respaldos/") for p in paths)


def test_from_state_or_legacy_path_normalizes_to_canonical_config(tmp_path):
    root = tmp_path / "canon"
    (root / "config").mkdir(parents=True)
    state = root / "canon.sombra"
    legacy = root / "config" / "estado.json"
    state.write_text('{"version": 1}', encoding="utf-8")
    legacy.write_text('{"version": 1}', encoding="utf-8")

    from_state = Project.from_config_path(str(state))
    from_legacy = Project.from_config_path(str(legacy))

    expected_config = root / "config" / "project.json"
    assert Path(from_state.config_path) == expected_config
    assert Path(from_legacy.config_path) == expected_config
    assert Path(from_state.state_path) == state
    assert Path(from_legacy.state_path) == state
