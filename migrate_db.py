"""
Migración única de la tabla `users`.

Tu users.db actual guarda `password` en texto plano. Este script:
  1. Hace un backup de users.db (users.db.backup).
  2. Renombra la tabla vieja a `users_old`.
  3. Crea la tabla nueva con password_hash + salt (vía DatabaseManager).
  4. Re-inserta cada usuario, hasheando su contraseña en el proceso.

Ejecutalo UNA sola vez:
    python migrate_db.py

Si algo sale mal, restaurá el backup:
    cp users.db.backup users.db
"""
import shutil
import sqlite3

from database_manager import DatabaseManager

DB_NAME = "users.db"


def migrar():
    shutil.copy(DB_NAME, DB_NAME + ".backup")
    print(f"Backup creado en {DB_NAME}.backup")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columnas = [c[1] for c in cur.fetchall()]

    if "password_hash" in columnas:
        print("La tabla ya está migrada. No se hace nada.")
        conn.close()
        return

    cur.execute("ALTER TABLE users RENAME TO users_old")
    conn.commit()

    cur.execute('''SELECT username, password, is_admin, first_name, last_name,
                    dni, email, phone, street, number, city FROM users_old''')
    usuarios_viejos = cur.fetchall()
    conn.close()

    dm = DatabaseManager(DB_NAME)  # crea la tabla nueva (users) con el esquema correcto

    migrados = 0
    for username, password_plano, is_admin, first_name, last_name, dni, email, phone, street, number, city in usuarios_viejos:
        ok = dm.add_user(username, password_plano, is_admin, first_name, last_name,
                          dni, email, phone, street, number, city)
        if ok:
            migrados += 1

    dm.close()
    print(f"Migrados {migrados}/{len(usuarios_viejos)} usuarios.")
    print("La tabla vieja quedó como 'users_old' por si necesitás verificar algo antes de borrarla.")


if __name__ == "__main__":
    migrar()
