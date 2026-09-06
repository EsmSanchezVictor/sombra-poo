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

import math
import os
import platform
import sys
import tkinter as tk
import traceback
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageTk
from matplotlib import colormaps
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from core.species import color_copa
from plot_style import CMAP_TEMPERATURA
from ui.solar_indicator import add_solar_indicator_2d


@dataclass(frozen=True)
class Scene3DData:
    X: np.ndarray
    Y: np.ndarray
    temperature: np.ndarray
    trees: tuple[Any, ...]
    structures: tuple[Any, ...]
    temperature_unit: str
    title: str
    solar_altitude_deg: float | None = None
    solar_azimuth_deg: float | None = None


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


def _optional_float(value: Any) -> float | None:
    if hasattr(value, "get"):
        try:
            value = value.get()
        except Exception:
            return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _finite_range(values: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = float(np.min(finite)), float(np.max(finite))
    if math.isclose(lo, hi, rel_tol=0.0, abs_tol=1e-12):
        eps = max(0.01, abs(lo) * 1e-6)
        return lo - eps, hi + eps
    return lo, hi


def _scene_extent(data: Scene3DData) -> tuple[float, float, float, float, float]:
    xmin = float(np.nanmin(data.X))
    xmax = float(np.nanmax(data.X))
    ymin = float(np.nanmin(data.Y))
    ymax = float(np.nanmax(data.Y))
    max_height = 1.0
    for tree in data.trees:
        max_height = max(max_height, float(getattr(tree, "h", 0.0) or 0.0))
    for structure in data.structures:
        max_height = max(max_height, float(getattr(structure, "altura", 0.0) or 0.0))
    return xmin, xmax, ymin, ymax, max_height


def _temperature_display(vars_dict: dict[str, Any]) -> tuple[np.ndarray, str]:
    T = np.asarray(vars_dict["T"], dtype=np.float32)
    app = vars_dict.get("_app_instance")
    if app is not None:
        return (
            np.asarray(app.convert_temperature_for_display(T), dtype=np.float32),
            app.get_temperature_unit_symbol(),
        )
    return T, "K"


def scene_data_from_vars(vars_dict: dict[str, Any], title: str) -> Scene3DData:
    """Construye los datos visuales a partir de resultados YA calculados."""
    X = np.asarray(vars_dict["X"], dtype=np.float32)
    Y = np.asarray(vars_dict["Y"], dtype=np.float32)
    temperature, unit = _temperature_display(vars_dict)
    return Scene3DData(
        X=X,
        Y=Y,
        temperature=temperature,
        trees=tuple(vars_dict.get("arboles", ()) or ()),
        structures=tuple(vars_dict.get("estructuras", ()) or ()),
        temperature_unit=unit,
        title=title,
        solar_altitude_deg=_optional_float(vars_dict.get("_render_solar_altitude_deg")),
        solar_azimuth_deg=_optional_float(vars_dict.get("_render_solar_azimuth_deg")),
    )


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


class _VTKOffscreenSceneController:
    """VTK real + presentación en Tk, sin depender de vtkRenderingTk.

    El RenderWindow trabaja off-screen. Cada cuadro se copia a una imagen RGBA
    y se muestra en un ``Label`` Tk. La cámara VTK se controla con eventos Tk:
    arrastre izquierdo = rotar, rueda = zoom.
    """

    MIN_WIDTH = 360
    MIN_HEIGHT = 260

    # v30: los hosts 2D/3D ocupan todo el bloque central. Para acercar el
    # widget a la nitidez del render de validación, los cuadros estáticos se
    # generan con supersampling moderado y luego se reducen al tamaño real.
    # Durante el arrastre se usa 1x; el límite evita picos innecesarios de RAM.
    QUALITY_RENDER_SCALE = 1.35
    MAX_RENDER_PIXELS = 2_600_000

    def __init__(self, parent: tk.Misc, data: Scene3DData):
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
        from vtkmodules.vtkCommonCore import vtkLookupTable, vtkPoints
        from vtkmodules.vtkCommonDataModel import vtkStructuredGrid
        from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkTubeFilter
        from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkCylinderSource, vtkLineSource, vtkSphereSource
        from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor, vtkScalarBarActor
        from vtkmodules.vtkRenderingCore import (
            vtkActor,
            vtkDataSetMapper,
            vtkLight,
            vtkPolyDataMapper,
            vtkRenderer,
            vtkRenderWindow,
            vtkWindowToImageFilter,
        )
        from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy

        self._parent = parent
        self._data = data
        self._renderer = vtkRenderer()
        self._render_window = vtkRenderWindow()
        self._image_filter = vtkWindowToImageFilter()
        self._vtk_to_numpy = vtk_to_numpy
        self._photo = None
        self._resize_after = None
        self._drag_origin: tuple[int, int] | None = None
        self._closed = False
        self._last_size = (0, 0)
        self._initial_render_after = None
        self._platform_is_windows = sys.platform.startswith("win")

        toolbar = tk.Frame(parent, bd=0)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Label(toolbar, text="Motor 3D: VTK", anchor="w").pack(
            side=tk.LEFT, padx=(6, 12), pady=3
        )
        tk.Button(toolbar, text="Isométrica", command=self.view_isometric).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        tk.Button(toolbar, text="Superior", command=self.view_top).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        tk.Button(toolbar, text="Reencuadrar", command=self.reset_camera).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        solar_summary = ""
        if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
            solar_summary = f" · ☀ Az {data.solar_azimuth_deg:.0f}° · El {data.solar_altitude_deg:.0f}°"
        tk.Label(
            toolbar,
            text=f"Arrastrar: rotar · Rueda: zoom{solar_summary}",
            anchor="e",
            fg="#555555",
        ).pack(side=tk.RIGHT, padx=8)

        self._image_label = tk.Label(parent, bd=0, highlightthickness=0)
        self._image_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._image_label.bind("<ButtonPress-1>", self._on_drag_start)
        self._image_label.bind("<B1-Motion>", self._on_drag_motion)
        self._image_label.bind("<ButtonRelease-1>", self._on_drag_end)
        self._image_label.bind("<MouseWheel>", self._on_mousewheel)
        self._image_label.bind("<Button-4>", lambda _e: self._zoom(1.10))
        self._image_label.bind("<Button-5>", lambda _e: self._zoom(0.90))
        self._image_label.bind("<Configure>", self._on_configure)

        render_window = self._render_window
        render_window.SetOffScreenRendering(1)
        # v31: algunos drivers de Windows fallan al crear el contexto OpenGL
        # cuando MSAA se solicita antes del primer Render(). VTK documenta
        # este problema. En Windows arrancamos con MSAA=0 y conservamos la
        # calidad mediante supersampling + LANCZOS. En otros sistemas se
        # mantiene MSAA 8x, ya validado en v29/v30.
        render_window.SetMultiSamples(0 if self._platform_is_windows else 8)
        render_window.AddRenderer(self._renderer)

        renderer = self._renderer
        # Cielo ligeramente más profundo. Es una decisión exclusivamente visual.
        renderer.SetBackground(0.94, 0.97, 1.00)
        renderer.SetBackground2(0.56, 0.72, 0.86)
        renderer.GradientBackgroundOn()
        # FXAA se evita en el RenderWindow off-screen: en algunos drivers
        # (incluido el wheel validado) produce un frame negro. Se conserva
        # MSAA del RenderWindow para suavizado de bordes.
        # Depth peeling se evita deliberadamente en el backend off-screen:
        # algunos drivers/wheels dejan de dibujar actores 3D cuando se combina
        # con multisampling. La mezcla alfa estándar es más estable aquí.

        # --- Plano térmico: EXACTAMENTE X/Y/T ya calculados ---
        X, Y, T = data.X, data.Y, data.temperature
        if X.shape != Y.shape or X.shape != T.shape:
            raise ValueError("X, Y y T deben tener la misma forma para la vista 3D")
        ny, nx = X.shape
        xyz = np.column_stack(
            [X.ravel(order="C"), Y.ravel(order="C"), np.zeros(X.size, dtype=np.float32)]
        ).astype(np.float32, copy=False)
        points = vtkPoints()
        points.SetData(numpy_to_vtk(xyz, deep=True))
        grid = vtkStructuredGrid()
        grid.SetDimensions(nx, ny, 1)
        grid.SetPoints(points)
        scalars = numpy_to_vtk(
            T.ravel(order="C").astype(np.float32, copy=False), deep=True
        )
        scalars.SetName("Temperatura")
        grid.GetPointData().SetScalars(scalars)

        lo, hi = _finite_range(T)
        lut = vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(lo, hi)
        cmap = colormaps.get_cmap(CMAP_TEMPERATURA)
        for idx in range(256):
            r, g, b, a = cmap(idx / 255.0)
            lut.SetTableValue(idx, float(r), float(g), float(b), float(a))
        lut.Build()

        ground_mapper = vtkDataSetMapper()
        ground_mapper.SetInputData(grid)
        ground_mapper.SetScalarRange(lo, hi)
        ground_mapper.SetLookupTable(lut)
        ground_mapper.ScalarVisibilityOn()
        ground = vtkActor()
        ground.SetMapper(ground_mapper)
        # v33: la temperatura se presenta como una capa analítica superpuesta
        # al terreno físico, no como el material del suelo. 50 % de opacidad
        # mejora la separación visual sin modificar ni interpolar la matriz T.
        ground.GetProperty().SetOpacity(0.50)
        # La capa analítica no recibe iluminación: así conserva los colores de
        # la escala térmica y no se confunde con el material físico del suelo.
        ground.GetProperty().LightingOff()
        renderer.AddActor(ground)

        xmin, xmax, ymin, ymax, max_height = _scene_extent(data)
        span_x = max(1.0, xmax - xmin)
        span_y = max(1.0, ymax - ymin)
        span = max(span_x, span_y)

        # Fuente/mapper de cubo reutilizada para base y estructuras.
        cube_source = vtkCubeSource()
        cube_source.SetXLength(1.0)
        cube_source.SetYLength(1.0)
        cube_source.SetZLength(1.0)
        cube_mapper = vtkPolyDataMapper()
        cube_mapper.SetInputConnection(cube_source.GetOutputPort())

        # Base fina debajo del plano: da espesor visual sin tocar T.
        base = vtkActor()
        base.SetMapper(cube_mapper)
        base_thickness = max(0.12, span * 0.004)
        base.SetScale(span_x, span_y, base_thickness)
        base.SetPosition(
            (xmin + xmax) / 2,
            (ymin + ymax) / 2,
            -base_thickness / 2 - 0.01,
        )
        # Terreno físico neutro: queda visible bajo la capa térmica translúcida.
        # El tono claro evita competir con la escala de temperatura.
        base.GetProperty().SetColor(0.93, 0.93, 0.90)
        base.GetProperty().SetAmbient(0.30)
        base.GetProperty().SetDiffuse(0.70)
        base.GetProperty().SetSpecular(0.03)
        renderer.AddActor(base)

        # Isotermas: refuerzo gráfico de la lectura térmica. Se generan a
        # partir de la MISMA matriz T ya calculada; no se recalcula física.
        # Se usan niveles uniformes dentro del rango visible para adaptarse a
        # cualquier escenario y se elevan apenas para evitar z-fighting.
        if hi > lo:
            contours = vtkContourFilter()
            contours.SetInputData(grid)
            contours.GenerateValues(6, lo, hi)
            # Doble trazo: borde oscuro + línea coloreada por temperatura.
            # Así la capa térmica sigue al 50 %, pero cada isoterma conserva
            # saturación completa y se distingue de los objetos físicos.
            contour_outline_mapper = vtkPolyDataMapper()
            contour_outline_mapper.SetInputConnection(contours.GetOutputPort())
            contour_outline_mapper.ScalarVisibilityOff()
            contour_outline = vtkActor()
            contour_outline.SetMapper(contour_outline_mapper)
            contour_outline.SetPosition(0.0, 0.0, max(0.008, span * 0.00035))
            contour_outline.GetProperty().SetColor(0.12, 0.12, 0.12)
            contour_outline.GetProperty().SetOpacity(0.62)
            contour_outline.GetProperty().SetLineWidth(2.6)
            contour_outline.GetProperty().SetAmbient(1.0)
            contour_outline.GetProperty().SetDiffuse(0.0)
            renderer.AddActor(contour_outline)

            contour_mapper = vtkPolyDataMapper()
            contour_mapper.SetInputConnection(contours.GetOutputPort())
            contour_mapper.SetLookupTable(lut)
            contour_mapper.SetScalarRange(lo, hi)
            contour_mapper.ScalarVisibilityOn()
            contour_actor = vtkActor()
            contour_actor.SetMapper(contour_mapper)
            contour_actor.SetPosition(0.0, 0.0, max(0.010, span * 0.00042))
            contour_actor.GetProperty().SetOpacity(1.0)
            contour_actor.GetProperty().SetLineWidth(1.45)
            contour_actor.GetProperty().LightingOff()
            renderer.AddActor(contour_actor)

        sphere_source = vtkSphereSource()
        sphere_source.SetRadius(1.0)
        # Una única malla más suave se reutiliza para todas las copas.
        sphere_source.SetThetaResolution(32)
        sphere_source.SetPhiResolution(24)
        sphere_mapper = vtkPolyDataMapper()
        sphere_mapper.SetInputConnection(sphere_source.GetOutputPort())

        cyl_source = vtkCylinderSource()
        cyl_source.SetRadius(1.0)
        cyl_source.SetHeight(1.0)
        cyl_source.SetResolution(24)
        cyl_mapper = vtkPolyDataMapper()
        cyl_mapper.SetInputConnection(cyl_source.GetOutputPort())

        # Árboles: dimensiones horizontales y altura total respetan los datos;
        # la forma elipsoidal de copa es solamente una convención gráfica.
        for tree in data.trees:
            x = float(getattr(tree, "x", 0.0))
            y = float(getattr(tree, "y", 0.0))
            h = max(0.2, float(getattr(tree, "h", 1.0) or 1.0))
            radius = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
            crown_z_radius = max(0.2, min(radius * 0.72, h * 0.34))
            crown_center_z = max(crown_z_radius, h - crown_z_radius)
            trunk_height = max(0.15, crown_center_z - crown_z_radius * 0.78)
            trunk_radius = max(0.06, min(radius * 0.10, h * 0.035))

            trunk = vtkActor()
            trunk.SetMapper(cyl_mapper)
            trunk.SetScale(trunk_radius, trunk_height, trunk_radius)
            trunk.RotateX(90.0)  # vtkCylinderSource está orientado en Y.
            trunk.SetPosition(x, y, trunk_height / 2.0)
            trunk.GetProperty().SetColor(0.34, 0.20, 0.10)
            trunk.GetProperty().SetInterpolationToPhong()
            trunk.GetProperty().SetAmbient(0.28)
            trunk.GetProperty().SetDiffuse(0.72)
            trunk.GetProperty().SetSpecular(0.08)
            renderer.AddActor(trunk)

            try:
                canopy_rgb = to_rgb(color_copa(getattr(tree, "especie", "")))
            except Exception:
                canopy_rgb = (0.18, 0.48, 0.16)
            rho = _optional_float(getattr(tree, "rho_copa", None))
            # La copa debe leerse como objeto físico por encima de la capa
            # térmica. Conservamos una leve variación por densidad, pero con
            # opacidad alta para que no se funda con el mapa de temperatura.
            opacity = 0.96 if rho is None else min(0.995, max(0.92, 0.90 + 0.095 * rho))

            # v30: copa multilobulada. La elipsoide única de v29 se veía
            # demasiado geométrica. Los cinco lóbulos quedan contenidos
            # dentro del radio de copa y de la altura originales: solo cambia
            # la representación visual, nunca la geometría usada en cálculos.
            lobe_specs = (
                (0.00, 0.00, 0.00, 0.78, 0.78, 1.00, 1.00),
                (0.28, 0.02, -0.05, 0.68, 0.64, 0.72, 0.92),
                (-0.27, -0.03, -0.04, 0.66, 0.69, 0.74, 1.05),
                (0.01, 0.28, -0.08, 0.64, 0.67, 0.70, 0.86),
                (-0.03, -0.27, -0.06, 0.68, 0.63, 0.72, 0.98),
            )
            for dx, dy, dz, sx, sy, sz, tint in lobe_specs:
                canopy = vtkActor()
                canopy.SetMapper(sphere_mapper)
                canopy.SetScale(radius * sx, radius * sy, crown_z_radius * sz)
                canopy.SetPosition(
                    x + radius * dx,
                    y + radius * dy,
                    crown_center_z + crown_z_radius * dz,
                )
                canopy.GetProperty().SetColor(
                    *tuple(min(1.0, max(0.0, c * tint)) for c in canopy_rgb)
                )
                canopy.GetProperty().SetOpacity(opacity)
                canopy.GetProperty().SetInterpolationToPhong()
                canopy.GetProperty().SetAmbient(0.18)
                canopy.GetProperty().SetDiffuse(0.82)
                canopy.GetProperty().SetSpecular(0.10)
                canopy.GetProperty().SetSpecularPower(20)
                renderer.AddActor(canopy)

        for structure in data.structures:
            tipo = str(getattr(structure, "tipo", ""))
            x1 = float(getattr(structure, "x1", 0.0))
            y1 = float(getattr(structure, "y1", 0.0))
            x2 = float(getattr(structure, "x2", x1))
            y2 = float(getattr(structure, "y2", y1))
            height = max(0.0, float(getattr(structure, "altura", 0.0) or 0.0))

            actor = vtkActor()
            actor.SetMapper(cube_mapper)
            if tipo == "Pared":
                dx, dy = x2 - x1, y2 - y1
                length = max(0.10, math.hypot(dx, dy))
                thickness = max(0.12, span * 0.003)
                wall_height = max(0.10, height)
                actor.SetScale(length, thickness, wall_height)
                actor.SetPosition((x1 + x2) / 2, (y1 + y2) / 2, wall_height / 2)
                actor.RotateZ(math.degrees(math.atan2(dy, dx)))
                actor.GetProperty().SetColor(0.52, 0.52, 0.50)
            else:
                width = max(0.10, abs(x2 - x1))
                depth = max(0.10, abs(y2 - y1))
                slab = max(0.06, span * 0.0025)
                if tipo == "Galeria":
                    actor.SetScale(width, depth, slab)
                    actor.SetPosition(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        max(slab / 2, height),
                    )
                    actor.GetProperty().SetColor(0.43, 0.28, 0.15)
                else:  # Sendero y otros rectángulos a ras del suelo.
                    actor.SetScale(width, depth, slab)
                    actor.SetPosition(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        slab / 2 + 0.015,
                    )
                    actor.GetProperty().SetColor(0.48, 0.48, 0.46)
            actor.GetProperty().SetOpacity(1.0)
            actor.GetProperty().SetInterpolationToPhong()
            actor.GetProperty().SetAmbient(0.24)
            actor.GetProperty().SetDiffuse(0.76)
            actor.GetProperty().SetSpecular(0.10)
            actor.GetProperty().SetSpecularPower(12)
            # Borde fino: ayuda a distinguir paredes, galerías y senderos
            # de la capa térmica sin cambiar su geometría.
            actor.GetProperty().EdgeVisibilityOn()
            actor.GetProperty().SetEdgeColor(0.16, 0.16, 0.16)
            actor.GetProperty().SetLineWidth(1.2)
            renderer.AddActor(actor)

        scalar_bar = vtkScalarBarActor()
        scalar_bar.SetLookupTable(lut)
        scalar_bar.SetTitle(f"Temperatura ({data.temperature_unit})")
        scalar_bar.SetNumberOfLabels(5)
        scalar_bar.SetMaximumWidthInPixels(105)
        scalar_bar.SetMaximumHeightInPixels(300)
        scalar_bar.SetPosition(0.88, 0.14)
        scalar_bar.GetTitleTextProperty().SetColor(0.12, 0.12, 0.12)
        scalar_bar.GetLabelTextProperty().SetColor(0.12, 0.12, 0.12)
        # v32: VTK 9.7 eliminó Renderer.AddActor2D(). vtkScalarBarActor
        # sigue siendo un vtkProp, por lo que AddViewProp() es la API compatible
        # tanto con VTK 9.6 como con 9.7+.
        renderer.AddViewProp(scalar_bar)

        axes = vtkCubeAxesActor()
        axes.SetBounds(xmin, xmax, ymin, ymax, 0.0, max_height)
        axes.SetCamera(renderer.GetActiveCamera())
        axes.SetXTitle("X (m)")
        axes.SetYTitle("Y (m)")
        axes.SetZTitle("Altura (m)")
        axes.SetFlyModeToOuterEdges()
        axes.SetXLabelFormat("%.0f")
        axes.SetYLabelFormat("%.0f")
        axes.SetZLabelFormat("%.1f")
        axes.GetProperty().SetColor(0.30, 0.30, 0.30)
        for axis_index in range(3):
            axes.GetTitleTextProperty(axis_index).SetColor(0.18, 0.18, 0.18)
            axes.GetLabelTextProperty(axis_index).SetColor(0.24, 0.24, 0.24)
        renderer.AddActor(axes)

        # Luz principal orientada con la geometría solar YA calculada, si
        # está disponible. Es iluminación visual; no genera nuevos resultados.
        center = ((xmin + xmax) / 2, (ymin + ymax) / 2, max_height * 0.35)
        key = vtkLight()
        key.SetPositional(False)
        if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
            alt = math.radians(data.solar_altitude_deg)
            azi = math.radians(data.solar_azimuth_deg)
            sx = math.sin(azi) * math.cos(alt)
            sy = math.cos(azi) * math.cos(alt)
            sz = max(0.15, math.sin(alt))
            distance = span * 4.0
            key.SetPosition(
                center[0] + sx * distance,
                center[1] + sy * distance,
                center[2] + sz * distance,
            )
        else:
            key.SetPosition(xmax + span, ymin - span, max_height + span)
        key.SetFocalPoint(*center)
        key.SetColor(1.00, 0.95, 0.86)
        key.SetIntensity(1.00)
        renderer.AddLight(key)

        fill = vtkLight()
        fill.SetPositional(False)
        fill.SetPosition(xmin - span, ymax + span, max_height + span * 0.6)
        fill.SetFocalPoint(*center)
        fill.SetColor(0.78, 0.86, 1.00)
        fill.SetIntensity(0.32)
        renderer.AddLight(fill)

        # Luz de recorte suave para separar vegetación y estructuras del fondo.
        rim = vtkLight()
        rim.SetPositional(False)
        rim.SetPosition(xmax + span * 0.5, ymax + span, max_height + span)
        rim.SetFocalPoint(*center)
        rim.SetColor(0.90, 0.95, 1.00)
        rim.SetIntensity(0.18)
        renderer.AddLight(rim)

        # Marcador solar representativo (opción 1): una esfera en el cielo
        # y una guía tenue hacia la escena. Usa azimut/elevación ya calculados.
        if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
            alt = math.radians(data.solar_altitude_deg)
            azi = math.radians(data.solar_azimuth_deg)
            sx = math.sin(azi) * math.cos(alt)
            sy = math.cos(azi) * math.cos(alt)
            sz = max(0.10, math.sin(alt))
            sun_distance = span * 2.15
            sun_pos = (
                center[0] + sx * sun_distance,
                center[1] + sy * sun_distance,
                center[2] + sz * sun_distance,
            )
            sun = vtkSphereSource()
            sun.SetRadius(max(0.20, span * 0.04))
            sun.SetThetaResolution(24)
            sun.SetPhiResolution(24)
            sun.SetCenter(*sun_pos)
            sun_mapper = vtkPolyDataMapper()
            sun_mapper.SetInputConnection(sun.GetOutputPort())
            sun_actor = vtkActor()
            sun_actor.SetMapper(sun_mapper)
            sun_actor.GetProperty().SetColor(1.00, 0.84, 0.22)
            sun_actor.GetProperty().SetAmbient(0.70)
            sun_actor.GetProperty().SetDiffuse(0.30)
            sun_actor.GetProperty().SetSpecular(0.10)
            renderer.AddActor(sun_actor)

            guide = vtkLineSource()
            guide.SetPoint1(*sun_pos)
            guide.SetPoint2(center[0] + sx * span * 0.35, center[1] + sy * span * 0.35, max(0.05, center[2] * 0.12))
            guide_tube = vtkTubeFilter()
            guide_tube.SetInputConnection(guide.GetOutputPort())
            guide_tube.SetRadius(max(0.03, span * 0.0035))
            guide_tube.SetNumberOfSides(12)
            guide_tube.CappingOn()
            guide_mapper = vtkPolyDataMapper()
            guide_mapper.SetInputConnection(guide_tube.GetOutputPort())
            guide_actor = vtkActor()
            guide_actor.SetMapper(guide_mapper)
            guide_actor.GetProperty().SetColor(0.86, 0.64, 0.16)
            guide_actor.GetProperty().SetOpacity(0.55)
            renderer.AddActor(guide_actor)

        self._image_filter.SetInput(render_window)
        self._image_filter.SetInputBufferTypeToRGB()
        self._image_filter.ReadFrontBufferOff()

        # Primera cámara y primer frame. El tamaño real se ajusta luego por
        # <Configure>; esto evita render 1x1 durante la construcción del tab.
        self._set_camera_isometric()
        # Ajuste automático al contenido: conserva la orientación elegida y
        # aprovecha mejor el viewport grande introducido en v30.
        renderer.ResetCamera()
        renderer.GetActiveCamera().Zoom(1.08)
        renderer.ResetCameraClippingRange()
        render_window.SetSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        # v31: no renderizar dentro del constructor. En Windows el tab de
        # ttk.Notebook puede no estar todavía mapeado y PhotoImage/OpenGL
        # pueden inicializarse demasiado pronto. Esperamos al ciclo idle.
        self._initial_render_after = self._image_label.after_idle(self._initial_render)

    def _initial_render(self) -> None:
        if self._closed:
            return
        self._initial_render_after = None
        try:
            # Forzar actualización geométrica del widget antes de crear el
            # primer contexto/render. No recalcula datos científicos.
            try:
                self._image_label.update_idletasks()
            except tk.TclError:
                pass
            self._render_to_tk(high_quality=True)
        except Exception as exc:
            # Si el contexto gráfico falla después de que el tab ya fue creado,
            # degradar realmente a Matplotlib y conservar el detalle visible.
            parent = self._parent
            try:
                self.close()
            except Exception:
                pass
            for widget in list(parent.winfo_children()):
                try:
                    widget.destroy()
                except Exception:
                    pass
            _render_matplotlib_fallback(parent, self._data, vtk_error=exc)

    def _show_runtime_error(self, exc: BaseException | None) -> None:
        """Reemplaza el lienzo por un diagnóstico accionable sin cerrar la app."""
        if self._closed:
            return
        detail = f"{type(exc).__name__}: {exc}" if exc is not None else "Error desconocido"
        try:
            self._image_label.configure(image="", text=(
                "VTK está instalado, pero no pudo crear/renderizar el contexto 3D.\n"
                f"{vtk_installation_info()}\n"
                f"Detalle: {detail}\n\n"
                "La aplicación continúa usando el fallback Matplotlib. "
                "Copie este detalle para diagnóstico."
            ), justify="left", anchor="nw", padx=12, pady=12)
        except Exception:
            pass

    # ---------- cámara/interacción ---------------------------------
    def _set_camera_isometric(self) -> None:
        xmin, xmax, ymin, ymax, max_height = _scene_extent(self._data)
        center = ((xmin + xmax) / 2, (ymin + ymax) / 2, max_height * 0.25)
        span = max(xmax - xmin, ymax - ymin, max_height, 1.0)
        cam = self._renderer.GetActiveCamera()
        cam.SetFocalPoint(*center)
        cam.SetPosition(
            center[0] + span * 1.15,
            center[1] - span * 1.35,
            center[2] + span * 0.95,
        )
        cam.SetViewUp(0, 0, 1)
        cam.SetViewAngle(35)

    def view_isometric(self) -> None:
        if self._closed:
            return
        self._set_camera_isometric()
        self._renderer.ResetCamera()
        self._renderer.GetActiveCamera().Zoom(1.08)
        self._renderer.ResetCameraClippingRange()
        self._render_to_tk(high_quality=True)

    def view_top(self) -> None:
        if self._closed:
            return
        xmin, xmax, ymin, ymax, max_height = _scene_extent(self._data)
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        span = max(xmax - xmin, ymax - ymin, 1.0)
        cam = self._renderer.GetActiveCamera()
        cam.SetFocalPoint(cx, cy, 0.0)
        cam.SetPosition(cx, cy, max(max_height + span * 1.8, span * 1.8))
        cam.SetViewUp(0, 1, 0)
        self._renderer.ResetCameraClippingRange()
        self._render_to_tk(high_quality=True)

    def reset_camera(self) -> None:
        if self._closed:
            return
        self._renderer.ResetCamera()
        self._renderer.GetActiveCamera().Zoom(1.05)
        self._renderer.ResetCameraClippingRange()
        self._render_to_tk(high_quality=True)

    def _on_drag_start(self, event) -> None:
        self._drag_origin = (int(event.x), int(event.y))

    def _on_drag_motion(self, event) -> None:
        if self._drag_origin is None or self._closed:
            return
        x0, y0 = self._drag_origin
        dx, dy = int(event.x) - x0, int(event.y) - y0
        self._drag_origin = (int(event.x), int(event.y))
        cam = self._renderer.GetActiveCamera()
        cam.Azimuth(-dx * 0.35)
        cam.Elevation(dy * 0.35)
        cam.OrthogonalizeViewUp()
        self._renderer.ResetCameraClippingRange()
        self._render_to_tk(high_quality=False)

    def _on_drag_end(self, _event) -> None:
        self._drag_origin = None
        # Al soltar se reemplaza el cuadro interactivo 1x por uno de mayor
        # calidad. No se recalcula ningún dato científico.
        self._render_to_tk(high_quality=True)

    def _on_mousewheel(self, event) -> None:
        delta = getattr(event, "delta", 0)
        self._zoom(1.10 if delta > 0 else 0.90)

    def _zoom(self, factor: float) -> None:
        if self._closed:
            return
        self._renderer.GetActiveCamera().Dolly(float(factor))
        self._renderer.ResetCameraClippingRange()
        self._render_to_tk(high_quality=True)

    def _on_configure(self, event) -> None:
        if self._closed:
            return
        width = max(self.MIN_WIDTH, int(getattr(event, "width", self.MIN_WIDTH)))
        height = max(self.MIN_HEIGHT, int(getattr(event, "height", self.MIN_HEIGHT)))
        size = (width, height)
        if size == self._last_size:
            return
        self._last_size = size
        if self._resize_after is not None:
            try:
                self._image_label.after_cancel(self._resize_after)
            except tk.TclError:
                pass
        self._resize_after = self._image_label.after(80, self._render_to_tk)

    # ---------- frame VTK -> Tk ------------------------------------
    def _render_to_tk(self, high_quality: bool = True) -> None:
        if self._closed:
            return
        self._resize_after = None
        try:
            width = max(self.MIN_WIDTH, int(self._image_label.winfo_width()))
            height = max(self.MIN_HEIGHT, int(self._image_label.winfo_height()))
        except (tk.TclError, ValueError):
            width, height = self.MIN_WIDTH, self.MIN_HEIGHT
        if self._last_size != (width, height):
            self._last_size = (width, height)

        scale = self.QUALITY_RENDER_SCALE if high_quality else 1.0
        if width > 0 and height > 0:
            max_scale = math.sqrt(self.MAX_RENDER_PIXELS / float(width * height))
            scale = max(1.0, min(scale, max_scale))
        render_width = max(self.MIN_WIDTH, int(round(width * scale)))
        render_height = max(self.MIN_HEIGHT, int(round(height * scale)))

        self._render_window.SetSize(render_width, render_height)
        self._render_window.Render()
        self._image_filter.Modified()
        self._image_filter.Update()
        image = self._image_filter.GetOutput()
        dims = image.GetDimensions()
        scalars = image.GetPointData().GetScalars()
        if scalars is None or dims[0] <= 0 or dims[1] <= 0:
            cls = self._render_window.GetClassName() if self._render_window is not None else "desconocido"
            raise RuntimeError(f"VTK no devolvió una imagen válida ({cls}, {dims[0]}x{dims[1]})")
        array = self._vtk_to_numpy(scalars).reshape(dims[1], dims[0], -1)
        if array.shape[2] >= 4:
            array = array[:, :, :4]
            mode = "RGBA"
        else:
            array = array[:, :, :3]
            mode = "RGB"
        array = np.flipud(array).copy()
        pil = Image.fromarray(array, mode=mode)
        if (render_width, render_height) != (width, height):
            pil = pil.resize((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil, master=self._image_label)
        self._image_label.configure(image=photo)
        self._photo = photo

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._resize_after is not None:
            try:
                self._image_label.after_cancel(self._resize_after)
            except Exception:
                pass
            self._resize_after = None
        if self._initial_render_after is not None:
            try:
                self._image_label.after_cancel(self._initial_render_after)
            except Exception:
                pass
            self._initial_render_after = None
        try:
            self._image_label.configure(image="")
        except Exception:
            pass
        self._photo = None
        try:
            self._render_window.Finalize()
        except Exception:
            pass
        self._image_filter = None
        self._render_window = None
        self._renderer = None
        self._parent = None


def _render_matplotlib_fallback(
    parent: tk.Misc,
    data: Scene3DData,
    vtk_error: Exception | None,
) -> None:
    """Fallback compatible; también queda dentro del mismo frame."""
    top = tk.Frame(parent)
    top.pack(side=tk.TOP, fill=tk.X)
    text = "Motor 3D: Matplotlib (fallback)"
    if vtk_error is None:
        text += " · VTK no está instalado"
    else:
        text += " · VTK no pudo inicializarse"
    if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
        text += f" · ☀ Az {data.solar_azimuth_deg:.0f}° · El {data.solar_altitude_deg:.0f}°"
    tk.Label(top, text=text, anchor="w").pack(side=tk.LEFT, padx=6, pady=3)
    if vtk_error is not None:
        detail = f"{type(vtk_error).__name__}: {vtk_error}"
        diag = tk.Label(
            parent,
            text=f"{vtk_installation_info()} · {detail}",
            anchor="w",
            justify="left",
            fg="#8a2d2d",
            wraplength=1000,
        )
        diag.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 3))

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    X, Y, T = data.X, data.Y, data.temperature
    lo, hi = _finite_range(T)
    levels = np.linspace(lo, hi, 20)
    floor = ax.contourf(
        X,
        Y,
        T,
        levels=levels,
        zdir="z",
        offset=0,
        cmap=CMAP_TEMPERATURA,
        alpha=0.50,
    )
    # Isotermas también en el fallback para mantener la misma lectura visual.
    iso = ax.contour(
        X, Y, T, levels=np.linspace(lo, hi, 6), zdir="z", offset=0.015,
        colors="0.18", linewidths=0.8, alpha=0.80,
    )
    cbar = fig.colorbar(floor, ax=ax, shrink=0.68, aspect=14, pad=0.07)
    cbar.set_label(f"Temperatura ({data.temperature_unit})")

    for tree in data.trees:
        x = float(getattr(tree, "x", 0.0))
        y = float(getattr(tree, "y", 0.0))
        h = max(0.2, float(getattr(tree, "h", 1.0) or 1.0))
        r = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
        ax.plot(
            [x, x],
            [y, y],
            [0, max(0.2, h - r)],
            color="saddlebrown",
            linewidth=2.5,
        )
        ax.scatter(
            [x],
            [y],
            [max(r, h - r * 0.55)],
            s=max(70, r * r * 55),
            color=color_copa(getattr(tree, "especie", "")),
            alpha=0.82,
            depthshade=True,
        )

    for structure in data.structures:
        tipo = str(getattr(structure, "tipo", ""))
        x1, y1 = float(structure.x1), float(structure.y1)
        x2, y2 = float(structure.x2), float(structure.y2)
        h = max(0.0, float(getattr(structure, "altura", 0.0) or 0.0))
        if tipo == "Pared":
            panel = [[(x1, y1, 0), (x2, y2, 0), (x2, y2, h), (x1, y1, h)]]
            ax.add_collection3d(
                Poly3DCollection(
                    panel, facecolor="0.5", alpha=0.72, edgecolor="0.25"
                )
            )
        else:
            z = h if tipo == "Galeria" else 0.04
            rect = [[(x1, y1, z), (x2, y1, z), (x2, y2, z), (x1, y2, z)]]
            color = "saddlebrown" if tipo == "Galeria" else "0.5"
            ax.add_collection3d(
                Poly3DCollection(rect, facecolor=color, alpha=0.55)
            )

    # Marcador solar representativo también en el fallback.
    if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
        xmin, xmax, ymin, ymax, max_height = _scene_extent(data)
        span = max(xmax - xmin, ymax - ymin, 1.0)
        center = ((xmin + xmax) / 2, (ymin + ymax) / 2, max_height * 0.35)
        alt = math.radians(data.solar_altitude_deg)
        azi = math.radians(data.solar_azimuth_deg)
        sx = math.sin(azi) * math.cos(alt)
        sy = math.cos(azi) * math.cos(alt)
        sz = max(0.10, math.sin(alt))
        sun_distance = span * 2.15
        sun_x = center[0] + sx * sun_distance
        sun_y = center[1] + sy * sun_distance
        sun_z = center[2] + sz * sun_distance
        ax.scatter([sun_x], [sun_y], [sun_z], s=220, color="#ffd34d", edgecolors="#d88a00", depthshade=False)
        ax.plot([sun_x, center[0]], [sun_y, center[1]], [sun_z, max(0.05, center[2] * 0.12)], color="#d88a00", alpha=0.45, linewidth=1.4)
        ax.text(sun_x, sun_y, sun_z, f"  ☀", fontsize=10, color="#6b4c00")

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Altura (m)")
    ax.set_title(data.title)
    ax.view_init(elev=38, azim=-58)

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, parent, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    class _FallbackController:
        def close(self_nonlocal) -> None:
            try:
                canvas.get_tk_widget().destroy()
            except Exception:
                pass
            fig.clear()

    setattr(parent, "_sombra_scene3d_controller", _FallbackController())
