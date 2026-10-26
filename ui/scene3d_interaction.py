"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
from ui.scene3d_backend import vtk_installation_info, _render_matplotlib_fallback
import math
import tkinter as tk
from core.scene3d_data import _scene_extent
from typing import Any
import numpy as np
from PIL import Image, ImageTk

class VTKInteractionMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def _ensure_shadow_overlay(self, shadow: np.ndarray) -> None:
        """Crea una única capa de sombra dinámica sobre el plano térmico."""
        from vtkmodules.vtkCommonCore import vtkLookupTable
        from vtkmodules.vtkCommonDataModel import vtkStructuredGrid
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper
        from vtkmodules.util.numpy_support import numpy_to_vtk

        if self._grid is None or self._renderer is None:
            return
        values = np.asarray(shadow, dtype=np.float32)
        if values.shape != self._data.temperature.shape:
            raise ValueError("La matriz de sombra no coincide con la malla térmica 3D")
        shade = np.clip(1.0 - values, 0.0, 1.0).astype(np.float32, copy=False)
        vtk_shadow = numpy_to_vtk(shade.ravel(order="C"), deep=True)
        vtk_shadow.SetName("Sombra")

        if self._shadow_grid is None:
            dims = [0, 0, 0]
            self._grid.GetDimensions(dims)
            shadow_grid = vtkStructuredGrid()
            shadow_grid.SetDimensions(*dims)
            shadow_grid.SetPoints(self._grid.GetPoints())
            shadow_grid.GetPointData().SetScalars(vtk_shadow)

            lut = vtkLookupTable()
            lut.SetNumberOfTableValues(256)
            lut.SetRange(0.0, 1.0)
            for idx in range(256):
                fraction = idx / 255.0
                # Sol prácticamente transparente; sombra cada vez más oscura.
                alpha = 0.58 * (fraction ** 0.85)
                lut.SetTableValue(idx, 0.05, 0.07, 0.09, alpha)
            lut.Build()

            mapper = vtkDataSetMapper()
            mapper.SetInputData(shadow_grid)
            mapper.SetScalarRange(0.0, 1.0)
            mapper.SetLookupTable(lut)
            mapper.ScalarVisibilityOn()
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.SetPosition(0.0, 0.0, max(0.004, float(self._scene_span or 1.0) * 0.00018))
            actor.GetProperty().LightingOff()
            self._renderer.AddActor(actor)
            self._shadow_grid = shadow_grid
            self._shadow_lut = lut
            self._shadow_mapper = mapper
            self._shadow_actor = actor
        else:
            self._shadow_grid.GetPointData().SetScalars(vtk_shadow)
            self._shadow_grid.Modified()

    def update_animation_frame(self, frame: dict[str, Any], *, render: bool = True) -> None:
        """Actualiza un fotograma SIN recrear viewport ni reencuadrar cámara."""
        if self._closed or self._grid is None:
            return
        from vtkmodules.util.numpy_support import numpy_to_vtk

        T = np.asarray(frame.get("T_display"), dtype=np.float32)
        if T.shape != self._data.temperature.shape:
            raise ValueError("El fotograma 3D tiene una resolución distinta a la escena inicial")
        vtk_t = numpy_to_vtk(T.ravel(order="C"), deep=True)
        vtk_t.SetName("Temperatura")
        self._grid.GetPointData().SetScalars(vtk_t)
        self._grid.Modified()
        if self._contours is not None:
            self._contours.Modified()

        shadow = frame.get("shadow")
        if shadow is not None:
            self._ensure_shadow_overlay(np.asarray(shadow, dtype=np.float32))

        alt_deg = float(frame.get("solar_altitude_deg", 0.0))
        azi_deg = float(frame.get("solar_azimuth_deg", 0.0))
        center = self._scene_center
        span = float(self._scene_span or 1.0)
        if center is not None:
            alt = math.radians(alt_deg)
            azi = math.radians(azi_deg)
            sx = math.sin(azi) * math.cos(alt)
            sy = math.cos(azi) * math.cos(alt)
            sz = max(0.10, math.sin(alt))
            if self._key_light is not None:
                distance = span * 4.0
                self._key_light.SetPosition(
                    center[0] + sx * distance,
                    center[1] + sy * distance,
                    center[2] + sz * distance,
                )
                self._key_light.SetFocalPoint(*center)
            sun_distance = span * 0.45
            sun_pos = (
                center[0] + sx * sun_distance,
                center[1] + sy * sun_distance,
                center[2] + sz * sun_distance,
            )
            if self._sun_source is not None:
                self._sun_source.SetCenter(*sun_pos)
                self._sun_source.Modified()
            if self._guide_source is not None:
                self._guide_source.SetPoint1(*sun_pos)
                self._guide_source.SetPoint2(center[0], center[1], max(0.05, center[2] * 0.12))
                self._guide_source.Modified()

        try:
            self._solar_status_label.configure(
                text=f"Arrastrar: rotar · Rueda: zoom · ☀ Az {azi_deg:.0f}° · El {alt_deg:.0f}°"
            )
        except Exception:
            pass
        # CRÍTICO: no ResetCamera() aquí. La cámara permanece idéntica a través
        # de toda la secuencia y solo cambian T, sombra, sol e iluminación.
        if self._renderer is not None:
            self._renderer.ResetCameraClippingRange()
        if render:
            self._render_to_tk(high_quality=False)

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
