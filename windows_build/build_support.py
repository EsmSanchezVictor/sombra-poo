"""Preparación de una copia de compilación sin datos locales del desarrollador."""
from pathlib import Path
import ast
import hashlib
import shutil

RESOURCE_FILES = (
    'assest/proyecto.png', 'assest/marca.png', 'assest/protada.png',
    'data/locations_latam.csv', 'data/locations_ar.csv',
    'validacion/campo/plantillas/plantilla_validacion_termica.csv',
    'validacion/campo/plantillas/plantilla_instrumentos_v16.csv',
    'validacion/campo/plantillas/plantilla_meteorologia_observada.csv',
    'validacion/fotos/manifest.plantilla.json',
    'docs/MANUAL_SOMBRA.html',
    'test/imagen/fiebre (3).png', 'test/imagen/sombra (3).png',
    'test/imagen/config (3).png', 'test/imagen/vista-3d (3).png',
)


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def prepare_stage(project_root, destination):
    root = Path(project_root).resolve()
    target = Path(destination).resolve()
    profile = root/'windows_build'
    assignments = ast.parse((root/'core/app_version.py').read_text(encoding='utf-8')).body
    release = next(ast.literal_eval(n.value) for n in assignments
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'APP_RELEASE' for t in n.targets))
    if release != 'v35.6-etapa4.3.5':
        raise ValueError(f'Este perfil corresponde a v35.6-etapa4.3.5; se encontró {release}.')
    if target.exists():
        raise ValueError('La carpeta temporal de compilación debe ser nueva.')
    if target == root or root.is_relative_to(target):
        raise ValueError('La carpeta temporal no puede contener el proyecto de origen.')
    for name in RESOURCE_FILES:
        if not (root/name).is_file():
            raise ValueError(f'Falta un recurso necesario: {name}')
    sources = list(root.glob('*.py'))
    for package in ('core', 'services', 'ui'):
        sources.extend(p for p in (root/package).rglob('*.py') if '__pycache__' not in p.parts)
    target.mkdir(parents=True)
    for source in sources:
        dest = target/source.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    for name in RESOURCE_FILES:
        dest = target/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, dest)
    shutil.copyfile(profile/'launcher.py', target/'sombra_launcher.py')
    for name in ('README.md', 'CHANGELOG.md', 'requirements.txt', 'requirements-full.txt'):
        if (root/name).is_file():
            shutil.copyfile(root/name, target/name)
    return dict(app_release=release, profile='windows-packaging-2', source_root=str(root), stage=str(target),
                resources=list(RESOURCE_FILES),
                source_files_sha256={p.relative_to(target).as_posix(): sha256(p)
                                     for p in sorted(target.rglob('*')) if p.is_file()},
                private_user_data_included=False)
