import json
import os
import shutil
import zipfile
from typing import Any, Dict, Optional

from core.app_state import AppState
from core.project import Project


class ProjectManager:
    def __init__(self, app_name: str, base_dir: Optional[str] = None) -> None:
        self.app_name = app_name
        self.base_dir = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "proyectos")
        self.current_project: Optional[Project] = None
        self.current_project_path: Optional[str] = None
        self.next_n = 1

    def new_project(self) -> None:
        self.current_project = None
        self.current_project_path = None
        self.next_n = 1

    def _project_root_from_path(self, json_path: str) -> str:
        return os.path.splitext(json_path)[0]

    def load_project(self, path: str, defaults: Dict[str, Any]) -> Optional[AppState]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if data.get("version") != 1:
            return None
        vars_data = AppState.merge_vars(defaults, data.get("vars", {}))
        state = AppState(
            vars=vars_data,
            ui=data.get("ui", {}),
            scene=data.get("scene", {}),
            next_n=int(data.get("next_n", 1)),
        )
        self.next_n = state.next_n
        self.current_project_path = path
        self.current_project = Project(self._project_root_from_path(path))
        return state

    def save_project(self, path: str, state: AppState) -> None:
        project = Project(self._project_root_from_path(path))
        project.ensure_structure()
        name = os.path.splitext(os.path.basename(path))[0]
        payload = state.to_dict(self.app_name, name)
        payload["next_n"] = state.next_n
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        with open(project.config_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        self.current_project = project
        self.current_project_path = path
        self.next_n = state.next_n

    def export_project(self, project: Project, destination_path: str) -> None:
        project.ensure_structure()
        base_name = os.path.splitext(destination_path)[0]
        archive_path = f"{base_name}.3es"
        shutil.make_archive(base_name, "zip", project.root_path)
        if os.path.exists(archive_path):
            os.remove(archive_path)
        os.rename(f"{base_name}.zip", archive_path)

    def import_project(self, archive_path: str) -> Optional[str]:
        os.makedirs(self.base_dir, exist_ok=True)
        name = os.path.splitext(os.path.basename(archive_path))[0]
        dest_root = os.path.join(self.base_dir, name)
        if os.path.exists(dest_root):
            shutil.rmtree(dest_root)
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(dest_root)
        config_path = os.path.join(dest_root, "config", "project.json")
        if os.path.exists(config_path):
            return config_path
        return None