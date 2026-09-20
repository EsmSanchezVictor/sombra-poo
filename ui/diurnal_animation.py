"""Reproductor 2D de secuencias diurnas de Proyecto Sombra.

La simulación se calcula previamente con los kernels existentes. Este módulo
solamente reproduce fotogramas ya calculados; no ejecuta física durante el play.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Sequence

import numpy as np
from matplotlib.figure import Figure
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import colormaps
from matplotlib.patches import Rectangle

from core.species import color_copa
from core.crown_shapes import canopy_profile
from ui.canopy_rendering import draw_canopy_2d, draw_canopy_3d_mpl

from plot_style import CMAP_TEMPERATURA
from ui.solar_indicator import add_solar_indicator_2d
from ui.scene3d import (
    Scene3DData, _VTKOffscreenSceneController, vtk_backend_available,
)


class DiurnalAnimationPlayer:
    def __init__(self, parent: tk.Misc, frames: Sequence[dict[str, Any]], app: Any, *, title: str):
        self.parent = parent
        self.frames = list(frames)
        self.app = app
        self.title = title
        self.index = 0
        self.playing = False
        self._after_id = None
        self.speed_ms = tk.IntVar(value=500)
        self.slider_var = tk.IntVar(value=0)

        for widget in list(parent.winfo_children()):
            try:
                widget.destroy()
            except tk.TclError:
                pass

        top = tk.Frame(parent, bd=0)
        top.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(3, 1))
        tk.Button(top, text="◀", width=3, command=self.previous).pack(side=tk.LEFT, padx=2)
        self.play_button = tk.Button(top, text="▶ Reproducir", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="▶|", width=3, command=self.next).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="⟲ Inicio", command=self.first).pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(top, text="Velocidad:").pack(side=tk.LEFT, padx=(12, 3))
        ttk.Combobox(
            top, textvariable=self.speed_ms,
            values=(1000, 750, 500, 300, 150), state="readonly", width=6,
        ).pack(side=tk.LEFT)
        tk.Label(top, text="ms/cuadro").pack(side=tk.LEFT, padx=(3, 8))
        self.status = tk.Label(top, text="", anchor="e")
        self.status.pack(side=tk.RIGHT, padx=6)

        # Ejes y colorbars con geometría FIJA. En v35.1 se creaba y eliminaba
        # una colorbar en cada fotograma; Matplotlib reajustaba los ejes una y
        # otra vez y ambos paneles se iban achicando progresivamente.
        self.figure = Figure(figsize=(9.5, 5.8))
        grid = self.figure.add_gridspec(
            2, 2, height_ratios=(22, 1.25), hspace=0.28, wspace=0.20,
            left=0.07, right=0.98, bottom=0.09, top=0.88,
        )
        self.ax_shadow = self.figure.add_subplot(grid[0, 0])
        self.ax_temp = self.figure.add_subplot(grid[0, 1])
        self._shadow_cax = self.figure.add_subplot(grid[1, 0])
        self._temp_cax = self.figure.add_subplot(grid[1, 1])
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        bottom = tk.Frame(parent, bd=0)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(1, 4))
        self.slider = tk.Scale(
            bottom, from_=0, to=max(0, len(self.frames) - 1),
            variable=self.slider_var, orient=tk.HORIZONTAL,
            showvalue=False, resolution=1, command=self._slider_changed,
        )
        self.slider.pack(fill=tk.X, expand=True)

        all_temp = []
        for frame in self.frames:
            arr = np.asarray(frame["T_display"], dtype=float)
            finite = arr[np.isfinite(arr)]
            if finite.size:
                all_temp.append((float(np.min(finite)), float(np.max(finite))))
        if all_temp:
            self.temp_min = min(v[0] for v in all_temp)
            self.temp_max = max(v[1] for v in all_temp)
        else:
            self.temp_min, self.temp_max = 0.0, 1.0
        if abs(self.temp_max - self.temp_min) < 1e-9:
            self.temp_min -= 0.5
            self.temp_max += 0.5

        self._shadow_mappable = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="Greys")
        self._shadow_mappable.set_array([])
        self._shadow_colorbar = self.figure.colorbar(
            self._shadow_mappable, cax=self._shadow_cax, orientation="horizontal"
        )
        self._shadow_colorbar.set_label("Fracción de sombra efectiva")
        self._temp_mappable = ScalarMappable(
            norm=Normalize(self.temp_min, self.temp_max), cmap=CMAP_TEMPERATURA
        )
        self._temp_mappable.set_array([])
        self._temp_colorbar = self.figure.colorbar(
            self._temp_mappable, cax=self._temp_cax, orientation="horizontal"
        )
        unit0 = self.frames[0].get("temp_unit", "°C") if self.frames else "°C"
        self._temp_colorbar.set_label(f"Temperatura ({unit0})")
        self.render_frame(0)
        setattr(parent, "_sombra_diurnal_player", self)

    def close(self) -> None:
        self.pause()
        try:
            self.figure.clear()
        except Exception:
            pass

    def _draw_objects(self, ax, frame: dict[str, Any]) -> None:
        for idx, tree in enumerate(frame.get("trees", ())):
            draw_canopy_2d(
                ax, tree, facecolor=color_copa(getattr(tree, "especie", "")),
                edgecolor="darkgreen", alpha=0.72, zorder=6,
                label="Árboles" if idx == 0 else None,
            )
        for structure in frame.get("structures", ()):
            tipo = str(getattr(structure, "tipo", ""))
            x1, y1 = float(structure.x1), float(structure.y1)
            x2, y2 = float(structure.x2), float(structure.y2)
            if tipo == "Pared":
                ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.7, zorder=7)
            else:
                face = "saddlebrown" if tipo == "Galeria" else "gray"
                ax.add_patch(Rectangle(
                    (min(x1, x2), min(y1, y2)), abs(x2 - x1), abs(y2 - y1),
                    facecolor=face, edgecolor="0.2", linewidth=0.7,
                    alpha=0.38 if tipo == "Galeria" else 0.28, zorder=5,
                ))

    def render_frame(self, index: int) -> None:
        if not self.frames:
            return
        self.index = max(0, min(int(index), len(self.frames) - 1))
        frame = self.frames[self.index]
        self.slider_var.set(self.index)
        self.ax_shadow.clear()
        self.ax_temp.clear()

        X = np.asarray(frame["X"])
        Y = np.asarray(frame["Y"])
        tau = np.clip(np.asarray(frame["shadow"], dtype=float), 0.0, 1.0)
        shade = 1.0 - tau
        T = np.asarray(frame["T_display"], dtype=float)

        shadow_plot = self.ax_shadow.contourf(
            X, Y, shade, levels=np.linspace(0.0, 1.0, 11), cmap="Greys", vmin=0.0, vmax=1.0,
        )
        temp_levels = np.linspace(self.temp_min, self.temp_max, 21)
        temp_plot = self.ax_temp.contourf(
            X, Y, T, levels=temp_levels, cmap=CMAP_TEMPERATURA,
            vmin=self.temp_min, vmax=self.temp_max,
        )
        self.ax_temp.contour(X, Y, T, levels=temp_levels[::2], colors="0.25", linewidths=0.35, alpha=0.5)

        for ax in (self.ax_shadow, self.ax_temp):
            self._draw_objects(ax, frame)
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlabel("X (m)")
            ax.set_ylabel("Y (m)")
            ax.grid(False)

        self.ax_shadow.set_title("Sombra efectiva\n0 = sol · 1 = máxima atenuación", fontsize=9)
        unit = frame.get("temp_unit", "°C")
        self.ax_temp.set_title(f"Temperatura superficial ({unit})", fontsize=9)
        add_solar_indicator_2d(
            self.ax_temp, frame.get("solar_azimuth_deg"), frame.get("solar_altitude_deg"), corner="upper-right"
        )

        hour = float(frame.get("hour", 0.0))
        hh = int(hour) % 24
        mm = int(round((hour - int(hour)) * 60)) % 60
        alt = frame.get("solar_altitude_deg")
        azi = frame.get("solar_azimuth_deg")
        mean_t = float(np.nanmean(T)) if np.isfinite(T).any() else float("nan")
        mean_shade = float(np.nanmean(shade)) * 100.0 if np.isfinite(shade).any() else float("nan")
        self.figure.suptitle(
            f"{self.title} · {hh:02d}:{mm:02d} · Sol: Az {azi:.0f}° / El {alt:.0f}° · "
            f"T media {mean_t:.1f} {unit} · sombra {mean_shade:.0f}%",
            fontsize=10,
        )
        self.status.configure(text=f"{self.index + 1}/{len(self.frames)} · {hh:02d}:{mm:02d}")
        self.canvas.draw_idle()

    def _slider_changed(self, value: str) -> None:
        try:
            idx = int(float(value))
        except (TypeError, ValueError):
            return
        if idx != self.index:
            self.pause()
            self.render_frame(idx)

    def first(self) -> None:
        self.pause()
        self.render_frame(0)

    def previous(self) -> None:
        self.pause()
        self.render_frame((self.index - 1) % len(self.frames))

    def next(self) -> None:
        self.pause()
        self.render_frame((self.index + 1) % len(self.frames))

    def toggle_play(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if not self.frames or self.playing:
            return
        self.playing = True
        self.play_button.configure(text="⏸ Pausar")
        self._schedule_next()

    def pause(self) -> None:
        self.playing = False
        self.play_button.configure(text="▶ Reproducir")
        if self._after_id is not None:
            try:
                self.parent.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _schedule_next(self) -> None:
        if not self.playing:
            return
        delay = max(60, int(self.speed_ms.get()))
        self._after_id = self.parent.after(delay, self._tick)

    def _tick(self) -> None:
        self._after_id = None
        if not self.playing:
            return
        next_index = self.index + 1
        if next_index >= len(self.frames):
            next_index = 0
        self.render_frame(next_index)
        self._schedule_next()


class Diurnal3DAnimationPlayer:
    """Reproductor 3D real de una secuencia diurna ya calculada.

    Mantiene UN único viewport. Los fotogramas actualizan los scalars de VTK,
    la máscara de sombra y la posición solar sin recrear widgets ni reencuadrar
    la cámara. Así se evita el efecto de imágenes duplicadas/encogimiento.
    """

    def __init__(self, parent: tk.Misc, frames: Sequence[dict[str, Any]], app: Any, *, title: str):
        self.parent = parent
        self.frames = list(frames)
        self.app = app
        self.title = title
        self.index = 0
        self.playing = False
        self._after_id = None
        self.speed_ms = tk.IntVar(value=500)
        self.slider_var = tk.IntVar(value=0)
        self.controller = None
        self._fallback_fig = None
        self._fallback_canvas = None
        self._fallback_ax = None

        old = getattr(parent, "_sombra_scene3d_controller", None)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        old_player = getattr(parent, "_sombra_diurnal_3d_player", None)
        if old_player is not None and old_player is not self:
            try:
                old_player.close()
            except Exception:
                pass
        for widget in list(parent.winfo_children()):
            try:
                widget.destroy()
            except tk.TclError:
                pass

        top = tk.Frame(parent, bd=0)
        top.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(3, 1))
        tk.Button(top, text="◀", width=3, command=self.previous).pack(side=tk.LEFT, padx=2)
        self.play_button = tk.Button(top, text="▶ Reproducir", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="▶|", width=3, command=self.next).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="⟲ Inicio", command=self.first).pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(top, text="Velocidad:").pack(side=tk.LEFT, padx=(12, 3))
        ttk.Combobox(
            top, textvariable=self.speed_ms,
            values=(1000, 750, 500, 300, 150), state="readonly", width=6,
        ).pack(side=tk.LEFT)
        tk.Label(top, text="ms/cuadro").pack(side=tk.LEFT, padx=(3, 8))
        self.status = tk.Label(top, text="", anchor="e")
        self.status.pack(side=tk.RIGHT, padx=6)

        self.scene_host = tk.Frame(parent, bd=0, highlightthickness=0)
        self.scene_host.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        bottom = tk.Frame(parent, bd=0)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(1, 4))
        self.slider = tk.Scale(
            bottom, from_=0, to=max(0, len(self.frames) - 1),
            variable=self.slider_var, orient=tk.HORIZONTAL,
            showvalue=False, resolution=1, command=self._slider_changed,
        )
        self.slider.pack(fill=tk.X, expand=True)

        ranges = []
        for frame in self.frames:
            arr = np.asarray(frame.get("T_display"), dtype=float)
            finite = arr[np.isfinite(arr)]
            if finite.size:
                ranges.append((float(np.min(finite)), float(np.max(finite))))
        if ranges:
            self.temp_range = (min(v[0] for v in ranges), max(v[1] for v in ranges))
        else:
            self.temp_range = (0.0, 1.0)
        if abs(self.temp_range[1] - self.temp_range[0]) < 1e-9:
            self.temp_range = (self.temp_range[0] - 0.5, self.temp_range[1] + 0.5)

        if self.frames and vtk_backend_available():
            first = self.frames[0]
            data = self._scene_data(first)
            try:
                self.controller = _VTKOffscreenSceneController(
                    self.scene_host, data, temperature_range=self.temp_range
                )
                setattr(self.scene_host, "_sombra_scene3d_controller", self.controller)
                # Añade máscara de sombra antes del primer frame sin mover cámara.
                self.controller.update_animation_frame(first, render=False)
            except Exception:
                self.controller = None
                self._build_fallback()
        else:
            self._build_fallback()

        self.render_frame(0)
        setattr(parent, "_sombra_diurnal_3d_player", self)

    def _scene_data(self, frame: dict[str, Any]) -> Scene3DData:
        return Scene3DData(
            X=np.asarray(frame["X"], dtype=np.float32),
            Y=np.asarray(frame["Y"], dtype=np.float32),
            temperature=np.asarray(frame["T_display"], dtype=np.float32),
            trees=tuple(frame.get("trees", ()) or ()),
            structures=tuple(frame.get("structures", ()) or ()),
            temperature_unit=str(frame.get("temp_unit", "°C")),
            title=self.title,
            solar_altitude_deg=float(frame.get("solar_altitude_deg", 0.0)),
            solar_azimuth_deg=float(frame.get("solar_azimuth_deg", 0.0)),
        )

    def _build_fallback(self) -> None:
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize

        for widget in list(self.scene_host.winfo_children()):
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._fallback_fig = Figure(figsize=(8, 6))
        self._fallback_ax = self._fallback_fig.add_subplot(111, projection="3d")
        self._fallback_canvas = FigureCanvasTkAgg(self._fallback_fig, master=self.scene_host)
        self._fallback_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        mappable = ScalarMappable(norm=Normalize(*self.temp_range), cmap=CMAP_TEMPERATURA)
        mappable.set_array([])
        self._fallback_fig.colorbar(mappable, ax=self._fallback_ax, shrink=0.70, pad=0.08, label="Temperatura")

    def _render_fallback(self, frame: dict[str, Any]) -> None:
        from matplotlib import colormaps as _cms
        from matplotlib.colors import Normalize
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        ax = self._fallback_ax
        if ax is None:
            return
        # Conservar orientación de cámara del usuario entre fotogramas.
        elev, azim = ax.elev, ax.azim
        ax.clear()
        X = np.asarray(frame["X"], dtype=float)
        Y = np.asarray(frame["Y"], dtype=float)
        T = np.asarray(frame["T_display"], dtype=float)
        tau = np.clip(np.asarray(frame.get("shadow", np.ones_like(T)), dtype=float), 0.0, 1.0)
        shade = 1.0 - tau
        norm = Normalize(*self.temp_range)
        rgba = _cms.get_cmap(CMAP_TEMPERATURA)(norm(T))
        # Oscurecer la misma superficie según sombra: una sola escena, no dos paneles.
        dark = 1.0 - 0.48 * np.clip(shade, 0.0, 1.0)
        rgba[..., :3] *= dark[..., None]
        ax.plot_surface(X, Y, np.zeros_like(T), facecolors=rgba, linewidth=0, antialiased=False, shade=False)

        for tree in frame.get("trees", ()):
            x = float(getattr(tree, "x", 0.0)); y = float(getattr(tree, "y", 0.0))
            h = max(0.2, float(getattr(tree, "h", getattr(tree, "altura", 1.0)) or 1.0))
            r = max(0.15, float(getattr(tree, "radio_copa", 0.5) or 0.5))
            profile = canopy_profile(getattr(tree, "forma_copa", None), r, h)
            ax.plot([x, x], [y, y], [0, float(profile["trunk_height"])], color="saddlebrown", linewidth=2.2)
            draw_canopy_3d_mpl(
                ax, tree, color=color_copa(getattr(tree, "especie", "")), alpha=0.90
            )
        for st in frame.get("structures", ()):
            tipo = str(getattr(st, "tipo", "")); x1,y1,x2,y2 = float(st.x1),float(st.y1),float(st.x2),float(st.y2)
            h = max(0.0, float(getattr(st, "altura", 0.0) or 0.0))
            if tipo == "Pared":
                panel=[[(x1,y1,0),(x2,y2,0),(x2,y2,h),(x1,y1,h)]]
                ax.add_collection3d(Poly3DCollection(panel, facecolor="0.5", alpha=0.85, edgecolor="0.25"))
        xmin,xmax=float(np.nanmin(X)),float(np.nanmax(X)); ymin,ymax=float(np.nanmin(Y)),float(np.nanmax(Y))
        max_h=max([1.0]+[float(getattr(t,"h",0.0) or 0.0) for t in frame.get("trees",())]+[float(getattr(st,"altura",0.0) or 0.0) for st in frame.get("structures",())])
        span=max(xmax-xmin,ymax-ymin,1.0); cx=(xmin+xmax)/2; cy=(ymin+ymax)/2
        alt=np.deg2rad(float(frame.get("solar_altitude_deg",0.0))); azi_r=np.deg2rad(float(frame.get("solar_azimuth_deg",0.0)))
        sx=np.sin(azi_r)*np.cos(alt); sy=np.cos(azi_r)*np.cos(alt); sz=max(0.10,float(np.sin(alt)))
        dist=span*1.35; sun=(cx+sx*dist,cy+sy*dist,max_h*0.3+sz*dist)
        ax.scatter([sun[0]],[sun[1]],[sun[2]],s=170,color="#ffd34d",edgecolors="#d88a00",depthshade=False)
        ax.plot([sun[0],cx],[sun[1],cy],[sun[2],0.05],color="#d88a00",alpha=0.45,lw=1.2)
        ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,ymax); ax.set_zlim(0,max(max_h*1.15,span*0.55))
        ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)"); ax.set_zlabel("Altura (m)")
        ax.view_init(elev=elev, azim=azim)
        self._fallback_canvas.draw_idle()

    def render_frame(self, index: int) -> None:
        if not self.frames:
            return
        self.index = max(0, min(int(index), len(self.frames)-1))
        frame = self.frames[self.index]
        self.slider_var.set(self.index)
        if self.controller is not None:
            self.controller.update_animation_frame(frame, render=True)
        else:
            self._render_fallback(frame)
        hour=float(frame.get("hour",0.0)); hh=int(hour)%24; mm=int(round((hour-int(hour))*60))%60
        alt=float(frame.get("solar_altitude_deg",0.0)); azi=float(frame.get("solar_azimuth_deg",0.0))
        self.status.configure(text=f"{self.index+1}/{len(self.frames)} · {hh:02d}:{mm:02d} · Az {azi:.0f}° · El {alt:.0f}°")

    def _slider_changed(self, value: str) -> None:
        try: idx=int(float(value))
        except (TypeError, ValueError): return
        if idx != self.index:
            self.pause(); self.render_frame(idx)

    def first(self): self.pause(); self.render_frame(0)
    def previous(self): self.pause(); self.render_frame((self.index-1)%len(self.frames))
    def next(self): self.pause(); self.render_frame((self.index+1)%len(self.frames))
    def toggle_play(self): self.pause() if self.playing else self.play()

    def play(self):
        if not self.frames or self.playing: return
        self.playing=True; self.play_button.configure(text="⏸ Pausar"); self._schedule_next()

    def pause(self):
        self.playing=False
        try: self.play_button.configure(text="▶ Reproducir")
        except Exception: pass
        if self._after_id is not None:
            try: self.parent.after_cancel(self._after_id)
            except tk.TclError: pass
            self._after_id=None

    def _schedule_next(self):
        if self.playing:
            self._after_id=self.parent.after(max(60,int(self.speed_ms.get())),self._tick)

    def _tick(self):
        self._after_id=None
        if not self.playing: return
        self.render_frame((self.index+1)%len(self.frames)); self._schedule_next()

    def close(self):
        self.pause()
        if self.controller is not None:
            try: self.controller.close()
            except Exception: pass
            self.controller=None
        if self._fallback_fig is not None:
            try: self._fallback_fig.clear()
            except Exception: pass
