"""Flujo de trabajo de proyectos: crear, abrir, guardar, exportar e importar."""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog

from core.file_versioning import safe_path
from core.project import Project
from ui import dialogs


class ProjectManager:
    """Orquesta operaciones sobre proyectos y su estado."""

    def __init__(self, app, app_state=None, settings_manager=None):
        self.app = app
        self.app_state = app_state
        self.settings_manager = settings_manager or getattr(app, "settings_manager", None)
        self.current_project: Project | None = None
        self.projects_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proyectos"))

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
        project_dir = os.path.join(self.projects_root, name)
        if os.path.exists(project_dir):
            messagebox.showwarning("Nuevo proyecto", "Ya existe un proyecto con ese nombre.")
            return
        project = Project(project_dir)
        project.ensure_structure()
        self.current_project = project
        self.app.current_project_path = project.state_path
        self.app._reset_scene()
        self.app._reset_vars_to_defaults()
        self.app.apply_project_location(location)
        self.app.is_dirty = False
        self._save_project_file(project.state_path)
        self._update_last_project_path(project.state_path)
        self.app.on_project_loaded()

    def open_project(self) -> None:
        """Abre un proyecto desde un JSON."""
        file_path = self._select_project_path()
        if not file_path:
            return
        self.open_project_from_path(file_path)

    def open_project_from_path(self, file_path: str) -> bool:
        """Abre un proyecto desde una ruta de estado/config."""
        payload = self._load_project_file(file_path)
        if not payload:
            return False
        project = Project.from_config_path(file_path)
        project.ensure_structure()
        project.next_n = int(payload.get("next_n", 1))
        self.current_project = project
        self.app_state.apply_payload(payload)        
        self.app.current_project_path = file_path
        self.app.is_dirty = False
        self._update_last_project_path(file_path)
        self.app.on_project_loaded()
        return True
    def save_project(self) -> bool:
        """Guarda el proyecto actual o solicita un destino."""
        if self.current_project:
            return self._save_project_file(self.current_project.state_path)
        self.save_project_as()
        return False

    def save_project_as(self) -> None:
        """NO-OP temporal para guardar como."""
        messagebox.showinfo(
            "Guardar como",
            "Guardar como se implementará luego; use Exportar .3es",
        )


    def duplicate_project(self) -> bool:
        """Duplica el proyecto actual bajo /proyectos."""
        if not self.current_project:
            messagebox.showerror("Duplicar proyecto", "No hay un proyecto abierto para duplicar.")
            return False
        new_name = simpledialog.askstring("Duplicar proyecto", "Nombre del proyecto duplicado:", parent=self.app.root)
        if not new_name:
            return False
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Duplicar proyecto", "El nombre del proyecto no puede estar vacío.")
            return False

        source_root = self.current_project.root_path
        target_dir = self._next_available_project_dir(new_name)
        try:
            shutil.copytree(source_root, target_dir)
            state_path = os.path.join(target_dir, "config", "estado.json")
            payload = self._load_project_file(state_path) if os.path.exists(state_path) else {}
            meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
            meta["name"] = new_name
            meta["cloned_from"] = self.current_project.name
            meta["saved_at"] = datetime.now().isoformat(timespec="seconds")
            payload["meta"] = meta
            payload["name"] = new_name
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)

            config_path = os.path.join(target_dir, "config", "project.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            messagebox.showerror("Duplicar proyecto", f"No se pudo duplicar el proyecto: {exc}")
            return False

        if messagebox.askyesno("Duplicar proyecto", "Proyecto duplicado correctamente. ¿Desea abrirlo ahora?"):
            return self.open_project_from_path(state_path)
        return True

    def export_project(self) -> bool:
        """Exporta el proyecto a un archivo .3es."""
        if not self.current_project:
            messagebox.showerror("Exportar .3es", "No hay un proyecto abierto para exportar.")
            return False
        if not self.save_project():
            return False
        file_path = filedialog.asksaveasfilename(
            title="Exportar proyecto",
            defaultextension=".3es",
            filetypes=[("Proyecto 3Esfera", "*.3es")],
        )
        if not file_path:
            return False
        try:
            root_path = self.current_project.root_path
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for folder, _dirs, files in os.walk(root_path):
                    for filename in files:
                        full_path = os.path.join(folder, filename)
                        rel_path = os.path.relpath(full_path, root_path)
                        archive.write(full_path, arcname=rel_path)
            return True
        except Exception as exc:
            messagebox.showerror("Exportar .3es", f"No se pudo exportar el proyecto: {exc}")
            return False

    def import_project(self) -> bool:
        """Importa un archivo .3es y ofrece abrirlo al finalizar."""
        file_path = filedialog.askopenfilename(
            title="Importar proyecto",
            filetypes=[("Proyecto 3Esfera", "*.3es")],
        )
        if not file_path:
            return False

        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                names = archive.namelist()
                state_member = self._find_state_member(names)
                if not state_member:
                    messagebox.showerror("Importar .3es", "El paquete no contiene config/estado.json ni config/project.json.")
                    return False

                with archive.open(state_member) as state_handle:
                    payload = json.loads(state_handle.read().decode("utf-8"))

                suggested_name = payload.get("meta", {}).get("name") or payload.get("name") or os.path.splitext(os.path.basename(file_path))[0]
                target_dir = self._next_available_project_dir(suggested_name)
                archive.extractall(target_dir)

            source_path = self._find_state_path_in_dir(target_dir)
            if not source_path:
                messagebox.showerror("Importar .3es", "No se encontró el estado del proyecto luego de importar.")
                return False

            if messagebox.askyesno("Importar .3es", "Importación completa. ¿Desea abrir el proyecto ahora?"):
                return self.open_project_from_path(source_path)
            return True
        except zipfile.BadZipFile:
            messagebox.showerror("Importar .3es", "El archivo seleccionado no es un ZIP válido.")
            return False
        except Exception as exc:
            messagebox.showerror("Importar .3es", f"No se pudo importar el proyecto: {exc}")
            return False

    def _save_project_file(self, path: str) -> bool:
        """Escribe el JSON de proyecto."""
        if not self.current_project:
            return False
        try:
            payload = self.app_state.build_payload(self.current_project)
            self.current_project.next_n = int(payload.get("next_n", self.current_project.next_n))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            state_path = safe_path(os.path.dirname(path), os.path.basename(path))
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            with open(self.current_project.config_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            self._sync_excel_copies()
            self.app.is_dirty = False
            self.app.current_project_path = str(state_path)
            self._update_last_project_path(str(state_path))
            self.app.update_status_saved_time(payload.get("meta", {}).get("saved_at"))
            return True
        except Exception as exc:
            messagebox.showerror("Guardar proyecto", f"No se pudo guardar el proyecto: {exc}")
            return False

    def _load_project_file(self, path: str) -> dict | None:
        """Lee un JSON de proyecto con control de errores."""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Error", f"No se pudo abrir el proyecto: {exc}")
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
            filetypes=[("Proyecto JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if file_path:
            return file_path
        folder = filedialog.askdirectory(title="Abrir carpeta de proyecto")
        if not folder:
            return None
        config_dir = os.path.join(folder, "config")
        state_files = sorted(
            [f for f in os.listdir(config_dir)] if os.path.isdir(config_dir) else []
        )
        state_candidates = [f for f in state_files if f.startswith("estado") and f.endswith(".json")]
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
        candidate = os.path.join(config_dir, "project.json")
        if os.path.exists(candidate):
            return candidate
        messagebox.showerror("Abrir proyecto", "No se encontró config/estado.json o config/project.json.")
        return None

    def _find_state_path_in_dir(self, root_dir: str) -> str | None:
        direct_state = os.path.join(root_dir, "config", "estado.json")
        direct_project = os.path.join(root_dir, "config", "project.json")
        if os.path.exists(direct_state):
            return direct_state
        if os.path.exists(direct_project):
            return direct_project
        for folder, _dirs, files in os.walk(root_dir):
            if "estado.json" in files and os.path.basename(folder) == "config":
                return os.path.join(folder, "estado.json")
            if "project.json" in files and os.path.basename(folder) == "config":
                return os.path.join(folder, "project.json")
        return None

    def _find_state_member(self, members: list[str]) -> str | None:
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
        safe_name = "_".join(base_name.strip().split()) or "proyecto"
        candidate = os.path.join(self.projects_root, safe_name)
        if not os.path.exists(candidate):
            return candidate
        version = 2
        while True:
            candidate = os.path.join(self.projects_root, f"{safe_name}_v{version}")
            if not os.path.exists(candidate):
                return candidate
            version += 1


    def _sync_excel_copies(self) -> None:
        if not self.current_project:
            return
        planos_dir = os.path.join(self.current_project.root_path, "Planos")
        modelos_dir = os.path.join(self.current_project.root_path, "modelos")
        os.makedirs(planos_dir, exist_ok=True)
        os.makedirs(modelos_dir, exist_ok=True)
        if self.app.last_edit_excel_path and os.path.exists(self.app.last_edit_excel_path):
            target = safe_path(planos_dir, os.path.basename(self.app.last_edit_excel_path))
            shutil.copy2(self.app.last_edit_excel_path, target)
            self.app.last_edit_excel_path = str(target)
        if self.app.last_model_excel_path and os.path.exists(self.app.last_model_excel_path):
            target = safe_path(modelos_dir, os.path.basename(self.app.last_model_excel_path))
            shutil.copy2(self.app.last_model_excel_path, target)
            self.app.last_model_excel_path = str(target)