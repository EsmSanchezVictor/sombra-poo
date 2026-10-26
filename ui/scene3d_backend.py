"""Disponibilidad, diagnóstico y fallback de VTK; no crea controladores."""
from __future__ import annotations
import platform
import sys
import tkinter as tk
from core.scene3d_data import Scene3DData

def vtk_backend_available() -> bool:
    """True si el wheel VTK contiene el renderer OpenGL estándar requerido."""
    try:
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
        from vtkmodules.vtkRenderingCore import vtkRenderWindow  # noqa: F401
        from vtkmodules.vtkFiltersSources import vtkSphereSource  # noqa: F401
        return True
    except Exception:
        return False


def vtk_installation_info() -> str:
    """Resumen corto para diagnóstico; no inicializa un render."""
    try:
        import vtk
        version = getattr(vtk, "__version__", None) or vtk.vtkVersion.GetVTKVersion()
    except Exception as exc:
        return f"VTK no importable: {type(exc).__name__}: {exc}"
    return (
        f"VTK {version} · Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
        f"· {platform.system()} {platform.release()}"
    )


def _render_matplotlib_fallback(parent: tk.Misc, data: Scene3DData, vtk_error: Exception | None) -> None:
    from ui.scene3d_fallback import render_matplotlib_fallback
    return render_matplotlib_fallback(parent,data,vtk_error)

