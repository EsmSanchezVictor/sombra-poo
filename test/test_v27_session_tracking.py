import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database_manager import DatabaseManager


def test_session_records_user_and_multiple_projects(tmp_path):
    db_path = tmp_path / "users.db"
    db = DatabaseManager(str(db_path))
    try:
        assert db.add_user(
            "vale", "clave-segura", 0, "Vale", "C", "", "", "", "", "", ""
        )
        session_id = db.start_session("vale")
        assert session_id > 0

        first = db.start_project_work(
            session_id,
            "Proyecto A",
            project_root=str(tmp_path / "Proyecto A"),
            project_state_path=str(tmp_path / "Proyecto A" / "Proyecto A.sombra"),
            action="created",
        )
        assert first > 0

        second = db.start_project_work(
            session_id,
            "Proyecto B",
            project_root=str(tmp_path / "Proyecto B"),
            project_state_path=str(tmp_path / "Proyecto B" / "Proyecto B.sombra"),
            action="opened",
        )
        assert second > first

        db.touch_session(session_id)
        db.end_session(session_id)

        history = db.fetch_session_history(limit=20)
        rows = [row for row in history if row[0] == session_id]
        assert len(rows) == 2
        names = {row[7] for row in rows}
        assert names == {"Proyecto A", "Proyecto B"}
        assert all(row[3] for row in rows)  # login_at
        assert all(row[4] for row in rows)  # logout_at
        assert all(row[11] for row in rows)  # project started_at
        assert all(row[12] for row in rows)  # project ended_at
    finally:
        db.close()


def test_session_without_project_is_kept(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        db.add_user("solo", "clave", 0, "", "", "", "", "", "", "", "")
        session_id = db.start_session("solo")
        db.end_session(session_id)
        row = next(row for row in db.fetch_session_history() if row[0] == session_id)
        assert row[2] == "solo"
        assert row[7] is None  # project_name from LEFT JOIN
    finally:
        db.close()


def test_history_survives_user_deletion(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        db.add_user("temporal", "clave", 0, "", "", "", "", "", "", "", "")
        user = db.get_user("temporal")
        session_id = db.start_session("temporal")
        db.start_project_work(session_id, "Proyecto Histórico")
        db.end_session(session_id)
        db.delete_user(user[0])

        row = next(row for row in db.fetch_session_history() if row[0] == session_id)
        assert row[1] is None  # user_id borrado por ON DELETE SET NULL
        assert row[2] == "temporal"  # snapshot preserva quién fue
        assert row[7] == "Proyecto Histórico"
    finally:
        db.close()
