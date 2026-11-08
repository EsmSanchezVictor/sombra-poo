"""Rutas del ejecutable: recursos incluidos y datos persistentes por usuario."""
from pathlib import Path
import sys
from core.auth_policy import default_users_path


def resource_root():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[1]


def resource_path(*parts):
    return resource_root().joinpath(*parts)


def writable_root():
    if getattr(sys, 'frozen', False):
        return default_users_path().parent
    return Path(__file__).resolve().parents[1]


def writable_path(*parts):
    return writable_root().joinpath(*parts)
