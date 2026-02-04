"""Representa la estructura física de un proyecto en disco."""

from __future__ import annotations

import os


class Project:
    """Gestiona rutas, carpeta base y numeración incremental."""

    def __init__(self, root_path: str, config_path: str | None = None):
        self.root_path = root_path
        self.config_path = config_path or os.path.join(root_path, "config", "project.json")
        self.next_n = 1

    @classmethod
    def from_config_path(cls, config_path: str) -> "Project":
        """Crea el proyecto a partir de un path a project.json."""
        config_dir = os.path.dirname(config_path)
        if os.path.basename(config_path) == "project.json" and os.path.basename(config_dir) == "config":
            root_path = os.path.dirname(config_dir)
        else:
            root_path = os.path.dirname(config_path)
        return cls(root_path, config_path)

    @property
    def name(self) -> str:
        """Nombre legible del proyecto."""
        return os.path.basename(self.root_path) or "Proyecto"

    def ensure_structure(self) -> None:
        """Crea la estructura estándar de carpetas."""
        for folder in ("imagenes", "curvas", "matrices", "mascaras", "excels", "config"):
            os.makedirs(os.path.join(self.root_path, folder), exist_ok=True)

    def allocate_n(self) -> int:
        """Obtiene el siguiente índice incremental para snapshots."""
        n = self.next_n
        self.next_n += 1
        return n