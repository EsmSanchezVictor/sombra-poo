"""Política de cuentas humanas y ubicación estable de credenciales."""
import os
import sys
from pathlib import Path

MIN_PASSWORD_LENGTH = 12
INTERNAL_USERNAME = "__sombra_internal__"


def password_error(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        return f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
    if len(password) > 1024 or not password.strip():
        return "La contraseña no es válida."
    return None


def username_error(username):
    if not isinstance(username, str) or not username.strip():
        return "Ingresá un nombre de usuario."
    if username.strip().casefold() == INTERNAL_USERNAME.casefold():
        return "Ese nombre está reservado para el sistema."
    if len(username.strip()) > 100 or any(ord(c) < 32 for c in username):
        return "El nombre de usuario no es válido."
    return None


def default_users_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "ProyectoSombra" / "users.db"
