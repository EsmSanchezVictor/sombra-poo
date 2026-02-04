"""Flujo de trabajo de proyectos: crear, abrir, guardar, exportar e importar."""

from __future__ import annotations

import json
import os
import zipfile
from tkinter import filedialog, messagebox

from core.project import Project


class ProjectManager:
    """Orquesta operaciones sobre proyectos y su estado."""

    def __init__(self, app, app_state=None, settings_manager=None):
        self.app = app
        self.app_state = app_state
        self.settings_manager = settings_manager or getattr(app, "settings_manager", None)
        self.current_project: Project | None = None
        self.projects_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proyectos"))

    def new_project(self) -> None:
        """Inicia un proyecto vacío, preservando la UI."""
        if not self.app._confirm_discard_changes("Nuevo proyecto"):
            return
        self.app._reset_scene()
        self.app._reset_vars_to_defaults()
        self.current_project = None
        self.app.current_project_path = None
        self.app.is_dirty = False

    def open_project(self) -> None:
        """Abre un proyecto desde un JSON."""
        file_path = filedialog.askopenfilename(
            title="Abrir proyecto",
            filetypes=[("Proyecto JSON", "*.json")],
        )
        if not file_path:
            return
        payload = self._load_project_file(file_path)
        if not payload:
            return
        project = Project.from_config_path(file_path)
        project.ensure_structure()
        project.next_n = int(payload.get("next_n", 1))
        self.app_state.apply_payload(payload)
        self.current_project = project
        self.app.current_project_path = project.config_path
        self.app.is_dirty = False
        self._update_last_project_path(project.config_path)

    def save_project(self) -> None:
        """Guarda el proyecto actual o solicita un destino."""
        if self.current_project:
            self._save_project_file(self.current_project.config_path)
            return
        self.save_project_as()

    def save_project_as(self) -> None:
        """Solicita destino y guarda el proyecto."""
        file_path = filedialog.asksaveasfilename(
            title="Guardar proyecto",
            defaultextension=".json",
            filetypes=[("Proyecto JSON", "*.json")],
        )
        if not file_path:
            return
        project = self._project_from_user_path(file_path)
        project.ensure_structure()
        self.current_project = project
        self.app.current_project_path = project.config_path
        self._update_last_project_path(project.config_path)
        self._save_project_file(project.config_path)

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
        config_path = os.path.join(target_dir, "config", "project.json")
        if not os.path.exists(config_path):
            messagebox.showerror("Importación", "El paquete no contiene config/project.json.")
            return
        payload = self._load_project_file(config_path)
        if not payload:
            return
        project = Project.from_config_path(config_path)
        project.ensure_structure()
        project.next_n = int(payload.get("next_n", 1))
        self.app_state.apply_payload(payload)
        self.current_project = project
        self.app.current_project_path = project.config_path
        self.app.is_dirty = False
        self._update_last_project_path(project.config_path)

    def _save_project_file(self, path: str) -> None:
        """Escribe el JSON de proyecto."""
        if not self.current_project:
            return
        payload = self.app_state.build_payload(self.current_project)
        self.current_project.next_n = int(payload.get("next_n", self.current_project.next_n))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        self.app.is_dirty = False
        self._update_last_project_path(path)

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