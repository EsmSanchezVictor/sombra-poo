import json
from pathlib import Path

from services.analysis_record_store import AnalysisRecordStore


def test_analysis_store_upsert_does_not_duplicate(tmp_path):
    store = AnalysisRecordStore(str(tmp_path))
    aid = store.new_analysis_id()
    first = {
        "analysis_id": aid,
        "n": 1,
        "label": "arbol_1",
        "image": "imagenes/arbol_1.jpg",
        "curve": "curvas/Celemento1.png",
        "cobertura_sombra": 45.0,
        "atenuacion_sombra": 60.0,
        "transmitancia_efectiva": 0.61,
    }
    store.upsert(first, complete=True)
    second = dict(first, cobertura_sombra=47.5)
    store.upsert(second, complete=True)

    rows = store.list_entries()
    assert len(rows) == 1
    assert rows[0]["analysis_id"] == aid
    assert rows[0]["cobertura_sombra"] == 47.5


def test_legacy_migration_skips_provisional_entries(tmp_path):
    store = AnalysisRecordStore(str(tmp_path))
    legacy = [
        {"n": 1, "label": "a", "image": "imagenes/a.jpg", "provisional": True},
        {"n": 2, "label": "b", "image": "imagenes/b.jpg", "curve": "curvas/b.png"},
    ]
    store.migrate_legacy_snapshots(legacy)
    rows = store.list_entries()
    assert len(rows) == 1
    assert rows[0]["label"] == "b"
    assert rows[0].get("analysis_id")


def test_legacy_migration_is_idempotent(tmp_path):
    store = AnalysisRecordStore(str(tmp_path))
    legacy = [{"n": 3, "timestamp": "2026-01-01T10:00:00", "label": "x", "image": "imagenes/x.jpg"}]
    store.migrate_legacy_snapshots(legacy)
    store.migrate_legacy_snapshots(legacy)
    assert store.count() == 1


def test_database_lives_inside_project_and_is_portable(tmp_path):
    store = AnalysisRecordStore(str(tmp_path))
    assert Path(store.db_path) == tmp_path / "analisis" / "analisis.sqlite3"
    assert Path(store.db_path).exists()


def test_carousel_click_is_read_only_in_source():
    source = (Path(__file__).resolve().parents[1] / "ui" / "app_ui.py").read_text(encoding="utf-8")
    start = source.index("    def _carrusel_seleccionar")
    end = source.index("    def _carrusel_desplazar", start)
    body = source[start:end]
    assert "cargar_snapshot(index)" in body
    assert "mostrar_curvas_nivel" not in body
    assert ".append(" not in body


def test_migration_collapses_known_v16_click_duplicate(tmp_path):
    store = AnalysisRecordStore(str(tmp_path))
    shared = {
        "poly_calculo": {"tipo": "rectangulo", "puntos": [1, 2, 3, 4]},
        "poly_referencia": {"tipo": "rectangulo", "puntos": [5, 6, 2, 2]},
        "cobertura_sombra": 42.0,
        "atenuacion_sombra": 55.0,
        "transmitancia_efectiva": 0.65,
        "tmrt_sombra": 48.0,
        "delta_tmrt": 12.0,
    }
    legacy = [
        {"n": 1, "label": "jacaranda", "image": "imagenes/jacaranda.jpg", **shared},
        {"n": 2, "label": "elemento1", "image": "imagenes/elemento1.png", **shared},
    ]
    store.migrate_legacy_snapshots(legacy)
    rows = store.list_entries()
    assert len(rows) == 1
    assert rows[0]["label"] == "jacaranda"


def test_snapshot_capture_upserts_same_tree_and_persists_required_payload(tmp_path):
    import os
    from types import SimpleNamespace
    import numpy as np
    from PIL import Image
    from core.project import Project
    from services.snapshot_service import SnapshotService

    project = Project(str(tmp_path / "proyecto"))
    project.ensure_structure()
    aid = AnalysisRecordStore.new_analysis_id()
    image = Path(project.layout.images_dir) / "arbol.jpg"
    paths = project.layout.element_paths(aid)
    curve = Path(paths["curve"])
    hist = Path(paths["histogram"])
    Image.new("RGB", (20, 10), "white").save(image)
    Image.new("RGB", (20, 10), "white").save(curve)
    Image.new("RGB", (20, 10), "white").save(hist)

    selector = SimpleNamespace(
        area_seleccionada=np.arange(16, dtype=float).reshape(4, 4),
        area_seleccionada_mask=np.ones((4, 4), dtype=bool),
        mask_calculo_full=np.ones((10, 20), dtype=bool),
        area_referencia=np.full((3, 3), 180.0),
        area_referencia_mask=np.ones((3, 3), dtype=bool),
        mask_referencia_full=np.ones((10, 20), dtype=bool),
        shape_patch_calculo=None,
        shape_patch_referencia=None,
    )

    store = AnalysisRecordStore(project.root_path)
    app = SimpleNamespace(
        current_analysis_id=aid,
        current_image_path=str(image), last_image_path=str(image), current_image_stem="arbol",
        last_curve_path=str(curve), last_histogram_path=str(hist),
        last_shadow_classification_path=None,
        shape_selector=selector,
        shadow_photo_analysis={
            "algorithm": "photo-shadow-v2-coverage-attenuation",
            "coverage_pct": 40.0, "attenuation_pct": 50.0,
            "shadow_transmittance": 0.5, "effective_transmittance": 0.8,
            "effective_attenuation_pct": 20.0, "threshold_ratio": 0.7,
            "legacy_shadow_index_pct": 20.0,
            "shadow_mask": np.zeros((4,4)),
            "local_transmittance_map": np.full((4,4), 0.8),
            "local_attenuation_map": np.full((4,4), 20.0),
            "ratio_map": np.full((4,4), 0.8),
        },
        cobertura_sombra=40.0, atenuacion_sombra=50.0, ref_gray_mean=180.0,
        tmrt_hover_data={"tmrt": np.full((4,4), 45.0), "air_temp": 25.0},
        tmrt_result=None, last_meteorology_data=None, settings={},
        surface_model_mode=SimpleNamespace(get=lambda: "standard"),
        radiation_source_mode=SimpleNamespace(get=lambda: "clear_sky"),
        last_model_excel_path=None, last_edit_excel_path=None,
        snapshots=[],
        _get_analysis_store=lambda: store,
        poblar_lista_snapshots=lambda selected_analysis_id=None: None,
    )
    # Labels recuperables sin Tk real.
    app.lbl_dimensiones_calculo = SimpleNamespace(cget=lambda key: "Área de Cálculo: 20x10")
    app.lbl_dimensiones_referencia = SimpleNamespace(cget=lambda key: "Área de Referencia: 10x10")
    pm = SimpleNamespace(current_project=project, save_project=lambda: True)
    service = SnapshotService(app, pm)

    first = service.capture_analysis_record(auto=True)
    assert first is not None
    assert store.count() == 1
    assert first["image"] == os.path.join("entradas", "imagenes", "arbol.jpg")
    assert first["promedio_gris"] == 180.0
    assert first["cobertura_sombra"] == 40.0
    assert first["atenuacion_sombra"] == 50.0
    assert first["transmitancia_efectiva"] == 0.8
    assert first["calc_data"] and first["reference_data"] and first["tmrt_data"]

    app.cobertura_sombra = 42.0
    app.shadow_photo_analysis["coverage_pct"] = 42.0
    second = service.capture_analysis_record(auto=True)
    assert second["analysis_id"] == first["analysis_id"]
    assert store.count() == 1
    assert store.list_entries()[0]["cobertura_sombra"] == 42.0
