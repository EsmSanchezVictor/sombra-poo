import hashlib
import hmac
import os
import sqlite3
from tkinter import messagebox


class DatabaseManager:
    """Clase para manejar la base de datos de usuarios.

    CAMBIO CLAVE respecto a la versión original: las contraseñas ya NO se
    guardan en texto plano. Se guarda un hash PBKDF2-HMAC-SHA256 + salt
    único por usuario. Nadie que abra users.db puede leer contraseñas.
    """

    def __init__(self, db_name="users.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
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
            city TEXT
        )''')
        self.connection.commit()

    # --- Seguridad de contraseñas -------------------------------------

    @staticmethod
    def _hash_password(password: str, salt: bytes = None):
        """Genera (hash_hex, salt_hex). Si no se pasa salt, genera uno nuevo
        aleatorio de 16 bytes. 200_000 iteraciones es un valor razonable
        de costo computacional para 2026 sin volver la UI lenta."""
        if salt is None:
            salt = os.urandom(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000)
        return hashed.hex(), salt.hex()

    @staticmethod
    def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
        salt = bytes.fromhex(salt_hex)
        hashed, _ = DatabaseManager._hash_password(password, salt)
        # compare_digest evita timing attacks (comparar substring por substring
        # filtraría información sobre cuánto del hash coincide)
        return hmac.compare_digest(hashed, hash_hex)

    # --- CRUD -------------------------------------------------------------

    def add_user(self, username, password, is_admin, first_name, last_name,
                 dni, email, phone, street, number, city):
        password_hash, salt = self._hash_password(password)
        try:
            self.cursor.execute('''INSERT INTO users
                (username, password_hash, salt, is_admin, first_name, last_name,
                 dni, email, phone, street, number, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (username, password_hash, salt, is_admin, first_name, last_name,
                 dni, email, phone, street, number, city))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "El nombre de usuario ya existe.")
            return False

    def authenticate(self, username: str, password: str) -> bool:
        """NUEVO: reemplaza cualquier comparación directa de password que
        hubiera en login_window.py. Úsalo así:

            if db.authenticate(usuario, clave):
                # login OK
        """
        row = self.get_user(username)
        if row is None:
            return False
        # Orden de columnas: id, username, password_hash, salt, is_admin, ...
        _, _, password_hash, salt, *_ = row
        return self._verify_password(password, salt, password_hash)

    def update_password(self, user_id, new_password):
        """NUEVO: para pantallas de 'cambiar contraseña' o reseteo por admin."""
        password_hash, salt = self._hash_password(new_password)
        self.cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?',
                             (password_hash, salt, user_id))
        self.connection.commit()

    def get_user(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return self.cursor.fetchone()

    def fetch_all_users(self):
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()

    def update_user(self, user_id, first_name, last_name, dni, email, phone,
                     street, number, city):
        self.cursor.execute('''UPDATE users SET first_name = ?, last_name = ?, dni = ?,
            email = ?, phone = ?, street = ?, number = ?, city = ? WHERE id = ?''',
            (first_name, last_name, dni, email, phone, street, number, city, user_id))
        self.connection.commit()

    def delete_user(self, user_id):
        self.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self.connection.commit()

    def get_user_by_id(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return self.cursor.fetchone()

    def close(self):
        self.connection.close()
