"""Representa la estructura física de un proyecto en disco.

CAMBIOS:
- `ensure_structure()` creaba `resultados/histograma` (singular), pero
  `services/snapshot_service.py` guarda ahí usando
  `resultados/histogramas` (plural) — corregido.
- `ensure_structure()` NO creaba las carpetas `matrices/` ni `excels/`,
  pese a que `snapshot_service.py::save_snapshot()` SÍ escribe ahí
  (la matriz de selección vía `to_excel`, y las copias de excel de
  modelo/edición vía `shutil.copy`). Ninguna de las dos funciones crea
  la carpeta destino si falta, así que en proyectos reales esas
  carpetas nunca llegaban a existir y esos guardados fallaban en
  silencio. Agregadas.
- El archivo índice principal del proyecto (`state_path`) ahora vive
  DIRECTAMENTE en la carpeta del proyecto y se llama como el proyecto
  (ej. `proyectos/mm/mm.sombra`), en vez de `config/estado.json` — un
  nombre genérico igual en todos los proyectos, escondido una carpeta
  adentro, imposible de identificar navegando las carpetas a mano.
  `config/project.json` se sigue escribiendo como copia secundaria
  para no romper proyectos ya guardados con el esquema anterior.
"""
from __future__ import annotations

import os

from core.project_layout import ProjectLayout


class Project:
    """Gestiona rutas, carpeta base y numeración incremental."""

    def __init__(self, root_path: str, config_path: str | None = None):
        self.root_path = root_path
        self.config_path = config_path or os.path.join(root_path, "config", "project.json")
        self.state_path = os.path.join(root_path, f"{self.name}.sombra")
        self.next_n = 1

    @classmethod
    def from_config_path(cls, config_path: str) -> "Project":
        """Crea el proyecto a partir de CUALQUIER archivo índice: el nuevo
        "<nombre>.sombra" en la raíz del proyecto, o los legacy
        config/project.json / config/estado.json.

        BUG CORREGIDO (el causante real de "no hay forma de volver a
        cargar un proyecto"): antes esta función solo reconocía que
        `config_path` estaba dentro de una carpeta `config/` cuando el
        archivo se llamaba exactamente "project.json". El criterio ahora
        es: si el archivo vive directamente dentro de una carpeta
        llamada "config" (sin importar su nombre), la raíz del proyecto
        es un nivel arriba de esa carpeta "config"; si no, el archivo ya
        está en la raíz del proyecto (caso del nuevo "<nombre>.sombra").
        """
        config_dir = os.path.dirname(config_path)
        if os.path.basename(config_dir) == "config":
            root_path = os.path.dirname(config_dir)
        else:
            root_path = os.path.dirname(config_path)
        # Desde v19, una vez resuelta la raíz todas las rutas de estado son
        # canónicas. El archivo recibido se usa solo para localizar/cargar el
        # proyecto; no debe convertirse en la ruta secundaria permanente.
        return cls(root_path)

    @property
    def name(self) -> str:
        """Nombre legible del proyecto."""
        return os.path.basename(self.root_path) or "Proyecto"

    @property
    def layout(self) -> ProjectLayout:
        return ProjectLayout(self.root_path)

    def ensure_structure(self) -> None:
        """Crea/migra la estructura lógica v19 del proyecto."""
        self.layout.ensure()
        self.layout.migrate_basic_legacy()

    def allocate_n(self) -> int:
        """Obtiene el siguiente índice incremental para snapshots."""
        n = self.next_n
        self.next_n += 1
        return n
