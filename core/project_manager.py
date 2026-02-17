"""Flujo de trabajo de proyectos: crear, abrir, guardar, exportar e importar."""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from tkinter import filedialog, messagebox

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
        payload = self._load_project_file(file_path)
        if not payload:
            return
        project = Project.from_config_path(file_path)
        project.ensure_structure()
        project.next_n = int(payload.get("next_n", 1))
        self.current_project = project
        self.app_state.apply_payload(payload)        
        self.app.current_project_path = file_path
        self.app.is_dirty = False
        self._update_last_project_path(file_path)
        self.app.on_project_loaded()

    def save_project(self) -> None:
        """Guarda el proyecto actual o solicita un destino."""
        if self.current_project:
            self._save_project_file(self.current_project.state_path)
            return
        self.save_project_as()

    def save_project_as(self) -> None:
        """NO-OP temporal para guardar como."""
        messagebox.showinfo(
            "Guardar como",
            "Guardar como se implementará luego; use Exportar .3es",
        )


    def export_project(self) -> None:
        """Exporta el proyecto a un archivo .3es."""
        if not self.current_project:
            messagebox.showwarning("Proyecto", "No hay un proyecto abierto para exportar.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Exportar proyecto",
            defaultextension=".3es",
            filetypes=[("Proyecto 3Esfera", "*.3es")],
        )
        if not file_path:
            return
        root_path = self.current_project.root_path
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for folder, _dirs, files in os.walk(root_path):
                for filename in files:
                    full_path = os.path.join(folder, filename)
                    rel_path = os.path.relpath(full_path, root_path)
                    archive.write(full_path, rel_path)

    def import_project(self) -> None:
        """Importa un archivo .3es y lo abre automáticamente."""
        file_path = filedialog.askopenfilename(
            title="Importar proyecto",
            filetypes=[("Proyecto 3Esfera", "*.3es")],
        )
        if not file_path:
            return
        os.makedirs(self.projects_root, exist_ok=True)
        project_name = os.path.splitext(os.path.basename(file_path))[0]
        target_dir = os.path.join(self.projects_root, project_name)
        if os.path.exists(target_dir):
            messagebox.showwarning("Importación", "Ya existe un proyecto con ese nombre.")
            return
        with zipfile.ZipFile(file_path, "r") as archive:
            archive.extractall(target_dir)
        state_path = os.path.join(target_dir, "config", "estado.json")            
        config_path = os.path.join(target_dir, "config", "project.json")
        source_path = state_path if os.path.exists(state_path) else config_path
        if not os.path.exists(source_path):
            messagebox.showerror("Importación", "El paquete no contiene config/estado.json ni config/project.json.")
            return
        payload = self._load_project_file(source_path)
        if not payload:
            return
        project = Project.from_config_path(source_path)
        project.ensure_structure()
        project.next_n = int(payload.get("next_n", 1))
        self.current_project = project
        self.app_state.apply_payload(payload)        
        self.app.current_project_path = source_path
        self.app.is_dirty = False
        self._update_last_project_path(source_path)

    def _save_project_file(self, path: str) -> None:
        """Escribe el JSON de proyecto."""
        if not self.current_project:
            return
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