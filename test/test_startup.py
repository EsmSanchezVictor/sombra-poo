"""Regresión de orden de arranque y limpieza ante fallas de dependencias."""
import logging
import subprocess
import sys
from pathlib import Path

import pytest


def test_bootstrap_import_does_not_start_heavy_dependencies():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-c",
         "import main, app, sys; "
         "assert not {'numpy', 'pandas', 'matplotlib', 'main_app'}.intersection(sys.modules)"],
        cwd=root, check=True, timeout=10,
    )


def test_missing_dependency_leaves_no_splash_or_hidden_root(monkeypatch):
    import main

    events = []

    class Root:
        def withdraw(self):
            events.append("ocultar raíz")

        def winfo_exists(self):
            return True

        def destroy(self):
            events.append("destruir raíz")

    class Splash:
        def __init__(self, root):
            events.append("portada")

        def phase(self, label, completed):
            events.append((label, completed))

        def close(self):
            events.append("cerrar portada")

    monkeypatch.setattr(main.tk, "Tk", Root)
    monkeypatch.setattr(main, "StartupSplash", Splash)
    monkeypatch.setattr(main, "aplicar_tema", lambda root: events.append("tema"))
    monkeypatch.setattr(main, "configure_logging", lambda: logging.getLogger("startup-test"))
    monkeypatch.setitem(sys.modules, "numpy", None)
    with pytest.raises(ModuleNotFoundError, match="numpy"):
        main.main()
    assert events == ["ocultar raíz", "tema", "portada", ("Cargando NumPy y pandas…", 0),
                      "cerrar portada", "destruir raíz"]
