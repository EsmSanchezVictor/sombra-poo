"""Contratos de arranque y distribución de la versión de cierre."""
from pathlib import Path
import json
import sys

import pytest
from types import SimpleNamespace

from windows_build.build_support import prepare_stage


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_command_uses_authenticated_entrypoint(monkeypatch):
    import app
    called = []
    monkeypatch.setitem(sys.modules, 'main', SimpleNamespace(main=lambda: called.append('login')))
    app.main()
    assert called == ['login']


@pytest.mark.parametrize(("quick", "filename", "title"), [
    (True, "GUIA_RAPIDA_SOMBRA.html", "<h1>Guía rápida</h1>"),
    (False, "MANUAL_SOMBRA.html", "<h1>Manual completo</h1>"),
])
def test_offline_help_opens_packagable_document_from_other_directory(monkeypatch, tmp_path, quick, filename, title):
    from core.app_version import APP_RELEASE
    from ui.app_ui import SombraApp
    import webbrowser
    links = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(webbrowser, 'open', lambda url: links.append(url) or True)
    SombraApp.open_user_help(SimpleNamespace(root=None), quick=quick)
    manual = ROOT/'docs'/filename
    content = manual.read_text(encoding='utf-8')
    assert APP_RELEASE in content and title in content and 'Validación de campo pendiente' in content
    assert links == [manual.as_uri()]


def test_windows_stage_matches_closure_layout_without_private_data(tmp_path):
    import shutil
    source = tmp_path/'fuente'
    shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
    private = ('users.db', 'data/settings.json', 'data/species_db.json', 'mascaras.json',
               'proyectos/Privado/foto.jpg', 'validacion/campo/campanias/prueba/crudos/mediciones.csv')
    for name in private:
        item = source/name
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_bytes(b'privado')
    target = tmp_path/'stage'
    report = prepare_stage(source, target)
    assert all(not (target/name).exists() for name in private)
    assert all((source/name).read_bytes() == b'privado' for name in private)
    for name in ('MANUAL_SOMBRA.html', 'GUIA_RAPIDA_SOMBRA.html', 'LICENCIA_PROYECTO_SOMBRA.txt'):
        assert (target/'docs'/name).read_bytes() == (source/'docs'/name).read_bytes()
    assert (target/'validacion/campo/plantillas/plantilla_validacion_termica.csv').is_file()
    assert (target/'validacion/fotos/manifest.plantilla.json').is_file()
    assert 'core/runtime_paths.py' in report['source_files_sha256']
    for name in ('proyecto.png', 'marca.png', 'protada.png'):
        assert (target/'assest'/name).read_bytes() == (source/'assest'/name).read_bytes()


def test_frozen_resources_and_writable_data_are_separate(monkeypatch, tmp_path):
    from core import runtime_paths
    bundle = tmp_path/'Programa'/'_internal'
    userdata = tmp_path/'perfil'/'ProyectoSombra'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle), raising=False)
    monkeypatch.setattr(runtime_paths, 'default_users_path', lambda: userdata/'users.db')
    assert runtime_paths.resource_path('docs', 'MANUAL_SOMBRA.html') == bundle/'docs/MANUAL_SOMBRA.html'
    assert runtime_paths.writable_path('data', 'settings.json') == userdata/'data/settings.json'
