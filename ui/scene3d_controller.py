"""Construcción de mallas y actores VTK; interacción en un mixin separado."""
from __future__ import annotations
import math
import sys
import tkinter as tk
from core.scene3d_data import Scene3DData, _optional_float, _finite_range, _scene_extent
import numpy as np
from matplotlib import colormaps
from matplotlib.colors import to_rgb
from core.species import color_copa
from core.crown_shapes import canopy_profile
from plot_style import CMAP_TEMPERATURA
from ui.scene3d_interaction import VTKInteractionMixin

class _VTKOffscreenSceneController(VTKInteractionMixin):
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

    def __init__(self, parent: tk.Misc, data: Scene3DData, temperature_range: tuple[float, float] | None = None):
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
        from vtkmodules.vtkCommonCore import vtkLookupTable, vtkPoints
        from vtkmodules.vtkCommonDataModel import vtkStructuredGrid
        from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkTubeFilter
        from vtkmodules.vtkFiltersSources import vtkConeSource, vtkCubeSource, vtkCylinderSource, vtkLineSource, vtkSphereSource
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
        self._temperature_range = temperature_range
        self._grid = None
        self._ground_mapper = None
        self._lut = None
        self._contours = None
        self._contour_mapper = None
        self._contour_outline_mapper = None
        self._key_light = None
        self._sun_source = None
        self._guide_source = None
        self._shadow_grid = None
        self._shadow_actor = None
        self._shadow_mapper = None
        self._shadow_lut = None
        self._scene_center = None
        self._scene_span = None

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
        self._solar_status_label = tk.Label(
            toolbar,
            text=f"Arrastrar: rotar · Rueda: zoom{solar_summary}",
            anchor="e",
            fg="#555555",
        )
        self._solar_status_label.pack(side=tk.RIGHT, padx=8)

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

        if temperature_range is None:
            lo, hi = _finite_range(T)
        else:
            lo, hi = float(temperature_range[0]), float(temperature_range[1])
            if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
                lo, hi = _finite_range(T)
        self._temperature_range = (lo, hi)
        lut = vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(lo, hi)
        cmap = colormaps.get_cmap(CMAP_TEMPERATURA)
        for idx in range(256):
            r, g, b, a = cmap(idx / 255.0)
            lut.SetTableValue(idx, float(r), float(g), float(b), float(a))
        lut.Build()
        self._grid = grid
        self._lut = lut

        ground_mapper = vtkDataSetMapper()
        ground_mapper.SetInputData(grid)
        ground_mapper.SetScalarRange(lo, hi)
        ground_mapper.SetLookupTable(lut)
        ground_mapper.ScalarVisibilityOn()
        self._ground_mapper = ground_mapper
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
        self._scene_span = span

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
            self._contours = contours
            # Doble trazo: borde oscuro + línea coloreada por temperatura.
            # Así la capa térmica sigue al 50 %, pero cada isoterma conserva
            # saturación completa y se distingue de los objetos físicos.
            contour_outline_mapper = vtkPolyDataMapper()
            contour_outline_mapper.SetInputConnection(contours.GetOutputPort())
            contour_outline_mapper.ScalarVisibilityOff()
            self._contour_outline_mapper = contour_outline_mapper
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
            self._contour_mapper = contour_mapper
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
        sphere_source.SetThetaResolution(32)
        sphere_source.SetPhiResolution(24)
        sphere_mapper = vtkPolyDataMapper()
        sphere_mapper.SetInputConnection(sphere_source.GetOutputPort())

        cone_source = vtkConeSource()
        cone_source.SetRadius(1.0)
        cone_source.SetHeight(2.0)
        cone_source.SetDirection(0.0, 0.0, 1.0)
        cone_source.SetResolution(32)
        cone_mapper = vtkPolyDataMapper()
        cone_mapper.SetInputConnection(cone_source.GetOutputPort())

        pyramid_source = vtkConeSource()
        pyramid_source.SetRadius(1.0)
        pyramid_source.SetHeight(2.0)
        pyramid_source.SetDirection(0.0, 0.0, 1.0)
        pyramid_source.SetResolution(4)
        pyramid_mapper = vtkPolyDataMapper()
        pyramid_mapper.SetInputConnection(pyramid_source.GetOutputPort())

        cyl_source = vtkCylinderSource()
        cyl_source.SetRadius(1.0)
        cyl_source.SetHeight(1.0)
        cyl_source.SetResolution(24)
        cyl_mapper = vtkPolyDataMapper()
        cyl_mapper.SetInputConnection(cyl_source.GetOutputPort())

        def add_canopy_actor(mapper, pos, scale, rgb, opacity, tint=1.0):
            canopy = vtkActor()
            canopy.SetMapper(mapper)
            canopy.SetScale(*scale)
            canopy.SetPosition(*pos)
            canopy.GetProperty().SetColor(
                *tuple(min(1.0, max(0.0, c * tint)) for c in rgb)
            )
            canopy.GetProperty().SetOpacity(opacity)
            canopy.GetProperty().SetInterpolationToPhong()
            canopy.GetProperty().SetAmbient(0.18)
            canopy.GetProperty().SetDiffuse(0.82)
            canopy.GetProperty().SetSpecular(0.10)
            canopy.GetProperty().SetSpecularPower(20)
            renderer.AddActor(canopy)
            return canopy

        # Árboles: la forma de copa es un atributo de representación; el
        # kernel de sombra/radiación no cambia en esta versión.
        for tree in data.trees:
            x = float(getattr(tree, "x", 0.0))
            y = float(getattr(tree, "y", 0.0))
            h = max(0.2, float(getattr(tree, "h", getattr(tree, "altura", 1.0)) or 1.0))
            radius = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
            profile = canopy_profile(getattr(tree, "forma_copa", None), radius, h)
            shape = str(profile["shape"])
            crown_h = float(profile["crown_height"])
            crown_base = float(profile["crown_base"])
            crown_center_z = float(profile["crown_center"])
            trunk_height = float(profile["trunk_height"])
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
            opacity = 0.96 if rho is None else min(0.995, max(0.92, 0.90 + 0.095 * rho))

            if shape == "Cónica":
                add_canopy_actor(
                    cone_mapper, (x, y, crown_center_z),
                    (radius, radius, crown_h / 2.0), canopy_rgb, opacity,
                )
            elif shape == "Piramidal":
                actor = add_canopy_actor(
                    pyramid_mapper, (x, y, crown_center_z),
                    (radius, radius, crown_h / 2.0), canopy_rgb, opacity,
                )
                actor.RotateZ(45.0)
            elif shape == "Columnar":
                add_canopy_actor(
                    sphere_mapper, (x, y, crown_center_z),
                    (radius * 0.56, radius * 0.56, crown_h / 2.0), canopy_rgb, opacity,
                )
            elif shape == "Extendida":
                specs = (
                    (0.00, 0.00, 0.00, 0.78, 0.48, 0.46, 1.00),
                    (-0.34, 0.00, -0.03, 0.55, 0.40, 0.34, 0.96),
                    (0.34, 0.00, -0.02, 0.55, 0.40, 0.34, 1.04),
                )
                for dx, dy, dz, sx, sy, sz, tint in specs:
                    add_canopy_actor(
                        sphere_mapper,
                        (x + radius * dx, y + radius * dy, crown_center_z + crown_h * dz),
                        (radius * sx, radius * sy, crown_h * sz),
                        canopy_rgb, opacity, tint,
                    )
            elif shape == "Irregular":
                specs = (
                    (0.00, 0.00, 0.00, 0.72, 0.68, 0.48, 1.00),
                    (0.34, 0.08, 0.02, 0.53, 0.45, 0.36, 0.92),
                    (-0.30, -0.12, -0.04, 0.56, 0.52, 0.38, 1.05),
                    (0.05, 0.32, -0.08, 0.46, 0.50, 0.32, 0.88),
                )
                for dx, dy, dz, sx, sy, sz, tint in specs:
                    add_canopy_actor(
                        sphere_mapper,
                        (x + radius * dx, y + radius * dy, crown_center_z + crown_h * dz),
                        (radius * sx, radius * sy, crown_h * sz),
                        canopy_rgb, opacity, tint,
                    )
            elif shape == "Llora":
                add_canopy_actor(
                    sphere_mapper, (x, y, h - crown_h * 0.28),
                    (radius * 0.72, radius * 0.70, crown_h * 0.28), canopy_rgb, opacity,
                )
                for idx, ang in enumerate(np.linspace(0.0, 2.0 * math.pi, 6, endpoint=False)):
                    add_canopy_actor(
                        sphere_mapper,
                        (x + radius * 0.50 * math.cos(ang),
                         y + radius * 0.50 * math.sin(ang),
                         crown_base + crown_h * 0.43),
                        (radius * 0.30, radius * 0.30, crown_h * 0.43),
                        canopy_rgb, opacity * 0.96, 0.92 + 0.03 * (idx % 3),
                    )
            else:  # Esférica
                lobe_specs = (
                    (0.00, 0.00, 0.00, 0.78, 0.78, 0.50, 1.00),
                    (0.28, 0.02, -0.04, 0.66, 0.62, 0.36, 0.92),
                    (-0.27, -0.03, -0.03, 0.64, 0.67, 0.37, 1.05),
                    (0.01, 0.28, -0.06, 0.62, 0.65, 0.35, 0.86),
                    (-0.03, -0.27, -0.05, 0.66, 0.61, 0.36, 0.98),
                )
                for dx, dy, dz, sx, sy, sz, tint in lobe_specs:
                    add_canopy_actor(
                        sphere_mapper,
                        (x + radius * dx, y + radius * dy, crown_center_z + crown_h * dz),
                        (radius * sx, radius * sy, crown_h * sz),
                        canopy_rgb, opacity, tint,
                    )

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
        self._scene_center = center
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
        self._key_light = key

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

        # Marcador solar representativo. No participa del encuadre de cámara:
        # SetUseBounds(False) evita que el sol lejano reduzca visualmente la escena.
        if data.solar_altitude_deg is not None and data.solar_azimuth_deg is not None:
            alt = math.radians(data.solar_altitude_deg)
            azi = math.radians(data.solar_azimuth_deg)
            sx = math.sin(azi) * math.cos(alt)
            sy = math.cos(azi) * math.cos(alt)
            sz = max(0.10, math.sin(alt))
            sun_distance = span * 0.45
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
            self._sun_source = sun
            sun_mapper = vtkPolyDataMapper()
            sun_mapper.SetInputConnection(sun.GetOutputPort())
            sun_actor = vtkActor()
            sun_actor.SetMapper(sun_mapper)
            sun_actor.GetProperty().SetColor(1.00, 0.84, 0.22)
            sun_actor.GetProperty().SetAmbient(0.70)
            sun_actor.GetProperty().SetDiffuse(0.30)
            sun_actor.SetUseBounds(False)
            renderer.AddActor(sun_actor)

            guide = vtkLineSource()
            guide.SetPoint1(*sun_pos)
            guide.SetPoint2(center[0], center[1], max(0.05, center[2] * 0.12))
            self._guide_source = guide
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
            guide_actor.GetProperty().SetOpacity(0.48)
            guide_actor.SetUseBounds(False)
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

