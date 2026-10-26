"""Restauración del proyecto y del carrusel, separada del montaje de la ventana."""
import os
import tkinter as tk
import numpy as np
import pandas as pd
import diseno as design
import modelo_con_excel as modelo
from PIL import Image, ImageTk
from services.analysis_record_store import AnalysisRecordStore
from image_processor import DEFAULT_MATRIX_SIZE,normalize_matrix_size


class SnapshotRestorationMixin:
    def _get_analysis_store(self):
        """Devuelve la base de análisis del proyecto actual.

        La instancia se recrea automáticamente al cambiar de proyecto. La
        SQLite vive dentro de la carpeta del proyecto, por lo que se incluye
        también al exportar/duplicar el proyecto.
        """
        project = self.project_manager.current_project
        if project is None:
            self.analysis_store = None
            return None
        root = os.path.abspath(project.root_path)
        store = getattr(self, "analysis_store", None)
        if store is None or os.path.abspath(store.project_root) != root:
            self.analysis_store = AnalysisRecordStore(root)
        return self.analysis_store


    def _recargar_analisis_desde_base(self, *, migrate_legacy=True):
        """Sincroniza el cache ``self.snapshots`` desde SQLite.

        ``snapshots`` se mantiene porque servicios de reportes/análisis ya lo
        consumen, pero desde v17 es un cache de los registros persistentes y
        no el mecanismo primario de almacenamiento del carrusel.
        """
        store = self._get_analysis_store()
        if store is None:
            return
        if migrate_legacy:
            store.migrate_legacy_snapshots(getattr(self, "snapshots", []))
        self.snapshots = store.list_entries(complete_only=True)


    def restore_project_artifacts(self):
        # v17: SQLite es la fuente primaria del carrusel. Los snapshots JSON
        # viejos se migran una sola vez de forma idempotente.
        self._recargar_analisis_desde_base(migrate_legacy=True)
        preferred=getattr(self,'_restore_analysis_id',None)
        self.poblar_lista_snapshots(selected_analysis_id=preferred)
        if self.snapshots:
            # Selecciona y carga el último elemento analizado —
            # equivalente a lo que hacía antes (imagen+curva+máscara),
            # pero ahora también restaura % de sombra y la barra de Tmrt,
            # y el resto del historial queda disponible para elegir.
            target=next((i for i,entry in enumerate(self.snapshots)
                if preferred and entry.get('analysis_id')==preferred),len(self.snapshots)-1)
            self.cargar_snapshot(target)
        else:
            # Proyecto sin snapshots todavía: mantener el comportamiento
            # anterior por si hay rutas sueltas guardadas.
            self.last_image_path = self._resolve_artifact_path(self.last_image_path, os.path.join("entradas", "imagenes"))
            self.last_curve_path = self._resolve_artifact_path(self.last_curve_path, os.path.join("analisis", "elementos"))
            self.last_mask_path = self._resolve_artifact_path(self.last_mask_path, os.path.join("analisis", "elementos"))
            if self.last_image_path and os.path.exists(self.last_image_path):
                self._load_image_from_path(self.last_image_path)
            if self.last_curve_path and os.path.exists(self.last_curve_path):
                self._load_curve_from_path(self.last_curve_path)
            if self.last_mask_path and os.path.exists(self.last_mask_path):
                self._load_mask_from_path(self.last_mask_path)
        self._restore_excel_files()


    def _restore_excel_files(self):
        project = self.project_manager.current_project
        if project is not None:
            if os.path.exists(project.layout.edit_excel):
                self.last_edit_excel_path = project.layout.edit_excel
            if os.path.exists(project.layout.model_excel):
                self.last_model_excel_path = project.layout.model_excel
        if self.last_edit_excel_path and os.path.exists(self.last_edit_excel_path):
            # abrir_archivo ya regenera el gráfico de edición internamente
            # (llama a actualizar_grafico al final) — no hace falta nada más acá.
            loaded = design.abrir_archivo(self.vars, self, filepath=self.last_edit_excel_path)
            if loaded:
                self.last_edit_excel_path = loaded
        if self.last_model_excel_path and os.path.exists(self.last_model_excel_path):
            loaded = modelo.cargar_excel(self.vars_modelo, filepath=self.last_model_excel_path)
            if loaded:
                self.last_model_excel_path = loaded
                # NUEVO: cargar_excel() solo llena vars_modelo, no vuelve a
                # dibujar nada — el modelo quedaba con datos cargados pero
                # invisible hasta que el usuario tocara algún control a
                # mano. Se regenera acá con el mismo método que usa el
                # botón "Ejecutar modelo", para que quede consistente con
                # la ubicación/modo ya restaurados del proyecto.
                try:
                    self.generar_grafico_modelo()
                except Exception as exc:
                    print(f"[restore] No se pudo regenerar el gráfico del modelo automáticamente: {exc}")


    def _resolve_artifact_path(self, path_value, folder, filename=None):
        if path_value and os.path.exists(path_value):
            return path_value
        project = self.project_manager.current_project
        if not project:
            return path_value
        if filename:
            candidate = os.path.join(project.root_path, folder, filename)
        else:
            candidate = os.path.join(project.root_path, folder, os.path.basename(path_value)) if path_value else None
        if candidate and os.path.exists(candidate):
            return candidate
        return path_value


    def poblar_lista_snapshots(self, selected_analysis_id=None):
        """Sincroniza contador y carrusel con la base de análisis.

        ``self.snapshots`` sigue existiendo como cache compatible para los
        reportes, pero desde v17 cada entrada completa tiene ``analysis_id`` y
        proviene de SQLite.
        """
        if hasattr(self, "status_elements_var"):
            self.status_elements_var.set(f"Elementos: {len(self.snapshots)}")
        if hasattr(self, "carrusel_inner"):
            self._carrusel_actualizar(selected_analysis_id=selected_analysis_id)


    def _registrar_histograma_en_carrusel(self):
        """Persiste/actualiza el análisis actual y refresca el carrusel.

        Antes esta función agregaba una entrada provisional a la lista. Esa
        lógica era la causa del bug de duplicación: seleccionar una miniatura
        regeneraba la curva/histograma y volvía a hacer ``append``. Ahora el
        registro se guarda por ``analysis_id`` con UPSERT en SQLite.
        """
        hist = getattr(self, "last_histogram_path", None)
        if not hist or not os.path.exists(str(hist)):
            return
        return self.snapshot_service.capture_analysis_record(auto=True)


    def cargar_snapshot(self, index: int):
        """Restaura un registro completo del carrusel sin recalcularlo.

        Desde v17 el click recupera de SQLite + artefactos persistidos:
        foto original, curva Tmrt, máscaras/ROIs de cálculo y referencia,
        matrices válidas, promedio gris, cobertura, atenuación y
        transmitancia. Para snapshots legacy se conservan fallbacks.
        """
        if getattr(self,'photo_exclusions_pending',False) and not getattr(self,'_suspend_autosave_tracking',False):
            from tkinter import messagebox
            messagebox.showinfo('Exclusiones pendientes','Genere la curva para actualizar el elemento antes de cambiar de análisis.')
            return
        if index < 0 or index >= len(self.snapshots):
            return
        entry = self.snapshots[index]
        project = self.project_manager.current_project
        if not project:
            return
        root = project.root_path

        def _abs(rel_path):
            if not rel_path:
                return None
            from core.safe_paths import safe_project_reference
            return safe_project_reference(root, rel_path)

        # Limpiar completamente el estado visual del elemento anterior antes
        # de restaurar el seleccionado. Luego fijamos el ID para que un futuro
        # Guardar/Recalcular haga UPDATE del mismo registro.
        self._reset_panel2_for_new_image()
        detection = entry.get("deteccion_candidatos")
        self.shadow_detection_meta = detection if isinstance(detection, dict) else None
        self.shadow_coverage_fraction = detection.get("coverage_fraction") if isinstance(detection, dict) else None
        self.current_analysis_id = entry.get("analysis_id")

        image_path = _abs(entry.get("image"))
        curve_path = _abs(entry.get("curve"))
        reference_path = _abs(entry.get("reference"))
        matrix_path = _abs(entry.get("matrix"))
        calc_data_path = _abs(entry.get("calc_data"))
        reference_data_path = _abs(entry.get("reference_data"))
        photo_analysis_path = _abs(entry.get("photo_analysis_data"))
        tmrt_data_path = _abs(entry.get("tmrt_data"))
        histogram_path = _abs(entry.get("histogram"))
        classification_path = _abs(entry.get("shadow_classification"))
        temperature_summary_path = _abs(entry.get("temperature_summary"))

        if image_path and os.path.exists(image_path):
            self._load_image_from_path(image_path)
            # En snapshots históricos la imagen puede llamarse elementoN.png;
            # el nombre conceptual del árbol es el label guardado.
            if entry.get("label"):
                self.current_image_stem = str(entry["label"])

        # Nuevos bundles NPZ preservan máscara válida y máscara full-size.
        calc_loaded = self._load_area_bundle(calc_data_path, "calculo")
        ref_loaded = self._load_area_bundle(reference_data_path, "referencia")

        # Fallback para snapshots <=v16.
        if not ref_loaded and reference_path and os.path.exists(reference_path):
            self._load_mask_from_path(reference_path)
        if not calc_loaded and matrix_path and os.path.exists(matrix_path):
            try:
                self.shape_selector.area_seleccionada = pd.read_excel(matrix_path).to_numpy()
                self.shape_selector.area_seleccionada_mask = np.ones_like(
                    self.shape_selector.area_seleccionada, dtype=bool
                )
                self.last_matrix_path = matrix_path
            except Exception:
                pass

        self.area_calculo_done = self.shape_selector.area_seleccionada is not None
        self.area_referencia_done = self.shape_selector.area_referencia is not None

        # Cada análisis puede haberse calculado con una resolución distinta.
        # Al seleccionarlo, el control refleja la resolución REAL del bundle
        # restaurado; esto no recalcula nada ni modifica sus resultados.
        matrix_n = entry.get("matrix_size")
        if self.area_calculo_done:
            arr_calc = np.asarray(self.shape_selector.area_seleccionada)
            if arr_calc.ndim == 2 and arr_calc.shape[0] == arr_calc.shape[1]:
                matrix_n = int(arr_calc.shape[0])
        matrix_n = normalize_matrix_size(matrix_n if matrix_n is not None else DEFAULT_MATRIX_SIZE)
        previous_suspend = getattr(self, "_suspend_autosave_tracking", False)
        self._suspend_autosave_tracking = True
        try:
            self.matriz_size.set(matrix_n)
            self.panel2_advanced_mode.set(matrix_n != DEFAULT_MATRIX_SIZE)
            self._toggle_panel2_advanced()
        finally:
            self._suspend_autosave_tracking = previous_suspend

        if self.area_calculo_done:
            self.area_ref_button.config(state=tk.NORMAL)
        if self.area_calculo_done and self.area_referencia_done:
            self.confirm_button.config(state=tk.NORMAL)

        # Restaurar ROIs visuales. Las máscaras full-size quedan además en
        # ShapeSelector para cálculos/inspección posteriores.
        self.shape_selector.shape_patch_calculo = self._restaurar_patch(
            entry.get("poly_calculo"), "blue")
        self.shape_selector.shape_patch_referencia = self._restaurar_patch(
            entry.get("poly_referencia"), "red")
        if self.ax1 is not None and self.img_rgb is not None:
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self._setup_hover_shadow_percent_photo(self.ax1, self.canvas1, self.img_rgb)
            if self.shape_selector.shape_patch_calculo is not None:
                self.ax1.add_patch(self.shape_selector.shape_patch_calculo)
            if self.shape_selector.shape_patch_referencia is not None:
                self.ax1.add_patch(self.shape_selector.shape_patch_referencia)
            self.canvas1.draw()

        # Valores de las áreas: se recuperan, no se vuelven a inferir.
        calc_text = entry.get("area_calculo_text")
        ref_text = entry.get("area_referencia_text")
        if calc_text:
            self.lbl_dimensiones_calculo.config(text=calc_text)
        elif entry.get("area_calculo_px") is not None:
            self.lbl_dimensiones_calculo.config(
                text=f"Área de Cálculo: {int(entry['area_calculo_px'])} px válidos")
        if ref_text:
            self.lbl_dimensiones_referencia.config(text=ref_text)
        elif entry.get("area_referencia_px") is not None:
            self.lbl_dimensiones_referencia.config(
                text=f"Área de Referencia: {int(entry['area_referencia_px'])} px válidos")

        promedio = entry.get("promedio_gris")
        if isinstance(promedio, (int, float)):
            self.ref_gray_mean = float(promedio)
        elif self.shape_selector.area_referencia is not None:  # legacy
            try:
                self.ref_gray_mean = self.image_processor.media_valida(
                    self.shape_selector.area_referencia,
                    self.shape_selector.area_referencia_mask,
                )
            except Exception:
                self.ref_gray_mean = None
        if self.ref_gray_mean is not None:
            self.lbl_promedio_referencia.config(
                text=f"Promedio Gris Referencia: {self.ref_gray_mean:.2f}")

        cobertura = entry.get("cobertura_sombra", entry.get("porcentaje_sombra"))
        atenuacion = entry.get("atenuacion_sombra")
        tau_eff = entry.get("transmitancia_efectiva")
        self.cobertura_sombra = cobertura
        self.atenuacion_sombra = atenuacion
        self.porcentaje_sombra = cobertura
        if isinstance(cobertura, (int, float)):
            self.lbl_porcentaje_sombra.config(text=f"Cobertura de sombra: {cobertura:.2f}%")
        if isinstance(atenuacion, (int, float)) and hasattr(self, "lbl_atenuacion_sombra"):
            self.lbl_atenuacion_sombra.config(text=f"Atenuación en sombra: {atenuacion:.2f}%")
        if isinstance(tau_eff, (int, float)) and hasattr(self, "lbl_transmitancia_sombra"):
            self.lbl_transmitancia_sombra.config(text=f"Transmitancia efectiva: {tau_eff*100:.2f}%")

        # Recuperar exactamente el análisis fotográfico y mapas guardados.
        self.shadow_photo_analysis = self._load_photo_analysis_bundle(photo_analysis_path, entry)
        if self.shadow_photo_analysis is None and self.area_calculo_done and self.area_referencia_done:
            # Compatibilidad exclusiva con registros viejos que no guardaban
            # los mapas: solo en ese caso se recompone desde matrices.
            try:
                self.shadow_photo_analysis = self.image_processor.analizar_sombra_fotografica(
                    self.shape_selector.area_seleccionada,
                    self.shape_selector.area_referencia,
                    mascara_area=self.shape_selector.area_seleccionada_mask,
                    mascara_referencia=self.shape_selector.area_referencia_mask,
                )
            except Exception:
                self.shadow_photo_analysis = None
        if self.shadow_photo_analysis is not None and hasattr(self, "shadow_mask_button"):
            self.shadow_mask_button.config(state=tk.NORMAL)
        if classification_path and os.path.exists(classification_path):
            self.last_shadow_classification_path = classification_path
        if temperature_summary_path and os.path.exists(temperature_summary_path):
            self.last_temp_graph_path = temperature_summary_path
        if histogram_path and os.path.exists(histogram_path):
            self.last_histogram_path = histogram_path

        # Curva: cargar matrices guardadas y reconstruir canvas interactivo sin
        # llamar mostrar_curvas_nivel(). Eso evita duplicar y evita recalcular.
        tmrt_loaded = self._load_tmrt_bundle(tmrt_data_path)
        if tmrt_loaded:
            self._render_stored_tmrt_map(entry)
        elif curve_path and os.path.exists(curve_path):
            self._load_curve_from_path(curve_path)
        if curve_path and os.path.exists(curve_path):
            self.last_curve_path = curve_path

        # Barra Tmrt escalar, si el registro la tenía.
        tmrt_sombra = entry.get("tmrt_sombra")
        temp_ambient = entry.get("temp_ambient")
        tmrt_sol = entry.get("tmrt_sol")
        valor_sol_grafico = tmrt_sol if tmrt_sol is not None else temp_ambient
        if tmrt_sombra is not None and valor_sol_grafico is not None:
            self.tmrt_result = {
                "Tmrt_sol": tmrt_sol,
                "Tmrt_sombra": tmrt_sombra,
                "Delta_Tmrt": entry.get("delta_tmrt"),
                "Modelo_Tmrt": entry.get("modelo_tmrt"),
                "Effective_scenario": entry.get("effective_scenario_point"),
            }
            if hasattr(self, "lbl_tmrt_sol") and tmrt_sol is not None:
                self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {tmrt_sol:.2f} °C")
            if hasattr(self, "lbl_tmrt_sombra"):
                self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {tmrt_sombra:.2f} °C")
            if hasattr(self, "lbl_delta_tmrt") and entry.get("delta_tmrt") is not None:
                self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {entry['delta_tmrt']:.2f} °C")
            if hasattr(self, "graph_frame"):
                self._show_temperature_graph(valor_sol_grafico, tmrt_sombra)

        self.curve_button.config(state=tk.NORMAL if self.area_calculo_done else tk.DISABLED)
        if hasattr(self,'photo_exclusion_button'):
            self.photo_exclusion_button.config(state=tk.NORMAL if entry.get('complete') else tk.DISABLED)
        self._carrusel_marcar(index)


    def _load_area_bundle(self, file_path, kind: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with np.load(file_path, allow_pickle=False) as data:
                values = np.asarray(data["values"])
                valid = np.asarray(data["valid_mask"], dtype=bool)
                full = np.asarray(data["full_mask"], dtype=bool) if "full_mask" in data else np.empty((0, 0), dtype=bool)
            if kind == "calculo":
                self.shape_selector.area_seleccionada = values
                self.shape_selector.area_seleccionada_mask = valid
                self.shape_selector.mask_calculo_full = full if full.size else None
                self.last_matrix_path = file_path
            else:
                self.shape_selector.area_referencia = values
                self.shape_selector.area_referencia_mask = valid
                self.shape_selector.mask_referencia_full = full if full.size else None
                self.last_mask_path = file_path
            return True
        except Exception as exc:
            print(f"[carrusel] no se pudo cargar bundle {kind}: {exc}")
            return False


    def _load_photo_analysis_bundle(self, file_path, entry):
        arrays = {}
        if file_path and os.path.exists(file_path):
            try:
                with np.load(file_path, allow_pickle=False) as data:
                    arrays = {key: np.asarray(data[key]) for key in data.files}
            except Exception as exc:
                print(f"[carrusel] no se pudo cargar análisis fotográfico: {exc}")
                arrays = {}
        if not arrays and not entry.get("algoritmo_sombra"):
            return None
        restored = {
            "algorithm": entry.get("algoritmo_sombra", "snapshot-restored"),
            "coverage_pct": entry.get("cobertura_sombra", entry.get("porcentaje_sombra")),
            "attenuation_pct": entry.get("atenuacion_sombra"),
            "shadow_transmittance": entry.get("transmitancia_sombra"),
            "effective_transmittance": entry.get("transmitancia_efectiva"),
            "effective_attenuation_pct": entry.get("atenuacion_efectiva"),
            "threshold_ratio": entry.get("umbral_sombra_ratio"),
            "reference_gray": entry.get("promedio_gris"),
            "legacy_shadow_index_pct": entry.get("indice_sombra_legacy"),
            "contrast_policy": entry.get("photo_contrast_policy","legacy_mad"),
            **arrays,
        }
        from services.photo_selection import restore_analysis_mask
        return restore_analysis_mask(restored,entry,self.shape_selector.area_seleccionada,
            self.shape_selector.area_referencia,self.shape_selector.area_seleccionada_mask,
            self.shape_selector.area_referencia_mask)


    def _load_tmrt_bundle(self, file_path) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with np.load(file_path, allow_pickle=False) as data:
                restored = {}
                for key in data.files:
                    value = np.asarray(data[key])
                    if value.ndim == 0:
                        restored[key] = float(value)
                    elif np.issubdtype(value.dtype, np.floating):
                        restored[key] = value.astype(np.float32, copy=False)
                    else:
                        restored[key] = value
            tmrt = restored.get("tmrt")
            if tmrt is None:
                return False
            self.tmrt_hover_data = restored
            self.tmrt_map = np.asarray(tmrt, dtype=np.float32)
            self.curvas_nivel_creadas = True
            self._curve_pinned_pixel = None
            return True
        except Exception as exc:
            print(f"[carrusel] no se pudo cargar datos Tmrt: {exc}")
            return False


    def _render_stored_tmrt_map(self, entry):
        """Redibuja la curva guardada a partir de sus matrices, sin física."""
        self.tmrt_map_scenario = entry.get("effective_scenario_map")
        mapa = np.asarray(self.tmrt_map, dtype=np.float32)
        finite = mapa[np.isfinite(mapa)]
        if not finite.size:
            return
        from plot_style import CMAP_CURVAS_NIVEL, agregar_colorbar_temperatura

        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None
        self.fig2.clf()
        ax = self.fig2.add_subplot(111)
        self.ax2 = ax
        x_disp, y_disp, mapa_disp, _stride = self._contour_display_grid(mapa)
        tmin, tmax = float(np.min(finite)), float(np.max(finite))
        span = tmax - tmin
        if span > 1e-9:
            niveles = np.linspace(tmin, tmax, 21)
            relleno = ax.contourf(x_disp, y_disp, mapa_disp, levels=niveles, cmap=CMAP_CURVAS_NIVEL, vmin=tmin, vmax=tmax, antialiased=True)
            ax.contour(x_disp, y_disp, mapa_disp, levels=niveles[::2], colors="0.35", linewidths=0.45, alpha=0.55)
            ticks = np.linspace(tmin, tmax, 6)
        else:
            eps = max(0.01, abs(tmin) * 1e-6)
            relleno = ax.contourf(x_disp, y_disp, mapa_disp, levels=[tmin-eps, tmin+eps], cmap=CMAP_CURVAS_NIVEL, vmin=tmin-eps, vmax=tmin+eps)
            ticks = np.array([tmin])
        ax.set_xlim(0, mapa.shape[1] - 1)
        ax.set_ylim(0, mapa.shape[0] - 1)
        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        ax.set_title(f"Tmrt guardada — {entry.get('label', 'elemento')}\nregistro {entry.get('analysis_id', '')[:8]}", fontsize=9)
        agregar_colorbar_temperatura(self.fig2, ax, relleno, unidad="°C", etiqueta="Tmrt", ticks=ticks)
        ax.text(0.01, 0.01, f"Rango guardado: {tmin:.2f}–{tmax:.2f} °C", transform=ax.transAxes, fontsize=7.5,
                va="bottom", ha="left", bbox=dict(boxstyle="round", fc="white", ec="0.75", alpha=0.82))
        self.fig2.tight_layout(pad=0.8)
        widget = self.canvas2.get_tk_widget()
        if not widget.winfo_ismapped():
            widget.pack(fill="both", expand=True)
        self._setup_hover_tmrt_map(ax, self.canvas2)
        self.canvas2.draw_idle()


    def _restaurar_patch(self, datos, color):
        """Reconstruye el patch dibujado (polígono/rectángulo/círculo)
        a partir de lo serializado en el snapshot."""
        if not isinstance(datos, dict):
            return None
        from matplotlib.patches import Circle, Polygon, Rectangle
        tipo = datos.get("tipo")
        pts = datos.get("puntos") or []
        if tipo == "rectangulo" and len(pts) >= 4:
            return Rectangle((pts[0], pts[1]), pts[2], pts[3],
                             edgecolor=color, facecolor="none", linewidth=2)
        if tipo == "circulo" and len(pts) >= 3:
            return Circle((pts[0], pts[1]), pts[2],
                          edgecolor=color, facecolor="none", linewidth=2)
        if len(pts) >= 3:
            return Polygon(pts, closed=True, edgecolor=color,
                           facecolor=color, alpha=0.3, linewidth=2)
        return None


    def _load_curve_from_path(self, file_path: str):
        if not self.curva_frame:
            return
        # CORRECCIÓN: canvas2 es un lienzo vacío (ejes 0-1 en blanco) que
        # _reset_panel2_for_new_image() vuelve a mostrar como placeholder.
        # mostrar_curvas_nivel() ya lo ocultaba al generar una curva nueva,
        # pero esta función (usada al restaurar un proyecto o un elemento
        # del historial) no lo hacía — quedaba packed al lado de la curva
        # real, achicándola. Es exactamente lo que se ve en el frame en
        # blanco de la captura.
        if self.canvas2 is not None:
            self.canvas2.get_tk_widget().pack_forget()
        with Image.open(file_path) as img:
            self.curva_img_pil_original = img.copy()
        resized_img = self._fit_image_to_frame(self.curva_img_pil_original, self.curva_frame)
        photo = ImageTk.PhotoImage(resized_img)
        if self.curva_label is None:
            self.curva_label = tk.Label(self.curva_frame, image=photo, bg=self.curva_frame.cget("bg"))
            self.curva_label.pack(expand=True, fill='both')
        else:
            self.curva_label.configure(image=photo)
        self.curva_photo = photo
        self.curva_label.image = photo


    def _load_mask_from_path(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in (".xlsx", ".xls"):
                data = pd.read_excel(file_path)
                self.shape_selector.area_referencia = data.to_numpy()
                self.shape_selector.area_referencia_mask = np.ones_like(self.shape_selector.area_referencia, dtype=bool)
            elif ext in (".png", ".jpg", ".jpeg"):
                with Image.open(file_path) as img:
                    self.shape_selector.area_referencia = np.asarray(img.convert("L"), dtype=np.uint8).copy()
                self.shape_selector.area_referencia_mask = np.ones_like(self.shape_selector.area_referencia, dtype=bool)
        except Exception:
            return


