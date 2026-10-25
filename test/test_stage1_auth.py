import sqlite3
from pathlib import Path
import pytest
from database_manager import DatabaseManager
from core.auth_policy import INTERNAL_USERNAME, default_users_path

PASSWORD = "Una clave de prueba 2026"


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "users.db")
    yield manager
    manager.close()


def add(manager, name="humano", password=PASSWORD, admin=True):
    return manager.add_user(name, password, admin, "", "", "", "", "", "", "", "")


def legacy_file(path, password="admin", name="admin", with_history=False):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE,
        password TEXT, is_admin INTEGER, first_name TEXT, last_name TEXT,
        dni TEXT, email TEXT, phone TEXT, street TEXT, number TEXT, city TEXT)""")
    conn.execute("INSERT INTO users VALUES (7,?,?,1,'','','','','','','','')", (name, password))
    if with_history:
        conn.execute("""CREATE TABLE user_sessions (id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            username_snapshot TEXT NOT NULL, login_at TEXT NOT NULL, logout_at TEXT,
            last_activity_at TEXT NOT NULL)""")
        conn.execute("INSERT INTO user_sessions VALUES (42,7,?,'2026-01-01',NULL,'2026-01-01')", (name,))
    conn.commit()
    conn.close()


def test_bootstrap_is_required_once_and_internal_is_not_admin(db):
    assert db.needs_initial_admin()
    assert db.get_user("admin") is None
    assert db.count_active_admins() == 0
    assert db.fetch_users_for_management() == []
    assert db.create_initial_admin("persona", PASSWORD)
    assert not db.needs_initial_admin()
    assert not db.create_initial_admin("otra", PASSWORD)
    assert db.authenticate("persona", PASSWORD)


@pytest.mark.parametrize("password", ["admin", "12345678901", " " * 12, "x" * 1025])
def test_backend_rejects_bad_new_passwords(db, password):
    assert not add(db, password=password)
    assert add(db)
    user = db.get_user("humano")
    with pytest.raises(ValueError):
        db.update_password(user["id"], password)
    assert db.authenticate("humano", PASSWORD)


def test_internal_is_hidden_and_all_mutators_protect_it(db):
    user = db.get_user(INTERNAL_USERNAME)
    uid = user["id"]
    assert not db.authenticate(INTERNAL_USERNAME, PASSWORD)
    assert not add(db, INTERNAL_USERNAME.upper())
    assert db.fetch_all_users() == []
    assert not db.set_user_active(uid, True)[0]
    assert not db.delete_user_safe(uid)[0]
    assert not db.delete_user(uid)[0]
    assert not db.update_user_management(uid, "visible", True, True, "", "", "", "", "", "", "", "")[0]
    with pytest.raises(ValueError):
        db.update_password(uid, PASSWORD)
    with pytest.raises(ValueError):
        db.update_user(uid, "", "", "", "", "", "", "", "")
    with pytest.raises(ValueError):
        db.start_session(INTERNAL_USERNAME)


def test_internal_does_not_allow_deleting_last_human_admin(db):
    assert add(db)
    uid = db.get_user("humano")["id"]
    assert not db.set_user_active(uid, False)[0]
    assert not db.delete_user(uid)[0]
    assert not db.update_user_management(uid, "humano", False, True, "", "", "", "", "", "", "", "")[0]
    assert db.count_active_admins() == 1


def test_plaintext_migration_preserves_ids_history_and_removes_cleartext(tmp_path):
    path = tmp_path / "legacy.db"
    legacy_file(path, PASSWORD, "persona", with_history=True)
    manager = DatabaseManager(path)
    try:
        assert manager.authenticate("persona", PASSWORD)
        assert manager.get_user("persona")["id"] == 7
        assert manager.fetch_session_history()[0]["session_id"] == 42
        assert manager.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert "password" not in {r[1] for r in manager.connection.execute("PRAGMA table_info(users)")}
        assert not manager.connection.execute("SELECT name FROM sqlite_master WHERE name='users_old'").fetchall()
    finally:
        manager.close()
    assert PASSWORD.encode() not in path.read_bytes()
    assert not Path(str(path) + ".backup").exists()


def test_default_admin_requires_verified_replacement(tmp_path):
    path = tmp_path / "legacy.db"
    legacy_file(path)
    manager = DatabaseManager(path)
    try:
        assert not manager.authenticate("admin", "admin")
        with pytest.raises(ValueError):
            manager.start_session("admin")
        assert not manager.replace_legacy_password("admin", "incorrecta", PASSWORD)
        assert manager.replace_legacy_password("admin", "admin", PASSWORD)
        assert manager.authenticate("admin", PASSWORD)
        assert not manager.authenticate("admin", "admin")
    finally:
        manager.close()


def test_hash_migration_keeps_existing_legacy_short_password(tmp_path):
    path = tmp_path / "legacy.db"
    legacy_file(path, "vieja", "persona")
    manager = DatabaseManager(path)
    try:
        assert manager.authenticate("persona", "vieja")
        with pytest.raises(ValueError):
            manager.update_password(7, "corta")
    finally:
        manager.close()


def test_progressive_delay_persists_across_reopen(tmp_path):
    path = tmp_path / "users.db"
    now = [1000.0]
    manager = DatabaseManager(path, clock=lambda: now[0])
    try:
        assert add(manager)
        for _ in range(3):
            assert not manager.authenticate("humano", "incorrecta")
        assert manager.retry_after("humano") == 1
        assert not manager.authenticate("humano", PASSWORD)
    finally:
        manager.close()
    manager = DatabaseManager(path, clock=lambda: now[0])
    try:
        assert manager.retry_after("humano") == 1
        now[0] += 1
        assert not manager.authenticate("humano", "incorrecta")
        assert manager.retry_after("humano") == 2
        now[0] += 2
        assert manager.authenticate("humano", PASSWORD)
        assert manager.retry_after("humano") == 0
    finally:
        manager.close()


def test_stable_default_db_migrates_installation_and_survives_cwd_change(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "data"))
    legacy = tmp_path / "install" / "users.db"
    legacy.parent.mkdir()
    legacy_file(legacy, PASSWORD, "persona")
    backup = Path(str(legacy) + ".backup")
    legacy_file(backup, PASSWORD, "persona")
    manager = DatabaseManager(legacy_path=legacy)
    try:
        expected = str(default_users_path())
        assert manager.db_name == expected
        assert manager.authenticate("persona", PASSWORD)
    finally:
        manager.close()
    monkeypatch.chdir(tmp_path)
    manager = DatabaseManager()
    try:
        assert manager.db_name == expected
        assert manager.authenticate("persona", PASSWORD)
    finally:
        manager.close()
    assert PASSWORD.encode() not in legacy.read_bytes()
    assert PASSWORD.encode() not in backup.read_bytes()


def test_abandoned_users_old_is_recovered_and_history_fk_is_repaired(tmp_path):
    path = tmp_path / "partial.db"
    legacy_file(path, PASSWORD, "persona", with_history=True)
    conn = sqlite3.connect(path)
    conn.execute("ALTER TABLE users RENAME TO users_old")
    conn.commit()
    conn.close()
    manager = DatabaseManager(path)
    try:
        assert manager.authenticate("persona", PASSWORD)
        assert manager.get_user("persona")["id"] == 7
        assert manager.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert manager.fetch_session_history()[0]["user_id"] == 7
        assert manager.delete_user(7)[0] is False  # único administrador humano
    finally:
        manager.close()
    assert PASSWORD.encode() not in path.read_bytes()


def test_failed_migration_rolls_back_schema_and_data(tmp_path, monkeypatch):
    path = tmp_path / "rollback.db"
    legacy_file(path, PASSWORD, "persona")
    original_connect = sqlite3.connect
    class BrokenConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("INSERT INTO users ("):
                raise sqlite3.OperationalError("fallo simulado de migración")
            return super().execute(sql, *args, **kwargs)
    def connect(*args, **kwargs):
        return original_connect(*args, **kwargs, factory=BrokenConnection)
    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError):
        DatabaseManager(path)
    conn = original_connect(path)
    try:
        assert "password" in {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        assert conn.execute("SELECT id,username,password FROM users").fetchone() == (7, "persona", PASSWORD)
    finally:
        conn.close()
