import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class Project:
    root_path: str

    def __post_init__(self) -> None:
        self.root_path = os.path.abspath(self.root_path)
        self.config_dir = os.path.join(self.root_path, "config")
        self.images_dir = os.path.join(self.root_path, "imagenes")
        self.curves_dir = os.path.join(self.root_path, "curvas")
        self.matrices_dir = os.path.join(self.root_path, "matrices")
        self.masks_dir = os.path.join(self.root_path, "mascaras")
        self.excels_dir = os.path.join(self.root_path, "excels")

    def ensure_structure(self) -> None:
        for path in (
            self.root_path,
            self.config_dir,
            self.images_dir,
            self.curves_dir,
            self.matrices_dir,
            self.masks_dir,
            self.excels_dir,
        ):
            os.makedirs(path, exist_ok=True)

    @property
    def config_path(self) -> str:
        return os.path.join(self.config_dir, "project.json")

    def allocate_n(self, state: Dict[str, int]) -> int:
        current = int(state.get("next_n", 1))
        state["next_n"] = current + 1
        return current