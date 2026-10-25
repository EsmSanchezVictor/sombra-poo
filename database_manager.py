import hashlib
import hmac
import os
import sqlite3
import time
import secrets
import tempfile
from pathlib import Path
from core.auth_policy import (default_users_path, password_error, username_error,
                              INTERNAL_USERNAME)
from datetime import datetime, timezone


class DatabaseManager:
    """Usuarios, autenticación, gestión administrativa y trazabilidad de sesiones."""

    def __init__(self, db_name=None, *, clock=None, legacy_path=None, _clean_backups=True):
        self.connection = None
        self.cursor = None
        self._clock = clock or time.time
        path = Path(db_name) if db_name is not None and str(db_name) != ":memory:" else None
        if db_name is None:
            path = default_users_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            source = Path(legacy_path) if legacy_path else Path(__file__).resolve().parent / "users.db"
            # La búsqueda de la base antigua es relativa a la instalación, nunca al CWD.
            if not path.exists() and source.is_file() and source.resolve() != path.resolve():
                old = DatabaseManager(str(source))
                fd, temporary = tempfile.mkstemp(prefix=".users-migrate-", dir=path.parent)
                os.close(fd)
                try:
                    dest = sqlite3.connect(temporary)
                    try:
                        old.connection.backup(dest)
                    finally:
                        dest.close()
                    # Publicación exclusiva: otro arranque no puede perder su base nueva.
                    try:
                        os.link(temporary, path)
                    except FileExistsError:
                        pass
                finally:
                    old.close()
                    if os.path.exists(temporary):
                        os.unlink(temporary)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.db_name = str(path) if path is not None else ":memory:"
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA secure_delete = ON")
            self.cursor = self.connection.cursor()
            self._migrate_plaintext_users()
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.create_table()
            self._migrate_users_schema()
            self.create_session_tables()
            self._initialize_security()
            if path is not None and _clean_backups:
                # Respaldo conocido del migrador histórico: conservar datos, sanitizar credenciales.
                backup = Path(str(path) + ".backup")
                if backup.is_file():
                    cleaned = DatabaseManager(str(backup), _clean_backups=False)
                    cleaned.close()
        except Exception:
            self.close()
            raise

    def _migrate_plaintext_users(self):
        tables = {r[0] for r in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        cols = {r[1] for r in self.connection.execute("PRAGMA table_info(users)")}
        has_plain = "password" in cols
        if not has_plain and "users_old" not in tables:
            return
        self.connection.execute("PRAGMA foreign_keys = OFF")
        rows = [dict(r) for r in self.connection.execute("SELECT * FROM users")] if "users" in tables else []
        names = {r["username"] for r in rows}
        if "users_old" in tables:
            for row in self.connection.execute("SELECT * FROM users_old"):
                row = dict(row)
                if row["username"] not in names:
                    if any(r.get("id") == row.get("id") for r in rows):
                        row["id"] = None
                    rows.append(row)
                    names.add(row["username"])
        prepared = []
        for row in rows:
            if "password" in row:
                row["password_hash"], row["salt"] = self._hash_password(row["password"])
            prepared.append(row)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("DROP TABLE IF EXISTS users")
            self.connection.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, salt TEXT NOT NULL, is_admin INTEGER NOT NULL,
                first_name TEXT, last_name TEXT, dni TEXT, email TEXT, phone TEXT,
                street TEXT, number TEXT, city TEXT, is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT, updated_at TEXT, last_login TEXT)""")
            columns = [r[1] for r in self.connection.execute("PRAGMA table_info(users)")]
            for row in prepared:
                row.setdefault("is_active", 1)
                self.connection.execute(
                    "INSERT INTO users (" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")",
                    [row.get(c) for c in columns])
            self.connection.execute("DROP TABLE IF EXISTS users_old")
            # ALTER TABLE del migrador antiguo podía redirigir esta FK a users_old.
            if "user_sessions" in tables:
                references = self.connection.execute("PRAGMA foreign_key_list(user_sessions)").fetchall()
                if any(row[2] == "users_old" for row in references):
                    self.connection.execute("""CREATE TABLE sessions_secure (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                        username_snapshot TEXT NOT NULL, login_at TEXT NOT NULL, logout_at TEXT,
                        last_activity_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL)""")
                    self.connection.execute("INSERT INTO sessions_secure SELECT id,user_id,username_snapshot,login_at,logout_at,last_activity_at FROM user_sessions")
                    self.connection.execute("DROP TABLE user_sessions")
                    self.connection.execute("ALTER TABLE sessions_secure RENAME TO user_sessions")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.execute("VACUUM")

    def _initialize_security(self):
        self.connection.execute("""CREATE TABLE IF NOT EXISTS auth_attempts (
            account_key TEXT PRIMARY KEY, failures INTEGER NOT NULL,
            blocked_until REAL NOT NULL, updated_at REAL NOT NULL)""")
        internal = self.get_user(INTERNAL_USERNAME)
        if internal is None:
            hashed, salt = self._hash_password(secrets.token_urlsafe(48))
            self.connection.execute("""INSERT OR IGNORE INTO users
                (username,password_hash,salt,is_admin,is_active,is_internal,created_at,updated_at)
                VALUES (?,?,?,0,0,1,?,?)""",
                (INTERNAL_USERNAME, hashed, salt, self._utc_now_iso(), self._utc_now_iso()))
        else:
            self.connection.execute("UPDATE users SET is_internal=1,is_active=0,is_admin=0 WHERE id=?", (internal["id"],))
        old_admin = self.get_user("admin")
        if old_admin and self._verify_password("admin", old_admin["salt"], old_admin["password_hash"]):
            self.connection.execute("UPDATE users SET requires_password_change=1 WHERE id=?", (old_admin["id"],))
        self.connection.commit()

    def needs_initial_admin(self):
        return self.count_active_admins() == 0

    def create_initial_admin(self, username, password, first_name="", last_name=""):
        if username_error(username) or password_error(password):
            return False
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            if not self.needs_initial_admin():
                self.connection.rollback()
                return False
            ok = self.add_user(username, password, 1, first_name, last_name, "", "", "", "", "", "")
            if not ok:
                self.connection.rollback()
            return ok
        except Exception:
            self.connection.rollback()
            raise

    def _protected_user(self, user_id):
        row = self.get_user_by_id(user_id)
        return row is not None and bool(row["is_internal"])

    @staticmethod
    def _account_key(username):
        return hashlib.sha256((username or "").strip().casefold().encode("utf-8")).hexdigest()

    def retry_after(self, username):
        row = self.connection.execute("SELECT blocked_until FROM auth_attempts WHERE account_key=?",
                                      (self._account_key(username),)).fetchone()
        return max(0.0, row[0] - self._clock()) if row else 0.0

    def _check_credentials(self, username, password, *, allow_reset=False):
        if self.retry_after(username) > 0:
            return False
        row = self.get_user(username)
        ok = bool(row is not None and row["is_active"] and not row["is_internal"]
                  and isinstance(password, str) and len(password) <= 1024
                  and self._verify_password(password, row["salt"], row["password_hash"]))
        now = self._clock()
        key = self._account_key(username)
        if not ok:
            previous = self.connection.execute("SELECT failures FROM auth_attempts WHERE account_key=?", (key,)).fetchone()
            failures = min(20, (previous[0] if previous else 0) + 1)
            delay = min(60, 2 ** (failures - 3)) if failures >= 3 else 0
            self.connection.execute("DELETE FROM auth_attempts WHERE updated_at < ?", (now - 86400,))
            self.connection.execute("INSERT OR REPLACE INTO auth_attempts VALUES (?,?,?,?)", (key, failures, now + delay, now))
            self.connection.commit()
            return False
        self.connection.execute("DELETE FROM auth_attempts WHERE account_key=?", (key,))
        self.connection.commit()
        return allow_reset or not row["requires_password_change"]

    def legacy_password_matches(self, username, password):
        row = self.get_user(username)
        return bool(row is not None and row["requires_password_change"]
                    and self._check_credentials(username, password, allow_reset=True))

    def replace_legacy_password(self, username, old_password, new_password):
        if password_error(new_password) or not self._check_credentials(username, old_password, allow_reset=True):
            return False
        row = self.get_user(username)
        if not row["requires_password_change"]:
            return False
        self.update_password(row["id"], new_password)
        return True

    @staticmethod
    def _utc_now_iso():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def create_table(self):
        now = self._utc_now_iso()
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_admin INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                dni TEXT,
                email TEXT,
                phone TEXT,
                street TEXT,
                number TEXT,
                city TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                last_login TEXT
            )'''
        )
        self.connection.commit()

    def _migrate_users_schema(self):
        """Migra en sitio bases anteriores sin perder usuarios existentes."""
        self.cursor.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in self.cursor.fetchall()}
        additions = {
            "is_active": "INTEGER NOT NULL DEFAULT 1",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "last_login": "TEXT",
            "is_internal": "INTEGER NOT NULL DEFAULT 0",
            "requires_password_change": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, decl in additions.items():
            if name not in cols:
                self.cursor.execute(f"ALTER TABLE users ADD COLUMN {name} {decl}")
        now = self._utc_now_iso()
        self.cursor.execute(
            "UPDATE users SET is_active = COALESCE(is_active, 1), "
            "created_at = COALESCE(created_at, ?), updated_at = COALESCE(updated_at, ?)",
            (now, now),
        )
        self.connection.commit()

    def create_session_tables(self):
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username_snapshot TEXT NOT NULL,
                login_at TEXT NOT NULL,
                logout_at TEXT,
                last_activity_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )'''
        )
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS session_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                project_root TEXT,
                project_state_path TEXT,
                action TEXT NOT NULL DEFAULT 'opened',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                last_activity_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES user_sessions(id) ON DELETE CASCADE
            )'''
        )
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_user_sessions_user '
            'ON user_sessions(user_id, login_at)'
        )
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_session_projects_session '
            'ON session_projects(session_id, started_at)'
        )
        self.connection.commit()

    # --- Seguridad de contraseñas -------------------------------------

    @staticmethod
    def _hash_password(password: str, salt: bytes = None):
        if salt is None:
            salt = os.urandom(16)
        hashed = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt, 200_000
        )
        return hashed.hex(), salt.hex()

    @staticmethod
    def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
        try:
            salt = bytes.fromhex(salt_hex)
            hashed, _ = DatabaseManager._hash_password(password, salt)
            return hmac.compare_digest(hashed, hash_hex)
        except (TypeError, ValueError):
            return False

    # --- CRUD de usuarios ----------------------------------------------

    def add_user(self, username, password, is_admin, first_name, last_name,
                 dni, email, phone, street, number, city):
        username = (username or "").strip()
        if username_error(username) or password_error(password):
            return False
        password_hash, salt = self._hash_password(password)
        now = self._utc_now_iso()
        try:
            self.cursor.execute(
                '''INSERT INTO users
                    (username, password_hash, salt, is_admin, first_name, last_name,
                     dni, email, phone, street, number, city, is_active,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)''',
                (username, password_hash, salt, int(bool(is_admin)), first_name, last_name,
                 dni, email, phone, street, number, city, now, now),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            self.connection.rollback()
            return False

    def authenticate(self, username: str, password: str) -> bool:
        if not self._check_credentials(username, password):
            return False
        row = self.get_user(username)
        self.connection.execute("UPDATE users SET last_login=? WHERE id=?", (self._utc_now_iso(), row["id"]))
        self.connection.commit()
        return True

    def update_password(self, user_id, new_password):
        if self._protected_user(user_id):
            raise ValueError("La cuenta interna está protegida.")
        error = password_error(new_password)
        if error:
            raise ValueError(error)
        password_hash, salt = self._hash_password(new_password)
        self.cursor.execute(
            'UPDATE users SET password_hash = ?, salt = ?, updated_at = ?, requires_password_change=0 WHERE id = ?',
            (password_hash, salt, self._utc_now_iso(), int(user_id)),
        )
        self.connection.commit()

    def get_user(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', ((username or "").strip(),))
        return self.cursor.fetchone()

    def get_user_by_id(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (int(user_id),))
        return self.cursor.fetchone()

    def fetch_all_users(self):
        """Compatibilidad histórica. No usar esta proyección en la interfaz."""
        self.cursor.execute('SELECT * FROM users WHERE is_internal=0 ORDER BY username COLLATE NOCASE')
        return self.cursor.fetchall()

    def fetch_users_for_management(self, search="", role="Todos", status="Todos"):
        """Proyección segura para UI: nunca expone hash ni salt."""
        clauses = ["is_internal = 0"]
        params = []
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            clauses.append(
                "(username LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR "
                "dni LIKE ? OR email LIKE ? OR phone LIKE ? OR city LIKE ?)"
            )
            params.extend([like] * 7)
        if role == "Administradores":
            clauses.append("is_admin = 1")
        elif role == "Usuarios":
            clauses.append("is_admin = 0")
        if status == "Activos":
            clauses.append("is_active = 1")
        elif status == "Inactivos":
            clauses.append("is_active = 0")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        self.cursor.execute(
            '''SELECT id, username, first_name, last_name, is_admin, dni, email,
                      phone, city, is_active, last_login
               FROM users''' + where +
            ''' ORDER BY username COLLATE NOCASE''',
            tuple(params),
        )
        return self.cursor.fetchall()

    def update_user(self, user_id, first_name, last_name, dni, email, phone,
                    street, number, city):
        if self._protected_user(user_id):
            raise ValueError("La cuenta interna está protegida.")
        self.cursor.execute(
            '''UPDATE users SET first_name = ?, last_name = ?, dni = ?,
               email = ?, phone = ?, street = ?, number = ?, city = ?,
               updated_at = ? WHERE id = ?''',
            (first_name, last_name, dni, email, phone, street, number, city,
             self._utc_now_iso(), int(user_id)),
        )
        self.connection.commit()

    def count_active_admins(self):
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1 AND is_internal = 0')
        return int(self.cursor.fetchone()[0])

    def update_user_management(self, user_id, username, is_admin, is_active,
                               first_name, last_name, dni, email, phone,
                               street, number, city):
        user_id = int(user_id)
        current = self.get_user_by_id(user_id)
        if current is None:
            return False, "El usuario ya no existe."
        if current["is_internal"]:
            return False, "La cuenta interna está protegida."
        if username_error(username):
            return False, username_error(username)
        username = (username or "").strip()
        if not username:
            return False, "El nombre de usuario no puede quedar vacío."
        self.cursor.execute('SELECT id FROM users WHERE username = ? AND id <> ?', (username, user_id))
        if self.cursor.fetchone() is not None:
            return False, "Ya existe otro usuario con ese nombre de usuario."

        demoting_last_admin = (
            bool(current["is_admin"]) and bool(current["is_active"]) and
            (not bool(is_admin) or not bool(is_active)) and
            self.count_active_admins() <= 1
        )
        if demoting_last_admin:
            return False, "Debe quedar al menos un administrador activo."

        self.cursor.execute(
            '''UPDATE users SET username = ?, is_admin = ?, is_active = ?,
               first_name = ?, last_name = ?, dni = ?, email = ?, phone = ?,
               street = ?, number = ?, city = ?, updated_at = ?
               WHERE id = ?''',
            (username, int(bool(is_admin)), int(bool(is_active)), first_name,
             last_name, dni, email, phone, street, number, city,
             self._utc_now_iso(), user_id),
        )
        self.connection.commit()
        return True, None

    def set_user_active(self, user_id, active):
        user_id = int(user_id)
        row = self.get_user_by_id(user_id)
        if row is None:
            return False, "El usuario no existe."
        if row["is_internal"]:
            return False, "La cuenta interna está protegida."
        if not bool(active) and bool(row["is_admin"]) and bool(row["is_active"]) and self.count_active_admins() <= 1:
            return False, "No se puede desactivar al último administrador activo."
        self.cursor.execute(
            'UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?',
            (int(bool(active)), self._utc_now_iso(), user_id),
        )
        self.connection.commit()
        return True, None

    def delete_user_safe(self, user_id, actor_user_id=None):
        user_id = int(user_id)
        row = self.get_user_by_id(user_id)
        if row is None:
            return False, "El usuario no existe."
        if row["is_internal"]:
            return False, "La cuenta interna está protegida."
        if actor_user_id is not None and int(actor_user_id) == user_id:
            return False, "No podés eliminar la cuenta con la que estás conectado."
        if bool(row["is_admin"]) and bool(row["is_active"]) and self.count_active_admins() <= 1:
            return False, "No se puede eliminar al último administrador activo."
        self.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self.connection.commit()
        return True, None

    def delete_user(self, user_id):
        """La API histórica aplica las mismas protecciones que la gestión."""
        return self.delete_user_safe(user_id)

    # --- Registro de sesiones -----------------------------------------

    def start_session(self, username):
        user = self.get_user(username)
        if user is None or user["is_internal"] or not user["is_active"] or user["requires_password_change"]:
            raise ValueError("La cuenta no puede iniciar sesión.")
        now = self._utc_now_iso()
        self.cursor.execute(
            '''INSERT INTO user_sessions
               (user_id, username_snapshot, login_at, last_activity_at)
               VALUES (?, ?, ?, ?)''',
            (int(user["id"]), str(user["username"]), now, now),
        )
        self.connection.commit()
        return int(self.cursor.lastrowid)

    def touch_session(self, session_id):
        if not session_id:
            return
        now = self._utc_now_iso()
        self.cursor.execute(
            '''UPDATE user_sessions SET last_activity_at = ?
               WHERE id = ? AND logout_at IS NULL''',
            (now, int(session_id)),
        )
        self.cursor.execute(
            '''UPDATE session_projects SET last_activity_at = ?
               WHERE session_id = ? AND ended_at IS NULL''',
            (now, int(session_id)),
        )
        self.connection.commit()

    def start_project_work(self, session_id, project_name, project_root=None,
                           project_state_path=None, action='opened'):
        if not session_id:
            return None
        now = self._utc_now_iso()
        self.cursor.execute(
            '''UPDATE session_projects
               SET ended_at = ?, last_activity_at = ?
               WHERE session_id = ? AND ended_at IS NULL''',
            (now, now, int(session_id)),
        )
        self.cursor.execute(
            '''INSERT INTO session_projects
               (session_id, project_name, project_root, project_state_path,
                action, started_at, last_activity_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (int(session_id), str(project_name), project_root,
             project_state_path, str(action or 'opened'), now, now),
        )
        self.cursor.execute(
            'UPDATE user_sessions SET last_activity_at = ? WHERE id = ?',
            (now, int(session_id)),
        )
        self.connection.commit()
        return int(self.cursor.lastrowid)

    def end_project_work(self, session_id):
        if not session_id:
            return
        now = self._utc_now_iso()
        self.cursor.execute(
            '''UPDATE session_projects
               SET ended_at = ?, last_activity_at = ?
               WHERE session_id = ? AND ended_at IS NULL''',
            (now, now, int(session_id)),
        )
        self.cursor.execute(
            'UPDATE user_sessions SET last_activity_at = ? WHERE id = ?',
            (now, int(session_id)),
        )
        self.connection.commit()

    def end_session(self, session_id):
        if not session_id:
            return
        now = self._utc_now_iso()
        self.cursor.execute(
            '''UPDATE session_projects
               SET ended_at = COALESCE(ended_at, ?), last_activity_at = ?
               WHERE session_id = ? AND ended_at IS NULL''',
            (now, now, int(session_id)),
        )
        self.cursor.execute(
            '''UPDATE user_sessions
               SET logout_at = COALESCE(logout_at, ?), last_activity_at = ?
               WHERE id = ?''',
            (now, now, int(session_id)),
        )
        self.connection.commit()

    def fetch_session_history(self, user_id=None, limit=500):
        params = []
        where = ''
        if user_id is not None:
            where = 'WHERE s.user_id = ?'
            params.append(int(user_id))
        params.append(max(1, int(limit)))
        self.cursor.execute(
            f'''SELECT
                    s.id AS session_id,
                    s.user_id,
                    s.username_snapshot,
                    s.login_at,
                    s.logout_at,
                    s.last_activity_at,
                    p.id AS project_period_id,
                    p.project_name,
                    p.project_root,
                    p.project_state_path,
                    p.action,
                    p.started_at,
                    p.ended_at,
                    p.last_activity_at
                FROM user_sessions AS s
                LEFT JOIN session_projects AS p ON p.session_id = s.id
                {where}
                ORDER BY s.login_at DESC, p.started_at DESC
                LIMIT ?''',
            tuple(params),
        )
        return self.cursor.fetchall()

    def delete_session_history(self, exclude_session_id=None):
        """Elimina el historial de sesiones de forma explícita.

        Si ``exclude_session_id`` está definido, conserva esa sesión (por
        ejemplo la sesión administrativa actualmente conectada). Gracias a
        ``ON DELETE CASCADE`` también se eliminan sus tramos de proyecto.
        Devuelve la cantidad de sesiones eliminadas.
        """
        if exclude_session_id is None:
            self.cursor.execute('DELETE FROM user_sessions')
        else:
            self.cursor.execute(
                'DELETE FROM user_sessions WHERE id <> ?',
                (int(exclude_session_id),),
            )
        deleted = int(self.cursor.rowcount if self.cursor.rowcount is not None else 0)
        self.connection.commit()
        return max(0, deleted)

    def close(self):
        """Cierra recursos SQLite de forma segura e idempotente."""
        cursor = getattr(self, "cursor", None)
        connection = getattr(self, "connection", None)
        self.cursor = None
        self.connection = None
        if cursor is not None:
            try:
                cursor.close()
            except sqlite3.Error:
                pass
        if connection is not None:
            try:
                connection.close()
            except sqlite3.Error:
                pass
