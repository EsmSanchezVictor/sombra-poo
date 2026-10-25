import json
import os
import sqlite3
import stat
import zipfile
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import pytest

from core.safe_io import atomic_write_json
from core.safe_paths import safe_component, contained_path, sanitize_payload
from core.project_archive import validate_archive, extract_validated_archive, ArchiveLimits
from core.project_manager import ProjectManager
from core.project_layout import ProjectLayout
from services.analysis_record_store import AnalysisRecordStore


@pytest.mark.parametrize("name", ["..", "../escape", "/absoluta", "C:\\escape", "a\\b", "a/b",
    "CON", "NUL.txt", "lpt1", "nombre.", "nombre ", "a:b", "", "a\x00b"])
def test_names_reject_paths_and_windows_reserved(name):
    with pytest.raises(ValueError):
        safe_component(name)


def test_names_keep_accents_and_spaces():
    assert safe_component("Plaza Paraná 2026") == "Plaza Paraná 2026"


@pytest.mark.parametrize("aid", ["../escape", "/tmp/escape", "a/b", "C:\\datos", "CON", "", "a.b"])
def test_analysis_id_cannot_create_folders_outside_project(tmp_path, aid):
    layout = ProjectLayout(str(tmp_path / "proyecto"))
    with pytest.raises(ValueError):
        layout.element_paths(aid)
    assert not (tmp_path / "proyecto").exists()


def test_symlink_is_not_a_contained_reference(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "alias").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        contained_path(root, "alias/file.txt")


def test_layout_rejects_external_symlink_before_writing(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "escena").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        ProjectLayout(str(root)).ensure()
    assert list(outside.iterdir()) == []


def test_json_fsync_failure_keeps_old_file(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"
    atomic_write_json(path, {"old": True})
    def fail(*args):
        raise OSError("fallo simulado fsync")
    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError):
        atomic_write_json(path, {"new": True})
    assert json.loads(path.read_text()) == {"old": True}
    assert len(list(tmp_path.iterdir())) == 1


def test_import_extraction_failure_leaves_no_final_project(tmp_path, monkeypatch):
    archive = package(tmp_path / "broken.3es", [("plaza.sombra", state())])
    def broken(archive, destination):
        Path(destination, "parcial.txt").write_text("contenido")
        raise OSError("fallo simulado al extraer")
    monkeypatch.setattr("core.project_manager.extract_validated_archive", broken)
    with pytest.raises(OSError):
        manager(tmp_path).import_archive(archive)
    assert list((tmp_path / "projects").iterdir()) == []


def test_json_failure_keeps_previous_state_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"
    atomic_write_json(path, {"estado": "original"})
    original = path.read_bytes()
    def fail(*args):
        raise OSError("fallo simulado de reemplazo")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        atomic_write_json(path, {"estado": "nuevo"})
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_json_serialization_failure_keeps_previous_state(tmp_path):
    path = tmp_path / "estado.json"
    atomic_write_json(path, {"original": True})
    with pytest.raises(TypeError):
        atomic_write_json(path, {"no_serializable": object()})
    assert json.loads(path.read_text()) == {"original": True}
    assert len(list(tmp_path.iterdir())) == 1


def manager(tmp_path):
    result = ProjectManager(SimpleNamespace())
    result.projects_root = str(tmp_path / "projects")
    return result


def package(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return path


def state(name="Plaza Paraná", **changes):
    payload = {"version": 1, "meta": {"name": name}, "paths": {}, "snapshots": []}
    payload.update(changes)
    return json.dumps(payload)


@pytest.mark.parametrize("bad_member", ["../escape", "C:/escape", "/escape", "a/../../escape", "a\\..\\escape", "NUL.txt"])
def test_import_rejects_unsafe_members_without_partial_project(tmp_path, bad_member):
    archive = package(tmp_path / "test.3es", [("plaza.sombra", state()), (bad_member, "bad")])
    mgr = manager(tmp_path)
    with pytest.raises(ValueError):
        mgr.import_archive(archive)
    assert list((tmp_path / "projects").iterdir()) == []


def test_archive_rejects_symlink(tmp_path):
    path = tmp_path / "links.3es"
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("alias")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "../fuera")
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(ValueError):
            validate_archive(archive)


@pytest.mark.parametrize("entries", [[("A.txt", "a"), ("a.txt", "b")], [("a", "f"), ("a/b", "b")]])
def test_archive_rejects_windows_collisions(tmp_path, entries):
    path = package(tmp_path / "ambiguous.3es", entries)
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(ValueError):
            validate_archive(archive)


@pytest.mark.parametrize("limits", [replace(ArchiveLimits(), max_members=0),
    replace(ArchiveLimits(), max_member_bytes=5), replace(ArchiveLimits(), max_total_bytes=5),
    replace(ArchiveLimits(), max_ratio=1.0)])
def test_archive_limits_are_enforced_before_extraction(tmp_path, limits):
    path = package(tmp_path / "limits.3es", [("data.txt", "a" * 1000)])
    dest = tmp_path / "dest"
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(ValueError):
            extract_validated_archive(archive, dest, limits)
    assert not dest.exists()


def test_import_valid_flat_and_wrapped_legacy_packages(tmp_path):
    mgr = manager(tmp_path)
    for prefix in ("", "envoltorio/"):
        archive = package(tmp_path / "valid.3es", [(prefix + "config/project.json", state()),
            (prefix + "entradas/imagenes/foto.txt", "foto")])
        path = mgr.import_archive(archive)
        assert json.loads(Path(path).read_text(encoding="utf-8"))["version"] == 1
        assert os.path.isfile(path)
    assert sorted(p.name for p in (tmp_path / "projects").iterdir()) == ["Plaza_Paraná", "Plaza_Paraná_v2"]


@pytest.mark.parametrize("path", ["../fuera.png", "/tmp/fuera.png", "C:\\fuera.png"])
def test_import_rejects_external_payload_references(tmp_path, path):
    archive = package(tmp_path / "bad.3es", [("plaza.sombra", state(paths={"current_image": path}))])
    mgr = manager(tmp_path)
    with pytest.raises(ValueError):
        mgr.import_archive(archive)
    assert list((tmp_path / "projects").iterdir()) == []


def test_import_rejects_external_references_in_sqlite(tmp_path):
    source = tmp_path / "source"
    store = AnalysisRecordStore(str(source))
    row = store.upsert({"n": 1, "label": "seguro"})
    conn = sqlite3.connect(store.db_path)
    conn.execute("UPDATE analysis_records SET payload_json=?", (json.dumps({**row, "image": "../externa.png"}),))
    conn.commit()
    conn.close()
    archive = tmp_path / "sqlite.3es"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("plaza.sombra", state())
        z.write(store.db_path, "analisis/analisis.sqlite3")
    mgr = manager(tmp_path)
    with pytest.raises(ValueError):
        mgr.import_archive(archive)
    assert list((tmp_path / "projects").iterdir()) == []


def test_local_legacy_reference_inside_root_keeps_compatibility(tmp_path):
    path = tmp_path / "imagen.png"
    path.write_bytes(b"contenido")
    result = sanitize_payload(str(tmp_path), {"paths": {"current_image": str(path)}})
    assert result["paths"]["current_image"] == "imagen.png"
    result = sanitize_payload(str(tmp_path), {"paths": {"current_image": "../externa.png"}})
    assert result["paths"]["current_image"] is None
