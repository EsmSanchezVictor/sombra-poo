"""Contenedor unificado para las vistas 2D y 3D.

La visualización de cada modo (Edición / Modelo) vive dentro del mismo frame
principal mediante un ttk.Notebook.  La pestaña 2D conserva Matplotlib y la
pestaña 3D aloja VTK de forma embebida en Tkinter.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class VisualizationHost:
    """Notebook 2D/3D embebido en un frame existente."""

    def __init__(self, parent: tk.Misc, palette: dict | None = None):
        self.parent = parent
        self.palette = palette or {}
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        bg = self.palette.get("panel", "white")
        self.frame_2d = tk.Frame(self.notebook, bg=bg)
        self.frame_3d = tk.Frame(self.notebook, bg=bg)
        self.notebook.add(self.frame_2d, text="Vista 2D")
        self.notebook.add(self.frame_3d, text="Vista 3D")

        self.scene_3d = None

    def exists(self) -> bool:
        try:
            return bool(self.notebook.winfo_exists())
        except tk.TclError:
            return False

    def select_2d(self):
        if self.exists():
            self.notebook.select(self.frame_2d)

    def select_3d(self):
        if self.exists():
            self.notebook.select(self.frame_3d)

    def ensure_3d_scene(self):
        if self.scene_3d is None:
            from ui.scene3d_vtk import VTKSceneView
            self.scene_3d = VTKSceneView(self.frame_3d, palette=self.palette)
        return self.scene_3d

    def render_3d(self, vars_dict: dict, app=None, title: str = "Vista 3D"):
        scene = self.ensure_3d_scene()
        # Seleccionar primero para que Tk ya conozca el tamaño real del Canvas
        # antes de pedirle a VTK el primer render.
        self.select_3d()
        try:
            self.parent.update_idletasks()
        except tk.TclError:
            pass
        scene.render(vars_dict, app=app, title=title)
        return scene

    def close(self):
        if self.scene_3d is not None:
            try:
                self.scene_3d.close()
            except Exception:
                pass
            self.scene_3d = None
