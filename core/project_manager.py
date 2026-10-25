"""Flujo de trabajo de proyectos: crear, abrir, guardar, exportar e importar."""

from __future__ import annotations

import json
import logging
from core.project_schema import migrate_payload
from core.project_lock import project_lock
from services.project_storage import read_json
from core.project_integrity import verify_inventory
from core.safe_io import atomic_write_json
import os
import shutil
import zipfile
import tempfile
import sqlite3
from core.safe_paths import (safe_component, contained_path, safe_project_reference,
                             sanitize_payload, sanitize_entry, validate_analysis_id)
from core.project_archive import validate_archive, extract_validated_archive
from datetime import datetime
from tkinter import filedialog, messagebox

from core.project import Project
from ui import dialogs
from ui.modal_style import ask_text


log = logging.getLogger("sombra.projects")

class ProjectManager:
    """Orquesta operaciones sobre proyectos y su estado."""

    def __init__(self, app, app_state=None, settings_manager=None):
        self.app = app
        self.app_state = app_state
        self.settings_manager = settings_manager or getattr(app, "settings_manager", None)
        self.current_project: Project | None = None
        self.projects_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proyectos"))
        self._autosave_after_id = None
        self._autosave_in_progress = False
        self._max_backups = 10

    def new_project(self) -> None:
        """Crea un proyecto con nombre y ubicación."""
        if not self.app._confirm_discard_changes("Nuevo proyecto"):
            return
        name = dialogs.ask_project_name(self.app.root)
        if not name:
            return
        location = dialogs.ask_project_location(self.app.root, self.app.locations_data)
        if not location:
            messagebox.showwarning("Nuevo proyecto", "Debe seleccionar una ubicación válida.")
            return
        try:
            project_dir = contained_path(self.projects_root, safe_component(name), allow_absolute=False)
        except ValueError as exc:
            messagebox.showerror("Nuevo proyecto", str(exc))
            return
        if os.path.exists(project_dir):
            messagebox.showwarning("Nuevo proyecto", "Ya existe un proyecto con ese nombre.")
            return
        project = Project(project_dir)
        project.ensure_structure()
        self.current_project = project
        self.app.current_project_path = project.state_path
        previous_tracking = getattr(self.app, "_suspend_autosave_tracking", False)
        self.app._suspend_autosave_tracking = True
        try:
            self.app._reset_scene()
            self.app._reset_vars_to_defaults()
            self.app.apply_project_location(location)
        finally:
            self.app._suspend_autosave_tracking = previous_tracking
        self.app.is_dirty = False
        self.app.project_integrity_events = []
        if not self._save_project_file(project.state_path, autosave=True):
            return
        self._update_last_project_path(project.state_path)
        self.app.on_project_loaded("created")

    def open_project(self) -> None:
        """Abre un proyecto desde un JSON."""
        file_path = self._select_project_path()
        if not file_path:
            return
        self.open_project_from_path(file_path)

    def open_project_from_path(self, file_path: str, project_action: str = "opened") -> bool:
        """Abre un proyecto desde una ruta de estado/config."""
        project = Project.from_config_path(file_path)
        try:
            payload, recovered, issues = project.storage.load(file_path)
            payload = sanitize_payload(project.root_path,payload)
            project.ensure_structure()
            payload = self._prepare_payload_for_layout(project,payload)
        except (ValueError,TypeError,OSError,KeyError) as exc:
            log.exception('No se pudo abrir/verificar el proyecto')
            messagebox.showerror('Abrir proyecto',str(exc))
            return False
        if recovered:
            messagebox.showwarning('Proyecto recuperado','Se recuperó un conjunto válido de estado, escenas y análisis.\nLos archivos divergentes se preservaron cuando existían.' + (f"\nCopias preservadas en: {os.path.join(project.root_path,recovered['preserved_at'])}" if recovered.get('preserved_at') else ''))
        if issues:
            names = ', '.join(item['path'] for item in issues[:5])
            messagebox.showwarning('Integridad del proyecto',f'{len(issues)} archivos modificados o ausentes desde el último guardado: {names}.\nEl incidente queda registrado; revisá los resultados asociados.')
        self.app.project_integrity_events = payload.get('integrity_events',[])
        project.next_n = int(payload.get("next_n", 1))
        self.current_project = project
        previous_tracking = getattr(self.app, "_suspend_autosave_tracking", False)
        self.app._suspend_autosave_tracking = True
        try:
            self.app_state.apply_payload(payload)
        finally:
            self.app._suspend_autosave_tracking = previous_tracking
        # Desde v19 la ruta canónica es siempre <proyecto>/<proyecto>.sombra,
        # incluso cuando se abrió un config/project.json legacy.
        self.app.current_project_path = project.state_path
        self.app.is_dirty = False
        self._update_last_project_path(project.state_path)
        self.app.on_project_loaded(project_action)
        # Persistir inmediatamente la migración de rutas/estructura.
        self._save_project_file(project.state_path, autosave=True)
        return True
    def schedule_autosave(self, delay_ms: int = 900) -> None:
        """Programa guardado automático consolidado sin abrir diálogos."""
        if not self.current_project or self._autosave_in_progress:
            return
        root = getattr(self.app, "root", None)
        if root is None:
            return
        if self._autosave_after_id is not None:
            try:
                root.after_cancel(self._autosave_after_id)
            except Exception:
                pass
        self._autosave_after_id = root.after(delay_ms, self.autosave_project)

    def autosave_project(self) -> bool:
        """Actualiza estado + archivos de trabajo en sus rutas fijas."""
        self._autosave_after_id = None
        if not self.current_project or self._autosave_in_progress:
            return False
        self._autosave_in_progress = True
        try:
            return self._save_project_file(self.current_project.state_path, autosave=True)
        finally:
            self._autosave_in_progress = False

    def save_project(self) -> bool:
        """Guardar = consolidar y crear un respaldo local, sin preguntar ruta.

        El estado vivo ya se autosalva. Ctrl+S/botón Guardar actúa como
        respaldo explícito y crea un .3es timestampado en ``respaldos/``.
        """
        if not self.current_project:
            return bool(self.save_project_as())
        if not self._save_project_file(self.current_project.state_path, autosave=False):
            return False
        backup = self._create_backup()
        if not backup:
            messagebox.showerror("Respaldo", "El estado quedó guardado, pero no se pudo crear el respaldo solicitado.")
            return False
        if backup and hasattr(self.app, "status_saved_var"):
            self.app.status_saved_var.set(
                f"Último guardado: {datetime.now().isoformat(sep=' ', timespec='seconds')} · respaldo creado"
            )
        return True

    def save_project_as(self) -> bool:
        """Copia el proyecto completo a un nuevo destino y lo abre.

        Esta es la única acción de guardado que solicita ubicación.
        """
        if not self.current_project:
            messagebox.showwarning("Guardar como", "Primero cree o abra un proyecto.")
            return False
        selected = filedialog.asksaveasfilename(
            title="Guardar proyecto como",
            defaultextension=".sombra",
            filetypes=[("Proyecto sombra", "*.sombra")],
            initialfile=f"{self.current_project.name}.sombra",
        )
        if not selected:
            return False
        if not self.autosave_project():
            return False
        base_name = os.path.splitext(os.path.basename(selected))[0].strip() or "proyecto"
        try:
            safe_component(base_name)
        except ValueError as exc:
            messagebox.showerror("Guardar como", str(exc))
            return False
        parent = os.path.dirname(os.path.abspath(selected))
        target_root = os.path.join(parent, base_name)
        if os.path.exists(target_root):
            messagebox.showerror("Guardar como", f"Ya existe la carpeta:\n{target_root}")
            return False
        try:
            from services.project_copy import copy_project
            state_path = copy_project(self.current_project,target_root)
        except Exception as exc:
            log.exception('No se pudo preparar Guardar como')
            messagebox.showerror('Guardar como',f'No se pudo crear la copia: {exc}')
            return False
        return self.open_project_from_path(state_path,project_action='save_as')

    def duplicate_project(self) -> bool:
        """Duplica el proyecto actual bajo /proyectos."""
        if not self.current_project:
            messagebox.showerror("Duplicar proyecto", "No hay un proyecto abierto para duplicar.")
            return False
        new_name = ask_text(self.app.root, "Duplicar proyecto", "Ingresá el nombre de la copia:", accept_text="Duplicar")
        if not new_name:
            return False
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Duplicar proyecto", "El nombre del proyecto no puede estar vacío.")
            return False

        if not self.autosave_project():
            return False
        try:
            from services.project_copy import copy_project
            target_dir = self._next_available_project_dir(new_name)
            state_path = copy_project(self.current_project,target_dir)
        except Exception as exc:
            log.exception('No se pudo preparar la copia')
            messagebox.showerror('Duplicar proyecto',f'No se pudo duplicar: {exc}')
            return False
        if messagebox.askyesno('Duplicar proyecto','Proyecto duplicado correctamente. ¿Desea abrirlo ahora?'):
            return self.open_project_from_path(state_path,project_action='duplicated')
        return True

    def export_project(self) -> bool:
        """Exporta el proyecto a un archivo .3es."""
        if not self.current_project:
            messagebox.showerror("Exportar .3es", "No hay un proyecto abierto para exportar.")
            return False
        if not self.autosave_project():
            return False
        file_path = filedialog.asksaveasfilename(
            title="Exportar proyecto",
            defaultextension=".3es",
            filetypes=[("Proyecto 3Esfera", "*.3es")],
        )
        if not file_path:
            return False
        try:
            self.current_project.storage.export(file_path)
            return True
        except Exception as exc:
            messagebox.showerror("Exportar .3es", f"No se pudo exportar el proyecto: {exc}")
            return False

    def import_project(self) -> bool:
        """Importa un paquete validado y ofrece abrirlo al finalizar."""
        file_path = filedialog.askopenfilename(title="Importar proyecto",
            filetypes=[("Proyecto 3Esfera", "*.3es")])
        if not file_path:
            return False
        try:
            source_path = self.import_archive(file_path)
            if messagebox.askyesno("Importar .3es", "Importación completa. ¿Desea abrir el proyecto ahora?"):
                return self.open_project_from_path(source_path, project_action="imported")
            return True
        except Exception as exc:
            messagebox.showerror("Importar .3es", f"No se pudo importar el proyecto: {exc}")
            return False

    def import_archive(self, file_path):
        """Valida y prepara todo antes de publicar una carpeta de proyecto."""
        os.makedirs(self.projects_root, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as archive:
            infos = validate_archive(archive)
            if any('.sombra-recovery' in info.filename.replace('\\','/').split('/') or info.filename.replace('\\','/').endswith('config/save.lock') for info in infos):
                raise ValueError('El paquete incluye controles internos de recuperación; exportalo desde la aplicación')
            member = self._find_state_member([i.filename for i in infos if not i.is_dir()])
            if not member:
                raise ValueError("El paquete no contiene un estado de proyecto.")
            info = archive.getinfo(member)
            if info.file_size > 8 * 1024 * 1024:
                raise ValueError("El estado JSON supera el límite permitido.")
            with archive.open(info) as handle:
                payload = json.loads(handle.read(8 * 1024 * 1024 + 1).decode("utf-8"))
            payload = migrate_payload(payload)
            suggested_name = (payload.get("meta") or {}).get("name") or payload.get("name") or os.path.splitext(os.path.basename(file_path))[0]
            target = self._next_available_project_dir(safe_component(suggested_name))
            with tempfile.TemporaryDirectory(prefix=".sombra-import-", dir=self.projects_root) as staging:
                extract_validated_archive(archive, staging)
                state = contained_path(staging, member.replace("\\", "/"), allow_absolute=False)
                source_root = Project.from_config_path(state).root_path
                # Un envoltorio de carpeta legacy es válido si contiene todos los archivos.
                for folder, dirs, files in os.walk(staging):
                    for name in files:
                        contained_path(source_root, os.path.join(folder, name))
                payload = sanitize_payload(source_root, payload, strict=True)
                db = os.path.join(source_root, "analisis", "analisis.sqlite3")
                if not os.path.isfile(db):
                    db = os.path.join(source_root, "datos", "analisis.sqlite3")
                if os.path.isfile(db):
                    from pathlib import Path
                    conn = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
                    try:
                        conn.execute("PRAGMA trusted_schema=OFF")
                        from core.project_schema import validate_analysis_schema
                        validate_analysis_schema(conn)
                        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            raise ValueError("Base de análisis dañada.")
                        for aid, raw in conn.execute("SELECT analysis_id,payload_json FROM analysis_records"):
                            validate_analysis_id(aid)
                            sanitize_entry(source_root, json.loads(raw), strict=True)
                    finally:
                        conn.close()
                inventory_path = os.path.join(source_root,'config','inventario.json')
                if os.path.isfile(inventory_path):
                    manifest = read_json(inventory_path)
                    if manifest.get('integrity_schema_version') is not None:
                        if verify_inventory(source_root,manifest):
                            raise ValueError('El paquete no coincide con su inventario SHA256')
                # El JSON importado ya contiene únicamente referencias relativas confinadas.
                # La copia se valida sin reescribirla: su hash sigue siendo verificable.
                relative_state = os.path.relpath(state, source_root)
                os.rename(source_root, target)
        return contained_path(target, relative_state, allow_absolute=False)

    def _save_project_file(self, path: str, *, autosave: bool = False) -> bool:
        """Publica el conjunto recuperable; sólo después actualiza indicadores."""
        if not self.current_project:
            return False
        committed = False
        try:
            project = self.current_project
            with project_lock(project.root_path):
                project.ensure_structure()
                payload = migrate_payload(self.app_state.build_payload(project))
                write_scenes = hasattr(self.app,'vars') and hasattr(self.app,'vars_modelo')
                if write_scenes:
                    payload.setdefault('paths',{}).update(edit_excel='escena/edicion.xlsx',model_excel='escena/modelo.xlsx')
                # Incidentes detectados al abrir siguen visibles en guardados posteriores.
                events = getattr(self.app,'project_integrity_events',None)
                if events:
                    payload['integrity_events'] = events
                from services.scene_persistence import write_scene
                payload = project.storage.commit(path,payload,
                    scene_writer=(lambda kind, target: write_scene(kind,target,self.app)) if write_scenes else None)
                committed = True
                project.next_n = payload.get('next_n',project.next_n)
                if write_scenes:
                    self.app.last_edit_excel_path = project.layout.edit_excel
                    self.app.last_model_excel_path = project.layout.model_excel
            self.app.is_dirty = False
            self.app.current_project_path = project.state_path
            self._update_last_project_path(project.state_path)
            self.app.update_status_saved_time(payload.get('meta',{}).get('saved_at'))
            touch = getattr(self.app,'_touch_session',None)
            if callable(touch): touch()
            return True
        except Exception as exc:
            if committed:
                self.app.is_dirty = False
                log.exception('Proyecto guardado; falló una actualización auxiliar')
                messagebox.showwarning('Proyecto guardado','El proyecto quedó guardado, pero no se pudieron actualizar todas las preferencias o indicadores.')
                return True
            self.app.is_dirty = True
            log.exception('No se pudo consolidar el proyecto')
            messagebox.showerror('Guardar proyecto',f'No se pudo completar el guardado: {exc}\nEl estado anterior y la recuperación se conservan.')
            return False

    def _prepare_payload_for_layout(self, project: Project, payload: dict) -> dict:
        """Adapta rutas legacy a la estructura v19 sin perder datos."""
        payload = sanitize_payload(project.root_path, payload)
        paths = dict(payload.get("paths") or {})
        root = project.root_path
        layout = project.layout

        def _src(key):
            value = paths.get(key)
            if not value:
                return None
            return safe_project_reference(root, value)

        def _copy_scene(key, target, legacy_dirs):
            source = _src(key)
            if not source or not os.path.exists(source):
                candidates = []
                for rel in legacy_dirs:
                    folder = os.path.join(root, rel)
                    if os.path.isdir(folder):
                        candidates.extend(
                            candidate for f in os.listdir(folder) if f.lower().endswith(".xlsx")
                            if (candidate := safe_project_reference(root, os.path.join(folder, f)))
                        )
                source = max(candidates, key=os.path.getmtime) if candidates else None
            if source and os.path.exists(source):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                if os.path.abspath(source) != os.path.abspath(target):
                    shutil.copy2(source, target)
                paths[key] = os.path.relpath(target, root)

        _copy_scene("edit_excel", layout.edit_excel, ("Planos", "excels"))
        _copy_scene("model_excel", layout.model_excel, ("modelos", "excels"))

        # Una vez consolidados los Excel activos, las carpetas antiguas ya no
        # forman parte del esquema vivo. Se preservan completas para auditoría
        # en _legacy_v18, sin borrar información silenciosamente.
        for legacy_rel in ("Planos", "modelos", "excels"):
            try:
                layout.archive_legacy_folder(legacy_rel)
            except Exception:
                pass

        image = paths.get("current_image")
        if image:
            candidate = os.path.join(layout.images_dir, os.path.basename(image))
            if os.path.exists(candidate):
                paths["current_image"] = os.path.relpath(candidate, root)
        met = paths.get("meteorology_csv")
        if met:
            candidate = os.path.join(layout.meteorology_dir, os.path.basename(met))
            if os.path.exists(candidate):
                paths["meteorology_csv"] = os.path.relpath(candidate, root)
        paths["analysis_database"] = os.path.relpath(layout.analysis_db, root)
        payload["paths"] = paths
        payload["layout_version"] = 2
        return payload

    def _load_project_file(self, path: str) -> dict | None:
        """Lee un JSON de proyecto con control de errores."""
        try:
            return migrate_payload(read_json(path))
        except (OSError,ValueError) as exc:
            log.exception('Lectura de estado inválida')
            messagebox.showerror('Error',f'No se pudo abrir el proyecto: {exc}')
            return None

    def _update_last_project_path(self, path: str) -> None:
        """Actualiza settings.json con el último proyecto."""
        self.app.settings["last_project_path"] = path
        if self.settings_manager:
            self.settings_manager.write(self.app.settings)

    def _project_from_user_path(self, file_path: str) -> Project:
        """Normaliza rutas para asegurar config/project.json."""
        if os.path.basename(file_path) != "project.json":
            root_path = os.path.splitext(file_path)[0]
            return Project(root_path)
        return Project.from_config_path(file_path)

    def _select_project_path(self) -> str | None:
        file_path = filedialog.askopenfilename(
            title="Abrir proyecto",
            filetypes=[
                ("Proyecto sombra-poo", "*.sombra"),
                ("Proyecto JSON (legacy)", "*.json"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if file_path:
            return file_path
        folder = filedialog.askdirectory(title="Abrir carpeta de proyecto")
        if not folder:
            return None
        return self._find_state_path_in_dir(folder)

    def _find_state_path_in_dir(self, root_dir: str) -> str | None:
        """Ubica el archivo índice de un proyecto dentro de una carpeta.

        Orden de búsqueda:
        1. `<nombre_de_la_carpeta>.sombra` directamente en la raíz —
           el esquema nuevo, donde el archivo se llama como el proyecto.
        2. Cualquier otro `*.sombra` suelto en la raíz (por si la carpeta
           fue renombrada después de crear el proyecto).
        3. Esquema legacy: `config/estado*.json` (tomando la versión más
           alta si hay varias, remanente del bug de versionado ya
           corregido) o `config/project.json`.
        """
        folder_name = os.path.basename(os.path.normpath(root_dir))
        named_candidate = os.path.join(root_dir, f"{folder_name}.sombra")
        if os.path.exists(named_candidate):
            return named_candidate

        if os.path.isdir(root_dir):
            sombra_files = sorted(f for f in os.listdir(root_dir) if f.endswith(".sombra"))
            if sombra_files:
                return os.path.join(root_dir, sombra_files[0])

        config_dir = os.path.join(root_dir, "config")
        if os.path.isdir(config_dir):
            state_candidates = [
                f for f in os.listdir(config_dir) if f.startswith("estado") and f.endswith(".json")
            ]
            if state_candidates:
                def _ver(name: str) -> int:
                    stem = os.path.splitext(name)[0]
                    if "_v" not in stem:
                        return 1
                    try:
                        return int(stem.rsplit("_v", 1)[1])
                    except ValueError:
                        return 1
                selected = max(state_candidates, key=_ver)
                return os.path.join(config_dir, selected)
            project_json = os.path.join(config_dir, "project.json")
            if os.path.exists(project_json):
                return project_json

        for folder, _dirs, files in os.walk(root_dir):
            if os.path.basename(folder) == "config":
                if "estado.json" in files:
                    return os.path.join(folder, "estado.json")
                if "project.json" in files:
                    return os.path.join(folder, "project.json")
        return None

    def _find_state_member(self, members: list[str]) -> str | None:
        sombra_members = [m for m in members if m.replace("\\", "/").endswith(".sombra")]
        if sombra_members:
            # Preferir el que esté en la raíz del zip (no dentro de una subcarpeta)
            raiz = [m for m in sombra_members if "/" not in m.replace("\\", "/")]
            return (raiz or sombra_members)[0]
        for candidate in ("config/estado.json", "config/project.json"):
            if candidate in members:
                return candidate
        for member in members:
            normalized = member.replace("\\", "/")
            if normalized.endswith("config/estado.json") or normalized.endswith("config/project.json"):
                return member
        return None

    def _next_available_project_dir(self, base_name: str) -> str:
        os.makedirs(self.projects_root, exist_ok=True)
        safe_name = "_".join(safe_component(base_name).split())
        candidate = contained_path(self.projects_root, safe_name, allow_absolute=False)
        if not os.path.exists(candidate):
            return candidate
        version = 2
        while True:
            candidate = contained_path(self.projects_root, safe_component(f"{safe_name}_v{version}"), allow_absolute=False)
            if not os.path.exists(candidate):
                return candidate
            version += 1


    def _save_workspace_files(self) -> bool:
        """Compatibilidad: guarda el conjunto completo mediante el mismo protocolo."""
        return bool(self.current_project and self._save_project_file(self.current_project.state_path,autosave=True))

    def _create_backup(self) -> str | None:
        """Crea un .3es en respaldos/ sin incluir respaldos previos."""
        if not self.current_project:
            return None
        layout = self.current_project.layout
        layout.ensure()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target = os.path.join(layout.backups_dir, f"{self.current_project.name}_{stamp}.3es")
        try:
            self.current_project.storage.export(target)
            backups = sorted(
                [os.path.join(layout.backups_dir, f) for f in os.listdir(layout.backups_dir) if f.lower().endswith(".3es")],
                key=os.path.getmtime, reverse=True,
            )
            for old in backups[self._max_backups:]:
                try: os.remove(old)
                except OSError: pass
            return target
        except Exception as exc:
            log.exception("No se pudo crear el respaldo")
            return None
