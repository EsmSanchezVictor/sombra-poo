"""Diagnóstico mínimo de VTK/OpenGL para Proyecto Sombra v31.

Ejecutar desde la carpeta del proyecto con:
    python DIAGNOSTICO_VTK_WINDOWS.py

No modifica archivos ni cálculos del proyecto.
"""
from __future__ import annotations

import platform
import sys
import traceback


def main() -> int:
    print("=== Proyecto Sombra · diagnóstico VTK ===")
    print("Python:", sys.version.replace("\n", " "))
    print("Ejecutable:", sys.executable)
    print("Sistema:", platform.platform())
    try:
        import vtk
        print("VTK:", getattr(vtk, "__version__", vtk.vtkVersion.GetVTKVersion()))
    except Exception:
        print("ERROR importando VTK:")
        traceback.print_exc()
        return 2

    try:
        rw = vtk.vtkRenderWindow()
        rw.SetOffScreenRendering(1)
        rw.SetMultiSamples(0)
        ren = vtk.vtkRenderer()
        ren.SetBackground(0.2, 0.3, 0.4)
        rw.AddRenderer(ren)
        rw.SetSize(240, 180)
        print("RenderWindow:", rw.GetClassName())
        rw.Render()
        print("OffScreenRendering:", rw.GetOffScreenRendering())
        try:
            print("SupportsOpenGL:", bool(rw.SupportsOpenGL()))
        except Exception as exc:
            print("SupportsOpenGL: no disponible:", exc)
        try:
            caps = rw.ReportCapabilities()
            if caps:
                print("--- Capacidades OpenGL ---")
                print(caps)
        except Exception as exc:
            print("ReportCapabilities no disponible:", exc)
        rw.Finalize()
        print("RESULTADO: VTK pudo crear y renderizar un contexto OpenGL.")
        return 0
    except Exception:
        print("ERROR inicializando/renderizando VTK:")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
