"""Render 3D embebido para Proyecto Sombra.

v29: la vista 3D deja de abrir una ventana independiente y se renderiza
adentro del mismo ``Frame`` Tkinter que la vista 2D (mediante pestañas).

Backend preferido: VTK estándar en modo off-screen. Esta estrategia usa el
motor VTK real (mallas, iluminación, cámara, Phong, antialiasing) pero evita
``vtkRenderingTk``, que no está incluido de forma consistente en los wheels
binarios de VTK. La imagen renderizada se presenta dentro de un widget Tk y
se actualiza al rotar/zoom/redimensionar.

Si VTK no está instalado o falla el contexto OpenGL, hay un fallback
Matplotlib 3D, también embebido en el mismo frame.

IMPORTANTE: este módulo es solamente visual. Consume ``X``, ``Y`` y ``T`` ya
calculados por los kernels existentes; no modifica ninguna ecuación física,
parámetro científico ni dato persistido.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any
from core.scene3d_data import Scene3DData, _optional_float, _finite_range, _scene_extent, _temperature_display, scene_data_from_vars
from ui.scene3d_backend import vtk_backend_available, vtk_installation_info, _render_matplotlib_fallback
from ui.scene3d_controller import _VTKOffscreenSceneController


def _clear_frame(frame: tk.Misc) -> None:
    old = getattr(frame, "_sombra_scene3d_controller", None)
    if old is not None:
        try:
            old.close()
        except Exception:
            pass
        try:
            delattr(frame, "_sombra_scene3d_controller")
        except Exception:
            pass
    for widget in frame.winfo_children():
        try:
            widget.destroy()
        except tk.TclError:
            pass


def render_scene_3d(vars_dict: dict[str, Any], frame: tk.Misc, *, title: str) -> str:
    """Renderiza la escena dentro de ``frame`` y devuelve el backend usado."""
    if "T" not in vars_dict or "X" not in vars_dict or "Y" not in vars_dict:
        raise ValueError("Primero genere el gráfico 2D")

    data = scene_data_from_vars(vars_dict, title)
    _clear_frame(frame)

    if vtk_backend_available():
        try:
            controller = _VTKOffscreenSceneController(frame, data)
            setattr(frame, "_sombra_scene3d_controller", controller)
            return "VTK"
        except Exception as exc:
            _clear_frame(frame)
            _render_matplotlib_fallback(frame, data, vtk_error=exc)
            return "Matplotlib (fallback)"

    _render_matplotlib_fallback(frame, data, vtk_error=None)
    return "Matplotlib (fallback)"

