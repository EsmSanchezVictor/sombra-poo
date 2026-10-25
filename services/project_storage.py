"""Guardado recuperable de estado, escenas e índice SQLite, sin dependencias UI.

Los archivos de una generación son inmutables. El journal se publica sólo
cuando todos están completos; la recuperación vuelve a publicar esa generación.
Los artefactos fotográficos se verifican por hash, no se duplican en cada autosave.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import os
import re
import shutil
import sqlite3
import uuid
import zipfile
from core.safe_io import atomic_write_json, atomic_output, fsync_directory, fsync_file
from core.safe_paths import contained_path, relative_path, sanitize_payload
from core.project_schema import migrate_payload, UnsupportedSchemaError, validate_analysis_schema
from core.project_lock import project_lock
from core.project_integrity import IntegrityTracker, sha256_file, verify_inventory, project_files, inventory_schema

log = logging.getLogger('sombra.storage')
PROTOCOL_VERSION = 1
MAX_JSON_BYTES = 16 * 1024 * 1024

class RecoveryDataError(ValueError):
    pass

class UnsupportedRecoveryError(ValueError):
    pass


def read_json(path):
    with open(path, 'rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('El JSON excede el límite de lectura de 16 MiB')
    return json.loads(raw.decode('utf-8'))


def atomic_copy(source, target):
    with atomic_output(target) as temporary:
        shutil.copyfile(source, temporary)


def backup_sqlite(source, target):
    original = sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True)
    copy = None
    try:
        original.execute('PRAGMA trusted_schema=OFF')
        validate_analysis_schema(original)
        copy = sqlite3.connect(target)
        original.backup(copy)
        if copy.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Base de análisis dañada; no se guardó')
        copy.commit()
    finally:
        if copy is not None: copy.close()
        original.close()
    fsync_file(target)


def check_sqlite_schema(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA trusted_schema=OFF')
        validate_analysis_schema(connection)
    finally:
        connection.close()


class ProjectStorage:
    def __init__(self, root):
        self.root = os.path.realpath(os.path.abspath(root))
        self.home = contained_path(self.root, '.sombra-recovery', allow_absolute=False)
        self.journal = os.path.join(self.home, 'journal.json')
        self.head = os.path.join(self.home, 'head.json')
        self.integrity = IntegrityTracker()
        self.last_recovery = None

    def _generation(self, transaction_id):
        if not isinstance(transaction_id, str) or not re.fullmatch('[0-9a-f]{32}', transaction_id):
            raise ValueError('Identificador de recuperación inválido')
        return contained_path(self.root, f'.sombra-recovery/generations/{transaction_id}', allow_absolute=False)

    @staticmethod
    def _allowed_target(rel):
        rel = relative_path(rel)
        fixed = {'config/project.json','config/inventario.json','escena/edicion.xlsx',
                 'escena/modelo.xlsx','analisis/analisis.sqlite3'}
        return rel in fixed or ('/' not in rel and rel.endswith('.sombra'))

    def _validate(self, transaction_id):
        folder = self._generation(transaction_id)
        manifest = read_json(contained_path(folder, 'manifest.json', allow_absolute=False))
        if not isinstance(manifest,dict) or manifest.get('protocol_version') != PROTOCOL_VERSION or manifest.get('transaction_id') != transaction_id:
            raise UnsupportedRecoveryError('Registro de recuperación no soportado')
        entries = manifest.get('entries')
        if not isinstance(entries,list) or not 3 <= len(entries) <= 6:
            raise ValueError('Lista de recuperación inválida')
        names = set()
        for entry in entries:
            rel = entry['path']
            if not self._allowed_target(rel) or rel in names:
                raise ValueError('La recuperación contiene una ruta no permitida')
            names.add(rel)
            source = contained_path(folder, rel, allow_absolute=False)
            if not os.path.isfile(source) or sha256_file(source) != entry['sha256'] or os.path.getsize(source) != entry['size_bytes']:
                raise RecoveryDataError('La generación de recuperación está incompleta o dañada')
        state_path = manifest.get('state_path')
        if state_path not in names or '/' in state_path or not state_path.endswith('.sombra'):
            raise ValueError('Estado de recuperación inválido')
        if not {'config/project.json','config/inventario.json'} <= names:
            raise ValueError('La recuperación carece de copias de estado e inventario')
        if Path(contained_path(folder,state_path)).read_bytes() != Path(contained_path(folder,'config/project.json')).read_bytes():
            raise RecoveryDataError('Las copias del estado no pertenecen al mismo conjunto')
        payload = sanitize_payload(self.root, migrate_payload(read_json(contained_path(folder,state_path))), strict=True)
        if payload.get('save_transaction_id') != transaction_id:
            raise ValueError('El estado pertenece a otro guardado')
        if inventory_schema(read_json(contained_path(folder,'config/inventario.json'))) is None:
            raise RecoveryDataError('La recuperación carece de inventario verificable')
        if 'analisis/analisis.sqlite3' in names:
            check_sqlite_schema(contained_path(folder, 'analisis/analisis.sqlite3'))
        return folder, manifest, payload

    def _publish(self, transaction_id):
        folder, manifest, _ = self._validate(transaction_id)
        # Índice .sombra al final; los lectores internos emplean project_lock.
        entries = sorted(manifest['entries'], key=lambda e: e['path'].endswith('.sombra'))
        for entry in entries:
            target = contained_path(self.root,entry['path'],allow_absolute=False)
            atomic_copy(contained_path(folder,entry['path'],allow_absolute=False),target)
        atomic_write_json(self.head, {'protocol_version': PROTOCOL_VERSION, 'transaction_id': transaction_id})
        atomic_write_json(os.path.join(folder,'committed.json'),{'transaction_id':transaction_id})

    def _read_pointer(self, filename):
        data = read_json(contained_path(self.root,filename))
        if not isinstance(data,dict) or data.get('protocol_version') != PROTOCOL_VERSION:
            raise UnsupportedRecoveryError('Protocolo de recuperación no soportado')
        transaction_id = data.get('transaction_id')
        self._generation(transaction_id)
        return transaction_id

    def _usable_head(self):
        try:
            current = self._read_pointer(self.head)
            self._validate(current)
            return current, False
        except (UnsupportedSchemaError, UnsupportedRecoveryError):
            raise
        except (RecoveryDataError,OSError,json.JSONDecodeError,UnicodeError):
            parent = os.path.join(self.home,'generations')
            candidates = sorted(os.scandir(parent),key=lambda e:e.stat().st_mtime_ns,reverse=True)
            for entry in candidates:
                if not entry.is_dir(follow_symlinks=False) or not os.path.isfile(os.path.join(entry.path,'committed.json')):
                    continue
                try:
                    self._validate(entry.name)
                except (ValueError,OSError):
                    continue
                log.warning('Se usará la generación anterior verificada: %s',entry.name)
                return entry.name, True
            raise RecoveryDataError('No queda una generación de recuperación íntegra')

    def _guard_live_schema(self, rel):
        target = contained_path(self.root, rel, allow_absolute=False)
        if not os.path.isfile(target):
            return
        try:
            if rel.endswith(('.sombra','project.json')):
                migrate_payload(read_json(target))
            elif rel == 'config/inventario.json':
                inventory_schema(read_json(target))
            elif rel == 'analisis/analisis.sqlite3':
                check_sqlite_schema(target)
        except UnsupportedSchemaError:
            raise
        except (ValueError, OSError, sqlite3.DatabaseError, UnicodeError):
            # Los archivos dañados pueden recuperarse desde una generación válida.
            pass

    def recover(self, *, check_live=False):
        self.last_recovery = None
        with project_lock(self.root):
            if os.path.isfile(self.journal):
                transaction_id = self._read_pointer(self.journal)
                self._publish(transaction_id)
                os.unlink(self.journal); fsync_directory(self.home)
                self.last_recovery = {'reason':'interrupted_save', 'transaction_id':transaction_id}
                log.warning('Se completó un guardado interrumpido: %s', transaction_id)
            elif check_live and os.path.isfile(self.head):
                transaction_id, previous = self._usable_head()
                folder, manifest, _ = self._validate(transaction_id)
                changed = []
                for entry in manifest['entries']:
                    target = contained_path(self.root,entry['path'],allow_absolute=False)
                    if not os.path.isfile(target) or sha256_file(target) != entry['sha256']:
                        # Un formato futuro no es corrupción: requiere una aplicación compatible.
                        self._guard_live_schema(entry['path'])
                        changed.append(entry['path'])
                if changed or previous:
                    # No destruir cambios posteriores: conservar los archivos divergentes.
                    quarantine = contained_path(self.root,f'.sombra-recovery/quarantine/{uuid.uuid4().hex}',allow_absolute=False)
                    for rel in changed:
                        target = contained_path(self.root,rel,allow_absolute=False)
                        if os.path.isfile(target):
                            destination = contained_path(quarantine,rel,allow_absolute=False)
                            os.makedirs(os.path.dirname(destination),exist_ok=True)
                            atomic_copy(target,destination)
                    self._publish(transaction_id)
                    self.last_recovery = {'reason':'previous_generation' if previous else 'inconsistent_files','transaction_id':transaction_id,
                                          'files':changed,'preserved_at':os.path.relpath(quarantine,self.root)}
                    log.warning('Se restauró un conjunto válido; diferencias preservadas: %s', changed)
            return self.last_recovery

    def commit(self, state_path, payload, *, scene_writer=None):
        with project_lock(self.root):
            # Un nuevo guardado nunca debe eliminar un journal pendiente.
            self.recover()
            if os.path.isfile(self.head):
                self._usable_head()
            state_path = contained_path(self.root,state_path)
            state_rel = os.path.relpath(state_path,self.root).replace('\\','/')
            if '/' in state_rel or not state_rel.endswith('.sombra'):
                raise ValueError('La ruta de estado canónica no es válida')
            for rel in (state_rel,'config/project.json','config/inventario.json','analisis/analisis.sqlite3'):
                self._guard_live_schema(rel)
            transaction_id = uuid.uuid4().hex
            folder = self._generation(transaction_id)
            os.makedirs(folder,exist_ok=False)
            prepared = False
            try:
                payload = sanitize_payload(self.root,migrate_payload(payload))
                payload['save_transaction_id'] = transaction_id
                payload['save_protocol_version'] = PROTOCOL_VERSION
                overlays = {}
                for rel in (state_rel,'config/project.json'):
                    target = contained_path(folder,rel,allow_absolute=False)
                    atomic_write_json(target,payload)
                    overlays[rel] = target
                if scene_writer is not None:
                    for rel, kind in (('escena/edicion.xlsx','edit'),('escena/modelo.xlsx','model')):
                        target = contained_path(folder,rel,allow_absolute=False)
                        os.makedirs(os.path.dirname(target),exist_ok=True)
                        scene_writer(kind,target)
                        with zipfile.ZipFile(target) as archive:
                            if archive.testzip() is not None or 'xl/workbook.xml' not in archive.namelist():
                                raise ValueError('Excel preparado inválido')
                        overlays[rel] = target
                database = contained_path(self.root,'analisis/analisis.sqlite3',allow_absolute=False)
                if os.path.isfile(database):
                    rel = 'analisis/analisis.sqlite3'
                    target = contained_path(folder,rel,allow_absolute=False)
                    os.makedirs(os.path.dirname(target),exist_ok=True)
                    backup_sqlite(database,target)
                    overlays[rel] = target
                inventory = self.integrity.inventory(self.root,overlays=overlays,transaction_id=transaction_id)
                rel = 'config/inventario.json'
                target = contained_path(folder,rel,allow_absolute=False)
                atomic_write_json(target,inventory); overlays[rel] = target
                manifest = {'protocol_version':PROTOCOL_VERSION,'transaction_id':transaction_id,
                            'created_at':datetime.now(timezone.utc).isoformat(),'state_path':state_rel,
                            'entries':[{'path':rel,'sha256':sha256_file(path),'size_bytes':os.path.getsize(path)} for rel,path in sorted(overlays.items())]}
                atomic_write_json(os.path.join(folder,'manifest.json'),manifest)
                self._validate(transaction_id)
                os.makedirs(self.home,exist_ok=True)
                atomic_write_json(self.journal,{'protocol_version':PROTOCOL_VERSION,'transaction_id':transaction_id})
                prepared = True
                self._publish(transaction_id)
                os.unlink(self.journal); fsync_directory(self.home)
                try:
                    self._prune(transaction_id)
                except OSError:
                    log.exception('No se pudo limpiar una generación antigua; el guardado está completo')
                log.info('Guardado consolidado %s',transaction_id)
                return payload
            except Exception:
                log.exception('Falló el guardado; se conserva el estado recuperable')
                if not prepared and not os.path.exists(self.journal):
                    shutil.rmtree(folder)
                raise

    def _prune(self, current):
        parent = os.path.dirname(self._generation(current))
        generations = []
        for entry in os.scandir(parent):
            if entry.is_dir(follow_symlinks=False) and re.fullmatch('[0-9a-f]{32}',entry.name):
                if os.path.isfile(os.path.join(entry.path,'committed.json')) or entry.name == current:
                    generations.append(entry)
                else:
                    shutil.rmtree(entry.path)
        generations.sort(key=lambda e:e.stat().st_mtime_ns,reverse=True)
        for entry in generations[2:]:
            if entry.name != current:
                shutil.rmtree(entry.path)

    def load(self, selected_path):
        with project_lock(self.root):
            selected_path = contained_path(self.root, selected_path)
            recovered = self.recover(check_live=True)
            if os.path.isfile(self.head):
                _, _, payload = self._validate(self._read_pointer(self.head))
            else:
                try:
                    payload = migrate_payload(read_json(selected_path))
                except (OSError,json.JSONDecodeError,UnicodeError):
                    # Legacy: usar sólo la copia secundaria validada; no adivinar datos.
                    secondary = contained_path(self.root,'config/project.json',allow_absolute=False)
                    if os.path.abspath(selected_path) == secondary:
                        raise
                    payload = migrate_payload(read_json(secondary))
                    recovered = {'reason':'secondary_state','files':[os.path.relpath(selected_path,self.root)]}
                    self.last_recovery = recovered
            inventory_path = contained_path(self.root,'config/inventario.json',allow_absolute=False)
            issues = []
            if os.path.isfile(inventory_path):
                inventory = read_json(inventory_path)
                if inventory_schema(inventory) is not None:
                    issues = verify_inventory(self.root,inventory)
            if issues:
                payload.setdefault('integrity_events',[]).append({'detected_at':datetime.now(timezone.utc).isoformat(),'issues':issues})
                log.warning('Integridad: %d entradas/resultados modificados o ausentes',len(issues))
            return payload, recovered, issues

    def export(self, target):
        """ZIP atómico sin generaciones/locks ni respaldos recursivos."""
        with project_lock(self.root):
            self.recover()
            inventory_path = contained_path(self.root,'config/inventario.json',allow_absolute=False)
            if os.path.isfile(inventory_path):
                manifest = read_json(inventory_path)
                if inventory_schema(manifest) is not None and verify_inventory(self.root,manifest):
                    raise ValueError('Archivos modificados después del guardado; guardá el proyecto antes de exportar')
            target = os.path.abspath(os.fspath(target))
            with atomic_output(target) as temporary:
                with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
                    for rel,path in project_files(self.root,include_legacy=True):
                        if path in (target,temporary): continue
                        archive.write(path,rel)
                with zipfile.ZipFile(temporary) as archive:
                    if archive.testzip() is not None:
                        raise ValueError('No pudo verificarse la exportación')
            return target
