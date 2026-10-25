"""Inventario SHA256 incremental y verificación de entradas/resultados."""
from datetime import datetime, timezone
import hashlib
import os
from core.safe_paths import contained_path, relative_path
from core.project_schema import UnsupportedSchemaError

INVENTORY_SCHEMA = 1
SKIP_DIRS = {'respaldos', '_legacy_v18', '.sombra-recovery', '.git', '__pycache__'}
SKIP_FILES = {'config/inventario.json', 'config/save.lock'}

def inventory_schema(manifest):
    if not isinstance(manifest, dict):
        raise ValueError('Inventario de integridad inválido')
    version = manifest.get('integrity_schema_version')
    if version is not None and (type(version) is not int or version != INVENTORY_SCHEMA):
        raise UnsupportedSchemaError('Esquema de inventario no soportado; no se modificó')
    return version

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def project_files(root, *, include_legacy=False):
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS or (include_legacy and d == '_legacy_v18'))
        for d in dirs:
            if os.path.islink(os.path.join(folder,d)):
                raise ValueError('El proyecto contiene un directorio enlazado; no se exportó')
            contained_path(root, os.path.join(folder,d))
        for name in sorted(files):
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root).replace('\\','/')
            if rel == 'config/save.lock' or name.endswith(('.tmp','.3es')) or name.startswith('.sombra-write-'):
                continue
            if os.path.islink(path):
                raise ValueError('El proyecto contiene un archivo enlazado; no se exportó')
            yield rel, contained_path(root, path)

class IntegrityTracker:
    def __init__(self):
        self.cache = {}

    def inventory(self, root, *, overlays=None, transaction_id=None):
        paths = dict(project_files(root))
        paths.update(overlays or {})
        entries = []
        active = set()
        for rel, filename in sorted(paths.items()):
            if rel in SKIP_FILES:
                continue
            relative_path(rel)
            stat = os.stat(filename)
            signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            active.add(rel)
            cached = self.cache.get(rel)
            digest = cached[1] if cached and cached[0] == signature else sha256_file(filename)
            self.cache[rel] = (signature, digest)
            entries.append({'path': rel, 'size_bytes': stat.st_size, 'sha256': digest,
                            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')})
        self.cache = {key: self.cache[key] for key in active}
        return {'integrity_schema_version': INVENTORY_SCHEMA, 'layout_version': 2,
                'transaction_id': transaction_id, 'updated_at': datetime.now(timezone.utc).isoformat(),
                'file_count': len(entries), 'files': entries}

def verify_inventory(root, manifest):
    if inventory_schema(manifest) != INVENTORY_SCHEMA:
        raise ValueError('Inventario de integridad no soportado')
    records = manifest.get('files')
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError('Inventario de integridad inválido')
    issues, seen = [], set()
    for record in records:
        rel = relative_path(record['path'])
        if rel in seen:
            raise ValueError('Ruta duplicada en el inventario')
        seen.add(rel)
        expected = record.get('sha256', '')
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('Hash SHA256 inválido')
        path = contained_path(root, rel, allow_absolute=False)
        if not os.path.isfile(path):
            issues.append({'path': rel, 'status': 'missing', 'expected_sha256': expected})
        elif sha256_file(path) != expected:
            issues.append({'path': rel, 'status': 'changed', 'expected_sha256': expected})
    return issues
