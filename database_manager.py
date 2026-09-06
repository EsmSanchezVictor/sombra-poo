import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone


class DatabaseManager:
    """Usuarios, autenticación, gestión administrativa y trazabilidad de sesiones."""

    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.connection.cursor()
        self.create_table()
        self._migrate_users_schema()
        self.create_session_tables()

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
        salt = bytes.fromhex(salt_hex)
        hashed, _ = DatabaseManager._hash_password(password, salt)
        return hmac.compare_digest(hashed, hash_hex)

    # --- CRUD de usuarios ----------------------------------------------

    def add_user(self, username, password, is_admin, first_name, last_name,
                 dni, email, phone, street, number, city):
        username = (username or "").strip()
        if not username:
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
            return False

    def authenticate(self, username: str, password: str) -> bool:
        row = self.get_user(username)
        if row is None:
            return False
        if "is_active" in row.keys() and not bool(row["is_active"]):
            return False
        password_hash = row["password_hash"]
        salt = row["salt"]
        ok = self._verify_password(password, salt, password_hash)
        if ok:
            now = self._utc_now_iso()
            self.cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, int(row["id"])),
            )
            self.connection.commit()
        return ok

    def update_password(self, user_id, new_password):
        password_hash, salt = self._hash_password(new_password)
        self.cursor.execute(
            'UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?',
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
        self.cursor.execute('SELECT * FROM users ORDER BY username COLLATE NOCASE')
        return self.cursor.fetchall()

    def fetch_users_for_management(self, search="", role="Todos", status="Todos"):
        """Proyección segura para UI: nunca expone hash ni salt."""
        clauses = []
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
        self.cursor.execute(
            '''UPDATE users SET first_name = ?, last_name = ?, dni = ?,
               email = ?, phone = ?, street = ?, number = ?, city = ?,
               updated_at = ? WHERE id = ?''',
            (first_name, last_name, dni, email, phone, street, number, city,
             self._utc_now_iso(), int(user_id)),
        )
        self.connection.commit()

    def count_active_admins(self):
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1')
        return int(self.cursor.fetchone()[0])

    def update_user_management(self, user_id, username, is_admin, is_active,
                               first_name, last_name, dni, email, phone,
                               street, number, city):
        user_id = int(user_id)
        current = self.get_user_by_id(user_id)
        if current is None:
            return False, "El usuario ya no existe."
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
        if actor_user_id is not None and int(actor_user_id) == user_id:
            return False, "No podés eliminar la cuenta con la que estás conectado."
        if bool(row["is_admin"]) and bool(row["is_active"]) and self.count_active_admins() <= 1:
            return False, "No se puede eliminar al último administrador activo."
        self.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self.connection.commit()
        return True, None

    def delete_user(self, user_id):
        """Compatibilidad histórica: elimina sin validaciones del actor."""
        self.cursor.execute('DELETE FROM users WHERE id = ?', (int(user_id),))
        self.connection.commit()

    # --- Registro de sesiones -----------------------------------------

    def start_session(self, username):
        user = self.get_user(username)
        if user is None:
            raise ValueError(f"Usuario inexistente: {username}")
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

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass
        try:
            self.connection.close()
        except Exception:
            pass
