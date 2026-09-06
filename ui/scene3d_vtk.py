"""Vista 3D embebida y más realista usando VTK en render off-screen.

La aplicación principal usa Tkinter. Los wheels modernos de VTK no siempre
incluyen ``vtkRenderingTk``; por eso v29 no depende de un widget OpenGL nativo
insertado en Tk. VTK renderiza la escena fuera de pantalla y la imagen se
presenta dentro de un Canvas Tkinter. El usuario puede rotar y hacer zoom y
cada interacción vuelve a renderizar la escena, de modo que sigue siendo una
vista 3D interactiva pero robusta en Windows/Linux.

La vista es una REPRESENTACIÓN visual de los mismos resultados físicos 2D:
no altera T, sombras ni balances.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image, ImageTk

from core.species import color_copa
from core.materials import get_surface_material
from plot_style import CMAP_TEMPERATURA
from matplotlib import colormaps

_TEMP_CMAP = colormaps.get_cmap(CMAP_TEMPERATURA)

try:  # dependencia grande: se informa de forma clara si falta
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    VTK_AVAILABLE = True
    VTK_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - depende del entorno
    vtk = None
    vtk_to_numpy = None
    VTK_AVAILABLE = False
    VTK_IMPORT_ERROR = exc


def _hex_to_rgb01(value: str, fallback=(0.18, 0.48, 0.20)):
    text = str(value or "").strip()
    named = {
        "forestgreen": "#228B22",
        "darkgreen": "#006400",
        "green": "#008000",
        "saddlebrown": "#8B4513",
        "gray": "#808080",
        "grey": "#808080",
        "black": "#000000",
        "white": "#FFFFFF",
    }
    text = named.get(text.lower(), text)
    if text.startswith("#") and len(text) == 7:
        try:
            return tuple(int(text[i:i+2], 16) / 255.0 for i in (1, 3, 5))
        except ValueError:
            pass
    return fallback


def _material_visual(material_name: str | None):
    """Deriva un aspecto visual coherente de propiedades ópticas del material."""
    mat = get_surface_material(material_name)
    name = (material_name or "").lower()
    if any(k in name for k in ("madera", "clt")):
        color = (0.45, 0.24, 0.10)
    elif any(k in name for k in ("alumin", "acero", "hierro", "zinc")):
        color = (0.52, 0.56, 0.60)
    elif any(k in name for k in ("ladrillo", "terracota", "corten")):
        color = (0.55, 0.24, 0.13)
    elif any(k in name for k in ("vidrio", "policarbonato", "etfe", "transl")):
        color = (0.65, 0.82, 0.88)
    elif any(k in name for k in ("hormig", "cement")):
        color = (0.55, 0.55, 0.52)
    else:
        color = (0.46, 0.47, 0.44)
    metallic = 0.85 if any(k in name for k in ("alumin", "acero", "hierro", "zinc")) else 0.0
    roughness = min(0.95, max(0.18, 0.25 + 0.75 * mat.solar_absorptance))
    opacity = min(1.0, max(0.18, 1.0 - 0.65 * mat.solar_transmittance))
    return color, metallic, roughness, opacity


def _set_pbr(prop, color, *, metallic=0.0, roughness=0.65, opacity=1.0):
    """Material visual robusto para render off-screen.

    En una ventana OpenGL nativa VTK-PBR funciona muy bien, pero algunos
    drivers off-screen lo muestran excesivamente oscuro. Para que la vista
    embebida sea consistente en Windows/Linux usamos Phong con parámetros
    derivados de metalicidad/rugosidad. El aspecto sigue siendo muy superior
    al mplot3d anterior y no depende de un mapa de entorno HDR.
    """
    prop.SetColor(*color)
    prop.SetOpacity(float(opacity))
    if hasattr(prop, "SetInterpolationToPhong"):
        prop.SetInterpolationToPhong()
    prop.SetAmbient(0.22)
    prop.SetDiffuse(0.72)
    prop.SetSpecular(0.52 if metallic > 0.5 else 0.18)
    prop.SetSpecularPower(max(8.0, 70.0 * (1.0 - float(roughness))))


def _actor_from_source(source):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    return actor


class VTKSceneView:
    """Motor VTK interactivo mostrado como imagen dentro de un Canvas Tk."""

    def __init__(self, parent: tk.Misc, palette: dict | None = None):
        if not VTK_AVAILABLE:
            raise RuntimeError(
                "VTK no está disponible. Instale las dependencias con "
                "'pip install -r requirements.txt'."
            ) from VTK_IMPORT_ERROR
        self.parent = parent
        self.palette = palette or {}
        self._closed = False
        self._photo = None
        self._canvas_image_id = None
        self._drag_origin = None
        self._resize_after_id = None
        self._scene_ready = False

        toolbar = tk.Frame(parent, bg=self.palette.get("panel", "white"))
        toolbar.pack(side=tk.TOP, fill=tk.X)
        self.status = tk.Label(
            toolbar,
            text="3D VTK · arrastre para rotar · rueda para zoom",
            anchor="w",
            bg=self.palette.get("panel", "white"),
            fg=self.palette.get("text", "#333333"),
            font=("Arial", 8),
        )
        self.status.pack(side=tk.LEFT, padx=8, pady=3, fill=tk.X, expand=True)
        ttk.Button(toolbar, text="Superior", command=self.top_camera).pack(side=tk.RIGHT, padx=(2, 4), pady=2)
        ttk.Button(toolbar, text="Isométrica", command=self.reset_camera).pack(side=tk.RIGHT, padx=2, pady=2)

        self.canvas = tk.Canvas(
            parent,
            bg="#dbe8f2",
            highlightthickness=0,
            bd=0,
            cursor="fleur",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<MouseWheel>", self._wheel)       # Windows/macOS
        self.canvas.bind("<Button-4>", lambda _e: self._zoom(1.12))  # Linux
        self.canvas.bind("<Button-5>", lambda _e: self._zoom(0.89))
        self.canvas.bind("<Configure>", self._on_resize)

        self.render_window = vtk.vtkRenderWindow()
        self.render_window.SetOffScreenRendering(1)
        self.render_window.SetMultiSamples(8)
        self.renderer = vtk.vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        self.renderer.SetGradientBackground(True)
        self.renderer.SetBackground(0.96, 0.98, 1.0)
        self.renderer.SetBackground2(0.67, 0.80, 0.92)
        # FXAA de VTK produce un framebuffer negro con algunos backends
        # off-screen (incluidos ciertos wheels Linux). El antialiasing se
        # mantiene mediante multisampling, que sí es estable en este modo.

        self.parent.bind("<Destroy>", self._on_destroy, add="+")

    # ----------------------------- interacción -----------------------------
    def _start_drag(self, event):
        self._drag_origin = (event.x, event.y)

    def _drag(self, event):
        if not self._scene_ready or self._drag_origin is None:
            return
        ox, oy = self._drag_origin
        dx, dy = event.x - ox, event.y - oy
        self._drag_origin = (event.x, event.y)
        cam = self.renderer.GetActiveCamera()
        cam.Azimuth(-dx * 0.42)
        cam.Elevation(dy * 0.34)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self._render_to_canvas()

    def _wheel(self, event):
        self._zoom(1.10 if event.delta > 0 else 0.91)
        return "break"

    def _zoom(self, factor):
        if not self._scene_ready:
            return
        cam = self.renderer.GetActiveCamera()
        cam.Dolly(float(factor))
        self.renderer.ResetCameraClippingRange()
        self._render_to_canvas()

    def _on_resize(self, _event=None):
        if not self._scene_ready:
            return
        if self._resize_after_id is not None:
            try:
                self.parent.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.parent.after(100, self._render_to_canvas)

    def _on_destroy(self, event):
        if event.widget is self.parent:
            self.close()

    # ------------------------------- escena --------------------------------
    def _temperature_grid(self, X, Y, T_display):
        rows, cols = T_display.shape
        # La GPU no necesita la resolución científica completa para mostrarla.
        # Se reduce SOLO la malla visual; el cálculo 2D permanece intacto.
        step = max(1, int(math.ceil(max(rows, cols) / 240)))
        Xr = np.asarray(X)[::step, ::step]
        Yr = np.asarray(Y)[::step, ::step]
        Tr = np.asarray(T_display, dtype=float)[::step, ::step]
        nr, nc = Tr.shape

        grid = vtk.vtkStructuredGrid()
        grid.SetDimensions(nc, nr, 1)
        points = vtk.vtkPoints()
        points.SetNumberOfPoints(nr * nc)

        valid = Tr[np.isfinite(Tr)]
        tmin = float(valid.min()) if valid.size else 0.0
        tmax = float(valid.max()) if valid.size else 1.0
        span = max(tmax - tmin, 1e-9)

        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("TemperaturaRGB")
        colors.SetNumberOfComponents(3)
        colors.SetNumberOfTuples(nr * nc)

        idx = 0
        for i in range(nr):
            for j in range(nc):
                points.SetPoint(idx, float(Xr[i, j]), float(Yr[i, j]), 0.0)
                val = float(Tr[i, j]) if np.isfinite(Tr[i, j]) else tmin
                rgba = _TEMP_CMAP(min(1.0, max(0.0, (val - tmin) / span)))
                colors.SetTuple3(idx, int(255 * rgba[0]), int(255 * rgba[1]), int(255 * rgba[2]))
                idx += 1

        grid.SetPoints(points)
        grid.GetPointData().SetScalars(colors)
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(grid)
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        _set_pbr(actor.GetProperty(), (1, 1, 1), roughness=0.90)
        return actor, tmin, tmax

    def _add_base(self, xmin, xmax, ymin, ymax):
        plane = vtk.vtkCubeSource()
        plane.SetXLength(max(xmax - xmin, 1.0) + 2.0)
        plane.SetYLength(max(ymax - ymin, 1.0) + 2.0)
        plane.SetZLength(0.18)
        plane.SetCenter((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, -0.11)
        actor = _actor_from_source(plane)
        _set_pbr(actor.GetProperty(), (0.42, 0.38, 0.31), roughness=0.95)
        self.renderer.AddActor(actor)

    def _add_tree(self, tree):
        x = float(getattr(tree, "x", 0.0))
        y = float(getattr(tree, "y", 0.0))
        h = max(0.5, float(getattr(tree, "h", getattr(tree, "altura", 3.0))))
        crown_r = max(0.35, float(getattr(tree, "radio_copa", 1.5)))
        crown_zr = min(crown_r * 0.85, h * 0.34)
        crown_center_z = max(crown_zr + 0.5, h - crown_zr)
        trunk_h = max(0.45, crown_center_z - crown_zr * 0.55)
        trunk_r = max(0.08, min(0.32, crown_r * 0.11))

        trunk = vtk.vtkCylinderSource()
        trunk.SetRadius(trunk_r)
        trunk.SetHeight(trunk_h)
        trunk.SetResolution(20)
        trunk_actor = _actor_from_source(trunk)
        trunk_actor.RotateX(90)
        trunk_actor.SetPosition(x, y, trunk_h / 2.0)
        _set_pbr(trunk_actor.GetProperty(), (0.30, 0.16, 0.07), roughness=0.88)
        self.renderer.AddActor(trunk_actor)

        base_color = _hex_to_rgb01(color_copa(getattr(tree, "especie", "")))
        # Copa compuesta para evitar el aspecto de una esfera única.
        lobes = [
            (0.00, 0.00, 0.10, 1.00),
            (-0.35, 0.12, -0.05, 0.72),
            (0.32, 0.18, 0.00, 0.68),
            (0.05, -0.34, -0.06, 0.70),
            (0.02, 0.05, 0.52, 0.62),
        ]
        for dx, dy, dz, scale in lobes:
            sphere = vtk.vtkSphereSource()
            sphere.SetRadius(1.0)
            sphere.SetThetaResolution(26)
            sphere.SetPhiResolution(20)
            actor = _actor_from_source(sphere)
            actor.SetScale(crown_r * scale, crown_r * 0.92 * scale, crown_zr * scale)
            actor.SetPosition(
                x + dx * crown_r,
                y + dy * crown_r,
                crown_center_z + dz * crown_zr,
            )
            shade = 0.90 + 0.08 * (dx + dy)
            color = tuple(min(1.0, max(0.0, c * shade)) for c in base_color)
            _set_pbr(actor.GetProperty(), color, roughness=0.88)
            self.renderer.AddActor(actor)

    def _add_box_actor(self, center, lengths, color, *, angle_deg=0.0, metallic=0.0, roughness=0.7, opacity=1.0):
        cube = vtk.vtkCubeSource()
        cube.SetXLength(max(0.02, lengths[0]))
        cube.SetYLength(max(0.02, lengths[1]))
        cube.SetZLength(max(0.02, lengths[2]))
        actor = _actor_from_source(cube)
        actor.SetPosition(*center)
        if angle_deg:
            actor.RotateZ(angle_deg)
        _set_pbr(actor.GetProperty(), color, metallic=metallic, roughness=roughness, opacity=opacity)
        self.renderer.AddActor(actor)
        return actor

    def _add_structure(self, structure):
        tipo = str(getattr(structure, "tipo", ""))
        x1, y1 = float(structure.x1), float(structure.y1)
        x2, y2 = float(structure.x2), float(structure.y2)
        h = max(0.05, float(getattr(structure, "altura", 0.0)))
        mat_name = getattr(structure, "material", None)
        color, metallic, roughness, mat_opacity = _material_visual(mat_name)
        explicit_opacity = min(1.0, max(0.05, float(getattr(structure, "opacidad", 1.0))))
        opacity = min(mat_opacity, max(0.20, explicit_opacity))

        if tipo == "Pared":
            dx, dy = x2 - x1, y2 - y1
            length = max(math.hypot(dx, dy), 0.1)
            angle = math.degrees(math.atan2(dy, dx))
            self._add_box_actor(
                ((x1+x2)/2, (y1+y2)/2, h/2),
                (length, 0.16, h), color,
                angle_deg=angle, metallic=metallic, roughness=roughness, opacity=opacity,
            )
            return

        xmin, xmax = sorted((x1, x2))
        ymin, ymax = sorted((y1, y2))
        width, depth = max(xmax-xmin, 0.2), max(ymax-ymin, 0.2)
        cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
        if tipo == "Galeria":
            roof_z = max(h, 0.35)
            self._add_box_actor(
                (cx, cy, roof_z), (width, depth, 0.12), color,
                metallic=metallic, roughness=roughness, opacity=opacity,
            )
            post_color = tuple(max(0.05, c * 0.72) for c in color)
            for px, py in ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax)):
                self._add_box_actor(
                    (px, py, roof_z/2), (0.10, 0.10, roof_z), post_color,
                    metallic=metallic, roughness=roughness, opacity=min(1.0, opacity+0.15),
                )
        else:  # Sendero u otra superficie horizontal
            self._add_box_actor(
                (cx, cy, 0.04), (width, depth, 0.08), color,
                metallic=metallic, roughness=max(0.75, roughness), opacity=0.92,
            )

    def _add_lights(self, bounds):
        self.renderer.RemoveAllLights()
        xmin, xmax, ymin, ymax = bounds
        span = max(xmax-xmin, ymax-ymin, 10.0)
        cx, cy = (xmin+xmax)/2, (ymin+ymax)/2

        key = vtk.vtkLight()
        key.SetLightTypeToSceneLight()
        key.SetPositional(False)
        key.SetPosition(cx - span, cy - span * 0.45, span * 1.8)
        key.SetFocalPoint(cx, cy, 0.0)
        key.SetColor(1.0, 0.93, 0.82)
        key.SetIntensity(1.05)
        self.renderer.AddLight(key)

        fill = vtk.vtkLight()
        fill.SetLightTypeToSceneLight()
        fill.SetPositional(False)
        fill.SetPosition(cx + span, cy + span, span * 0.8)
        fill.SetFocalPoint(cx, cy, 0.0)
        fill.SetColor(0.72, 0.82, 1.0)
        fill.SetIntensity(0.38)
        self.renderer.AddLight(fill)

        head = vtk.vtkLight()
        head.SetLightTypeToHeadlight()
        head.SetIntensity(0.42)
        head.SetColor(1.0, 1.0, 1.0)
        self.renderer.AddLight(head)

        self.renderer.SetAmbient(0.18, 0.18, 0.18)

    def _add_scalar_bar(self, tmin, tmax, unit):
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(tmin, tmax)
        lut.Build()
        for i in range(256):
            rgba = _TEMP_CMAP(i / 255.0)
            lut.SetTableValue(i, rgba[0], rgba[1], rgba[2], 1.0)
        scalar_bar = vtk.vtkScalarBarActor()
        scalar_bar.SetLookupTable(lut)
        scalar_bar.SetTitle(f"Temperatura ({unit})")
        scalar_bar.SetNumberOfLabels(5)
        scalar_bar.SetPosition(0.82, 0.12)
        scalar_bar.SetWidth(0.12)
        scalar_bar.SetHeight(0.72)
        self.renderer.AddActor2D(scalar_bar)

    def render(self, vars_dict: dict, app=None, title: str = "Vista 3D"):
        X = vars_dict.get("X")
        Y = vars_dict.get("Y")
        T = vars_dict.get("T")
        if X is None or Y is None or T is None:
            raise ValueError("Primero genere el gráfico 2D para disponer del campo térmico.")

        X = np.asarray(X)
        Y = np.asarray(Y)
        T = np.asarray(T)
        T_display = app.convert_temperature_for_display(T) if app is not None else T
        unit = app.get_temperature_unit_symbol() if app is not None else "K"

        self.renderer.RemoveAllViewProps()
        actor_ground, tmin, tmax = self._temperature_grid(X, Y, T_display)
        xmin, xmax = float(np.nanmin(X)), float(np.nanmax(X))
        ymin, ymax = float(np.nanmin(Y)), float(np.nanmax(Y))
        self._add_base(xmin, xmax, ymin, ymax)
        self.renderer.AddActor(actor_ground)

        for tree in vars_dict.get("arboles", []):
            self._add_tree(tree)
        for structure in vars_dict.get("estructuras", []):
            self._add_structure(structure)

        self._add_lights((xmin, xmax, ymin, ymax))
        self._add_scalar_bar(tmin, tmax, unit)

        title_actor = vtk.vtkTextActor()
        title_actor.SetInput(title)
        title_actor.GetTextProperty().SetFontSize(18)
        title_actor.GetTextProperty().SetColor(0.10, 0.12, 0.15)
        title_actor.SetPosition(12, 12)
        self.renderer.AddActor2D(title_actor)

        self._scene_ready = True
        self.reset_camera(render=False)
        self.status.config(
            text=f"3D VTK · {len(vars_dict.get('arboles', []))} árbol(es) · "
                 f"{len(vars_dict.get('estructuras', []))} estructura(s) · "
                 "arrastre para rotar · rueda para zoom"
        )
        self.parent.update_idletasks()
        self._render_to_canvas()

    # ------------------------------- cámara --------------------------------
    def reset_camera(self, render=True):
        if not self._scene_ready:
            return
        self.renderer.ResetCamera()
        cam = self.renderer.GetActiveCamera()
        cam.ParallelProjectionOff()
        cam.Azimuth(-35)
        cam.Elevation(34)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        if render:
            self._render_to_canvas()

    def top_camera(self):
        if not self._scene_ready:
            return
        self.renderer.ResetCamera()
        cam = self.renderer.GetActiveCamera()
        fp = cam.GetFocalPoint()
        dist = max(cam.GetDistance(), 1.0)
        cam.SetPosition(fp[0], fp[1], fp[2] + dist)
        cam.SetViewUp(0, 1, 0)
        cam.ParallelProjectionOn()
        self.renderer.ResetCameraClippingRange()
        self._render_to_canvas()

    # ------------------------------ raster VTK ------------------------------
    def _render_to_canvas(self):
        if self._closed or not self._scene_ready:
            return
        self._resize_after_id = None
        try:
            width = max(320, int(self.canvas.winfo_width()))
            height = max(240, int(self.canvas.winfo_height()))
        except (tk.TclError, ValueError):
            return
        # limitar render gigante en monitores HiDPI; Tk escala el resultado
        scale = min(1.0, 1400 / width, 900 / height)
        rw, rh = max(320, int(width*scale)), max(240, int(height*scale))
        self.render_window.SetSize(rw, rh)
        self.render_window.Render()

        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(self.render_window)
        capture.SetInputBufferTypeToRGB()
        capture.ReadFrontBufferOff()
        capture.Update()
        image_data = capture.GetOutput()
        dims = image_data.GetDimensions()
        arr = vtk_to_numpy(image_data.GetPointData().GetScalars())
        if arr.size == 0 or dims[0] <= 0 or dims[1] <= 0:
            return
        arr = arr.reshape(dims[1], dims[0], -1)
        arr = np.flipud(arr).astype(np.uint8, copy=False)
        pil = Image.fromarray(arr[:, :, :3], mode="RGB")
        if pil.size != (width, height):
            pil = pil.resize((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(pil)
        if self._canvas_image_id is None:
            self._canvas_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.canvas.itemconfigure(self._canvas_image_id, image=self._photo)
        self.canvas.coords(self._canvas_image_id, 0, 0)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._resize_after_id is not None:
            try:
                self.parent.after_cancel(self._resize_after_id)
            except Exception:
                pass
            self._resize_after_id = None
        try:
            self.render_window.Finalize()
        except Exception:
            pass
        self._photo = None
