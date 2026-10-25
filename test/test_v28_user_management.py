import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database_manager import DatabaseManager


def test_management_projection_never_exposes_hash_or_salt(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        assert db.add_user("vale", "clave-segura-2026", 1, "Vale", "Marcó", "123", "v@example.com", "555", "Calle", "10", "Paraná")
        row = db.fetch_users_for_management()[0]
        assert "password_hash" not in row.keys()
        assert "salt" not in row.keys()
        assert row["username"] == "vale"
        assert row["first_name"] == "Vale"
        assert row["last_name"] == "Marcó"
        assert row["is_admin"] == 1
        assert row["dni"] == "123"
    finally:
        db.close()


def test_existing_database_is_migrated_with_status_and_login_fields(tmp_path):
    import sqlite3
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        is_admin INTEGER NOT NULL,
        first_name TEXT,last_name TEXT,dni TEXT,email TEXT,phone TEXT,street TEXT,number TEXT,city TEXT
    )''')
    conn.commit(); conn.close()
    db = DatabaseManager(str(path))
    try:
        cols = {r[1] for r in db.connection.execute("PRAGMA table_info(users)").fetchall()}
        assert {"is_active", "created_at", "updated_at", "last_login"}.issubset(cols)
    finally:
        db.close()


def test_inactive_user_cannot_authenticate(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        db.add_user("u1", "123456789012", 0, "", "", "", "", "", "", "", "")
        row = db.get_user("u1")
        assert db.authenticate("u1", "123456789012")
        ok, err = db.set_user_active(row["id"], False)
        assert ok and err is None
        assert not db.authenticate("u1", "123456789012")
    finally:
        db.close()


def test_last_active_admin_cannot_be_deactivated_or_deleted(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        db.add_user("admin", "123456789012", 1, "", "", "", "", "", "", "", "")
        user = db.get_user("admin")
        ok, _ = db.set_user_active(user["id"], False)
        assert not ok
        ok, _ = db.delete_user_safe(user["id"], actor_user_id=None)
        assert not ok
    finally:
        db.close()


def test_user_management_ui_uses_treeview_and_safe_projection():
    src = (ROOT / "main_app.py").read_text(encoding="utf-8")
    start = src.index("    def open_user_management")
    end = src.index("    def refresh_user_management", start)
    block = src[start:end]
    assert "ttk.Treeview" in block
    assert "fetch_all_users" not in block
    assert "password_hash" not in block
    assert '"Nombre y apellido"' in block
    assert '"Estado"' in block
