import gc
import sqlite3
import warnings

from database_manager import DatabaseManager
from services.analysis_record_store import AnalysisRecordStore


def test_analysis_record_store_closes_every_short_lived_connection(tmp_path):
    root = tmp_path / "project"
    store = AnalysisRecordStore(str(root))

    for i in range(20):
        entry = store.upsert({"n": i + 1, "label": f"item-{i}"})
        assert store.get(entry["analysis_id"])["label"] == f"item-{i}"
        assert store.count(complete_only=False) == i + 1
        assert len(store.list_entries(complete_only=False)) == i + 1

    # Si alguna sqlite3.Connection quedó abandonada, CPython 3.13+ emite
    # ResourceWarning al recolectarla. Convertimos el warning en fallo.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        gc.collect()
        gc.collect()

    # La base debe seguir libre para otra conexión y escritura inmediata.
    conn = sqlite3.connect(store.db_path, timeout=0.2)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
    finally:
        conn.close()


def test_database_manager_close_is_idempotent(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    db.close()
    db.close()
    assert db.connection is None
    assert db.cursor is None
