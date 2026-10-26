"""Selección, máscaras y mapas fotográficos; controlador de UI extraído."""
import os
from datetime import datetime
import pandas as pd
import tkinter as tk
from tkinter import messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
from services.analysis_record_store import AnalysisRecordStore
from core import thermal_comfort
from core.effective_scenario import scenario_date
from core.uncertainty import estimate_tmrt_uncertainty
from image_processor import normalize_matrix_size
from ui.modal_style import prepare_dialog
from ui.solar_indicator import add_solar_indicator_2d


class PhotoAnalysisMixin:
    @property
    def shadow_quality(self):
        """Alias histórico de cobertura fraccional; no representa calidad."""
        return self.shadow_coverage_fraction

    @shadow_quality.setter
    def shadow_quality(self, value):
        self.shadow_coverage_fraction = value

    def _analizar_seleccion_fotografica(self):
        from services.photo_selection import analyze_selection
        selector=self.shape_selector
        return analyze_selection(self.image_processor,selector.area_seleccionada,selector.area_referencia,
            selector.area_seleccionada_mask,selector.area_referencia_mask,
            previous=getattr(self,'shadow_photo_analysis',None))

    def editar_exclusiones_fotograficas(self):
        if not self.require_project('excluir materiales de la fotografía'):return
        selector=self.shape_selector
        if selector.area_seleccionada is None or selector.area_referencia is None:
            messagebox.showinfo('Exclusiones','Primero seleccione el área de cálculo y su referencia iluminada.');return
        # Only existing complete elements can be corrected: pending state can then bind to their persisted inputs.
        store=self._get_analysis_store()
        record=store.get(self.current_analysis_id) if self.current_analysis_id else None
        if not record or not record.get('complete'):
            messagebox.showinfo('Exclusiones','Genere primero la curva del elemento; después podrá corregir y guardar sus exclusiones.');return
        from ui.photo_exclusion_editor import PhotoExclusionEditor
        from services.photo_selection import selection_signature
        analysis=self._analizar_seleccion_fotografica()
        shape=np.asarray(selector.area_seleccionada).shape
        mask=analysis.get('exclusion_mask')
        if mask is None:mask=np.zeros(shape,dtype=bool)
        valid=np.isfinite(selector.area_seleccionada)
        if selector.area_seleccionada_mask is not None:valid &= np.asarray(selector.area_seleccionada_mask,dtype=bool)
        signature=selection_signature(selector.area_seleccionada,selector.area_referencia,
            selector.area_seleccionada_mask,selector.area_referencia_mask)
        PhotoExclusionEditor(self.root,selector.area_seleccionada,valid,mask,
            lambda edited:self._apply_photo_exclusions(edited,expected_signature=signature),
            on_discard=self.descartar_exclusiones_pendientes if getattr(self,'photo_exclusions_pending',False) else None)

    def descartar_exclusiones_pendientes(self):
        matches=[i for i,entry in enumerate(self.snapshots) if entry.get('analysis_id')==self.current_analysis_id]
        if not matches:raise ValueError('No hay un elemento guardado que restaurar.')
        self.photo_exclusions_pending=False
        self.cargar_snapshot(matches[0]);self.mark_dirty()

    def _set_photo_coverage_labels(self,analysis):
        self.cobertura_sombra=analysis['coverage_pct'];self.porcentaje_sombra=self.cobertura_sombra
        self.atenuacion_sombra=analysis['attenuation_pct']
        count=analysis.get('excluded_pixels',0)
        suffix=f' · excluidos {count} px de rejilla' if count else ''
        self.lbl_porcentaje_sombra.config(text=f'Cobertura fotográfica estimada: {self.cobertura_sombra:.2f}%{suffix}')
        self.lbl_atenuacion_sombra.config(text=f'Atenuación en sombra: {self.atenuacion_sombra:.2f}%')
        self.lbl_transmitancia_sombra.config(text=f'Transmitancia efectiva: {analysis["effective_transmittance"]*100:.2f}%')

    def _invalidate_photo_thermal_results(self):
        self.tmrt_result=None;self.tmrt_map=None;self.tmrt_hover_data=None;self.tmrt_map_scenario=None
        self.curvas_nivel_creadas=False
        self._curve_hover_annotation=None;self._curve_hover_canvas=None;self._curve_pinned_pixel=None
        label=getattr(self,'curva_label',None)
        if label is not None:label.destroy();self.curva_label=None
        self.curva_photo=None
        uncertainty=getattr(self,'lbl_tmrt_uncertainty',None)
        if uncertainty is not None:uncertainty.config(text='Incertidumbre operativa: recalcular curva')
        for name in ('last_curve_path','last_histogram_path','last_temp_graph_path','last_shadow_classification_path'):
            setattr(self,name,None)
        self._clear_temperature_graph()
        for name,prefix in (('lbl_tmrt_sol','Tmrt al sol'),('lbl_tmrt_sombra','Tmrt en sombra'),('lbl_delta_tmrt','ΔTmrt')):
            label=getattr(self,name,None)
            if label is not None:label.config(text=f'{prefix}: recalcular curva')
        figure=getattr(self,'fig2',None);canvas=getattr(self,'canvas2',None)
        if canvas is not None:
            for name in ('_curve_hover_cid','_curve_click_cid'):
                token=getattr(self,name,None)
                if token is not None:canvas.mpl_disconnect(token);setattr(self,name,None)
        if figure is not None:
            figure.clf();self.ax2=figure.add_subplot(111)
            if canvas is not None:canvas.draw_idle()
        button=getattr(self,'save_dataset_button',None)
        if button is not None:button.config(state=tk.DISABLED)

    def _apply_photo_exclusions(self,mask,*,expected_signature=None,mark_dirty=True):
        from services.photo_selection import analyze_selection,selection_signature
        selector=self.shape_selector
        signature=selection_signature(selector.area_seleccionada,selector.area_referencia,
            selector.area_seleccionada_mask,selector.area_referencia_mask)
        if expected_signature is not None and expected_signature!=signature:
            raise ValueError('La selección cambió. Cierre y vuelva a abrir el editor.')
        candidate=analyze_selection(self.image_processor,selector.area_seleccionada,selector.area_referencia,
            selector.area_seleccionada_mask,selector.area_referencia_mask,exclusions=mask,reuse_previous=False)
        previous=getattr(self,'shadow_photo_analysis',None) or {}
        old=previous.get('exclusion_mask');new=candidate.get('exclusion_mask')
        equal=(old is None and new is None) or (old is not None and new is not None and np.array_equal(old,new))
        self.shadow_photo_analysis=candidate;self._set_photo_coverage_labels(candidate)
        if not equal:
            self.photo_exclusions_pending=True
            self.shadow_detection_meta=None;self.shadow_coverage_fraction=None
            self._invalidate_photo_thermal_results()
            self.curve_button.config(state=tk.NORMAL)
            if mark_dirty:self.mark_dirty()
        return not equal

    def restore_pending_photo_exclusions(self,state):
        from core.photo_exclusions import decode_state
        mask,signature,pending=decode_state(state)
        self._apply_photo_exclusions(mask,expected_signature=signature,mark_dirty=False)
        if pending:
            self.photo_exclusions_pending=True
            self._invalidate_photo_thermal_results()

    def confirmar_seleccion(self):
        if not self.require_project("confirmar selección"):
            return
        # Verificamos que ambas áreas hayan sido seleccionadas
        if self.shape_selector.area_seleccionada is not None and self.shape_selector.area_referencia is not None:
            # v11: se separan explícitamente cobertura geométrica e
            # intensidad/atenuación de sombra. El porcentaje que alimenta
            # el modelo como S es COBERTURA; la transmitancia de las zonas
            # clasificadas sombra se estima por separado contra la referencia.
            analisis = self._analizar_seleccion_fotografica()
            self.shadow_photo_analysis = analisis
            self.cobertura_sombra = analisis["coverage_pct"]
            self.atenuacion_sombra = analisis["attenuation_pct"]
            # Compatibilidad con módulos/proyectos anteriores: porcentaje_sombra
            # pasa a significar cobertura cuando el origen es fotográfico v2.
            self.porcentaje_sombra = self.cobertura_sombra
            self.lbl_porcentaje_sombra.config(
                text=f"Cobertura fotográfica estimada: {self.cobertura_sombra:.2f}%"
            )
            self.lbl_atenuacion_sombra.config(
                text=f"Atenuación en sombra: {self.atenuacion_sombra:.2f}%"
            )
            self.lbl_transmitancia_sombra.config(
                text=f"Transmitancia efectiva: {analisis['effective_transmittance']*100:.2f}%"
            )
            self.shadow_coverage_fraction = None
            self.shadow_detection_meta = None
            if self.shadow_detector_enabled.get() and self.img_rgb is not None:
                detected = self.shadow_detector.detect_shadow_candidates(self.img_rgb, method="adaptive")
                roi = self.shape_selector.mask_calculo_full
                if roi is None or np.asarray(roi).shape != detected.shape:
                    raise ValueError("La ROI de detección no coincide con la imagen; vuelva a seleccionar el área.")
                coverage_meta = self.shadow_detector.compute_shadow_coverage(
                    detected, roi_mask=np.asarray(roi, dtype=bool)
                )
                if analisis.get('exclusion_mask') is not None:
                    local=self.shadow_detector.detect_shadow_candidates(np.nan_to_num(self.shape_selector.area_seleccionada).astype(np.uint8),method='adaptive')
                    coverage_meta=self.shadow_detector.compute_shadow_coverage(local,
                        roi_mask=np.isfinite(self.shape_selector.area_seleccionada) & (np.ones(local.shape,dtype=bool) if self.shape_selector.area_seleccionada_mask is None else self.shape_selector.area_seleccionada_mask),exclusion_mask=analisis['exclusion_mask'])
                    coverage_meta['scope']='corrected_analysis_grid'
                self.shadow_coverage_fraction = coverage_meta["coverage_fraction"]
                self.shadow_detection_meta = coverage_meta
                
            # Habilitar el botón para curvas de nivel
            self.curve_button.config(state=tk.NORMAL)
            if hasattr(self, "shadow_mask_button"):
                self.shadow_mask_button.config(state=tk.NORMAL)
            self._guardar_mascara_clasificacion_sombra()
            if not self.current_image_path or not os.path.exists(self.current_image_path):
                print(f"[confirmar] Ruta de imagen inexistente: {self.current_image_path}")
                messagebox.showerror("Error", "La imagen del proyecto no existe. Cargá la imagen nuevamente.")
                return            
            self.dataset_saver.save_dataset(
                img_filename=self.current_image_basename,
                mask_filename=f"{self.current_image_stem}_mask.png",
                save_image=False,
            )
            self.shape_selector.disable_selection()
            self.area_calc_button.config(state=tk.DISABLED)
            self.area_ref_button.config(state=tk.DISABLED)
            self.mark_dirty()
        else:
            print("Error: No se ha seleccionado un área válida.")


    def _guardar_mascara_clasificacion_sombra(self):
        """Guarda una máscara reproducible sombra/sol para auditoría v11."""
        analisis = self.shadow_photo_analysis
        project = self.project_manager.current_project
        if not analisis or project is None:
            return None
        mask = np.asarray(analisis.get("shadow_mask"), dtype=np.float32)
        if mask.size == 0:
            return None
        valid = np.isfinite(mask)
        if not np.any(valid):
            return None

        if not self.current_analysis_id:
            self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
        out_path = project.layout.element_paths(self.current_analysis_id)["shadow_classification"]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        fig, ax = plt.subplots(figsize=(6, 5))
        display = np.ma.masked_invalid(mask)
        im = ax.imshow(display, cmap=(plt.get_cmap("gray_r").with_extremes(bad="#ba8a8a") if analisis.get("excluded_pixels",0) else "gray_r"), vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(
            "Clasificación fotográfica sombra / sol\n"
            f"Cobertura {analisis['coverage_pct']:.1f}% · "
            f"Atenuación sombra {analisis['attenuation_pct']:.1f}% · "
            f"umbral I/Iref={analisis['threshold_ratio']:.3f}" +
            (f" · excluidos {analisis['excluded_pixels']} px de rejilla" if analisis.get('excluded_pixels',0) else ''),
            fontsize=9,
        )
        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1], fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels(["Sol", "Sombra"])
        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.last_shadow_classification_path = str(out_path)
        return str(out_path)


    def mostrar_mascara_sombra(self):
        """Muestra la clasificación sombra/sol y la atenuación óptica local."""
        analisis = self.shadow_photo_analysis
        if not analisis:
            messagebox.showinfo(
                "Sombra fotográfica",
                "Primero confirme un área de cálculo y un área de referencia.",
            )
            return

        dlg = tk.Toplevel(self.root)
        prepare_dialog(dlg, self.root, modal=False, resizable=True, minsize=(720, 440))
        dlg.title("Cobertura e intensidad de sombra")
        dlg.geometry("920x520")
        dlg.configure(bg=self.palette["background"])

        fig, axes = plt.subplots(1, 2, figsize=(9, 4.5))
        mask = np.asarray(analisis["shadow_mask"], dtype=np.float32)
        att = np.asarray(analisis["local_attenuation_map"], dtype=np.float32)

        m0 = np.ma.masked_invalid(mask)
        im0 = axes[0].imshow(m0, cmap=(plt.get_cmap("gray_r").with_extremes(bad="#ba8a8a") if analisis.get("excluded_pixels",0) else "gray_r"), vmin=0, vmax=1, interpolation="nearest")
        axes[0].set_title(f"Cobertura de sombra: {analisis['coverage_pct']:.1f}%")
        axes[0].set_xlabel("X")
        axes[0].set_ylabel("Y")
        cb0 = fig.colorbar(im0, ax=axes[0], ticks=[0, 1], fraction=0.046, pad=0.04)
        cb0.ax.set_yticklabels(["Sol", "Sombra"])

        m1 = np.ma.masked_invalid(att)
        im1 = axes[1].imshow(m1, cmap="viridis", vmin=0, vmax=100, interpolation="nearest")
        axes[1].set_title(f"Atenuación en sombra: {analisis['attenuation_pct']:.1f}%")
        axes[1].set_xlabel("X")
        axes[1].set_ylabel("Y")
        cb1 = fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
        cb1.set_label("Atenuación óptica relativa (%)")

        fig.suptitle(
            f"Método {analisis['algorithm']} · umbral I/Iref={analisis['threshold_ratio']:.3f} · "
            f"transmitancia efectiva={analisis['effective_transmittance']:.3f}",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

        note = tk.Label(
            dlg,
            text=(
                "Cobertura = fracción de píxeles clasificados como sombra.  "
                "Atenuación = reducción fotométrica relativa respecto del área de referencia; "
                "no sustituye una medición radiométrica de irradiancia. Seleccione la misma superficie al sol y a la sombra: copas, asfalto y agua pueden confundirse con sombra."
            ),
            bg=self.palette["background"],
            justify="left",
            wraplength=880,
            font=("Arial", 8),
        )
        note.pack(fill="x", padx=10, pady=(0, 8))

        def _close():
            plt.close(fig)
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close)


    def mostrar_curvas_nivel(self):
        """Genera un mapa interactivo de Tmrt local.

        La escala de color usa exactamente el mínimo y máximo de Tmrt
        finitos del mapa. Por lo tanto, el rango mostrado en la colorbar
        coincide con el rango de valores que se pueden leer al mover el
        mouse sobre la figura.
        """
        if not self.require_project("generar curvas de nivel"):
            return
        if self.shape_selector.area_seleccionada is None:
            return

        # El mapa se voltea para conservar la orientación visual que ya
        # utiliza la aplicación en la curva de nivel.
        temp_ambient, hora, fecha, lat, lon = self._leer_parametros_tmrt()
        try:
            scenario, solar_data = self._resolve_temperature_scenario(temp_ambient, hora, fecha, lat, lon)
        except ValueError as exc:
            messagebox.showerror("Escenario de temperatura", str(exc))
            return
        analisis_foto = self._analizar_seleccion_fotografica()
        self.shadow_photo_analysis = analisis_foto
        self.cobertura_sombra = analisis_foto["coverage_pct"]
        self.atenuacion_sombra = analisis_foto["attenuation_pct"]
        self.porcentaje_sombra = self.cobertura_sombra

        # Mapa binario de cobertura (0=sol, 100=sombra) separado de la
        # transmitancia óptica local. Así la Tmrt espacial usa la intensidad
        # medida dentro de la sombra sin confundirla con área sombreada.
        shadow_mask = np.asarray(analisis_foto["shadow_mask"], dtype=np.float32)
        mapa_sombra = (shadow_mask * np.float32(100.0)).astype(np.float32, copy=False)
        mapa_sombra_volteado = np.flipud(mapa_sombra)
        tau_photo_map = np.flipud(
            np.asarray(analisis_foto["local_transmittance_map"], dtype=np.float32)
        )
        attenuation_photo_map = np.flipud(
            np.asarray(analisis_foto["local_attenuation_map"], dtype=np.float32)
        )

        calculador = scenario.calculator()
        temp_ambient = scenario.air_temp_c
        resultado_mapa = calculador.calculate_tmrt_map(
            temp_ambient,
            mapa_sombra_volteado,
            shadow_type="tree",
            date_value=fecha,
            time_value=hora,
            radiation_override=solar_data["ghi"],
            solar_altitude_override=solar_data["elevation"],
            dni_override=solar_data.get("dni"),
            dhi_override=solar_data.get("dhi"),
            transmittance_map_override=tau_photo_map,
        )
        resultado_mapa["Solar_azimuth"] = solar_data.get("azimuth")
        resultado_mapa["Fuente_solar"] = solar_data.get("source_label", solar_data.get("source", "fallback"))
        resultado_mapa["Fuente_solar_codigo"] = solar_data.get("source_mode", "clear_sky")
        resultado_mapa["Calidad_meteorologica"] = solar_data.get("quality")
        resultado_mapa["Componentes_derivados"] = list(solar_data.get("derived_components", []))
        mapa_temperatura = np.asarray(resultado_mapa["Tmrt_map"], dtype=np.float32)

        # Variables locales que se mostrarán en el hover. Se derivan del
        # MISMO modelo que genera el mapa para evitar discrepancias entre
        # tooltip, colorbar y curva.
        tau_map = np.asarray(tau_photo_map, dtype=np.float32)
        radiacion_global = max(0.0, float(resultado_mapa["Radiacion_Wm2"]))
        radiacion_efectiva = (np.float32(radiacion_global) * tau_map).astype(np.float32, copy=False)
        # Temperatura del aire local estimada bajo sombra. No se deriva de
        # Tmrt: usa la radiación evitada respecto a pleno sol y un modelo
        # empírico acotado (ver shadow_temp.Temperatura).
        aire_local_estimado = calculador.estimate_local_air_temperature_map(
            temp_ambient,
            mapa_sombra_volteado,
            radiacion_global,
            shadow_type="tree",
            cooling_coefficient=float(
                self.settings.get("local_air_tree_coefficient", 0.0025)
            ),
            max_cooling=float(
                self.settings.get("local_air_tree_max_cooling", 2.5)
            ),
            transmittance_map_override=tau_photo_map,
        )
        tmrt_sol_result = calculador.calculate_tmrt(
            temp_ambient, 0.0, shadow_type="tree", date_value=fecha, time_value=hora,
            radiation_override=solar_data["ghi"],
            solar_altitude_override=solar_data["elevation"],
            dni_override=solar_data.get("dni"),
            dhi_override=solar_data.get("dhi"),
        )
        tmrt_sol = float(tmrt_sol_result["Tmrt_sol"])
        delta_tmrt_map = (np.float32(tmrt_sol) - mapa_temperatura).astype(np.float32, copy=False)

        finite = mapa_temperatura[np.isfinite(mapa_temperatura)]
        if finite.size == 0:
            messagebox.showerror("Error", "El mapa Tmrt no contiene valores válidos.")
            return
        tmrt_min = float(np.min(finite))
        tmrt_max = float(np.max(finite))

        from plot_style import (
            CMAP_CURVAS_NIVEL, CMAP_HISTOGRAMA,
            agregar_colorbar_temperatura, anotar_estadisticas,
            anotar_metadatos,
        )

        # Volvemos al FigureCanvasTkAgg real para que Matplotlib reciba
        # motion_notify_event. La versión anterior convertía la figura en
        # PNG y la mostraba dentro de un Label de Tk, lo que hacía
        # imposible consultar el dato bajo el mouse de forma fiable.
        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None

        self.fig2.clf()
        ax = self.fig2.add_subplot(111)
        self.ax2 = ax

        # Para dibujar se usa una malla reducida; los datos científicos y
        # el hover permanecen en resolución completa.
        x_disp, y_disp, mapa_disp, _display_stride = self._contour_display_grid(mapa_temperatura)
        span = tmrt_max - tmrt_min
        if span > 1e-9:
            niveles = np.linspace(tmrt_min, tmrt_max, 21)
            relleno = ax.contourf(
                x_disp, y_disp, mapa_disp,
                levels=niveles,
                cmap=CMAP_CURVAS_NIVEL,
                vmin=tmrt_min,
                vmax=tmrt_max,
                antialiased=True,
            )
            ax.contour(
                x_disp, y_disp, mapa_disp,
                levels=niveles[::2],
                colors="0.35",
                linewidths=0.45,
                alpha=0.55,
            )
            ticks = np.linspace(tmrt_min, tmrt_max, 6)
        else:
            eps = max(0.01, abs(tmrt_min) * 1e-6)
            niveles = np.array([tmrt_min - eps, tmrt_min + eps])
            relleno = ax.contourf(
                x_disp, y_disp, mapa_disp,
                levels=niveles,
                cmap=CMAP_CURVAS_NIVEL,
                vmin=tmrt_min - eps,
                vmax=tmrt_min + eps,
            )
            ticks = np.array([tmrt_min])
        ax.set_xlim(0, mapa_temperatura.shape[1] - 1)
        ax.set_ylim(0, mapa_temperatura.shape[0] - 1)

        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        ax.set_title(
            "Tmrt estimada según distribución local de sombra\n"
            f"T aire {temp_ambient:.1f} °C · rad. {radiacion_global:.0f} W/m² · "
            f"alt. solar {resultado_mapa['Solar_altitude']:.1f}° · "
            f"fuente {resultado_mapa.get('Fuente_solar', 'fallback')} · "
            f"{resultado_mapa.get('Modelo_Tmrt_label', 'Modelo Tmrt')}",
            fontsize=9,
        )
        cbar = agregar_colorbar_temperatura(
            self.fig2, ax, relleno, unidad="°C", etiqueta="Tmrt", ticks=ticks
        )
        if span <= 1e-9:
            cbar.ax.set_title(f"uniforme\n{tmrt_min:.2f} °C", fontsize=7)

        # Indicación explícita del rango que puede aparecer en el hover.
        ax.text(
            0.01, 0.01,
            f"Rango consultable con mouse: {tmrt_min:.2f}–{tmrt_max:.2f} °C",
            transform=ax.transAxes,
            fontsize=7.5,
            va="bottom",
            ha="left",
            bbox=dict(boxstyle="round", fc="white", ec="0.75", alpha=0.82),
        )
        add_solar_indicator_2d(
            ax, resultado_mapa.get("Solar_azimuth"), resultado_mapa.get("Solar_altitude"),
            corner="upper-right",
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.fig2.tight_layout(pad=0.8)
        anotar_metadatos(
            self.fig2,
            f"Mover mouse: valores locales · clic izq.: fijar · clic der.: liberar  ·  "
            f"Generado: {timestamp}",
        )

        # Guardamos exactamente las matrices que corresponden a la figura
        # activa. El hover consulta estas matrices, no vuelve a estimar el
        # valor a partir del color del gráfico.
        self.tmrt_map_scenario = scenario.to_dict()
        self.tmrt_map = mapa_temperatura
        self.tmrt_hover_data = {
            "tmrt": mapa_temperatura,
            "air_temp": float(temp_ambient),
            "local_air_est": np.asarray(aire_local_estimado, dtype=np.float32),
            "shadow": np.asarray(mapa_sombra_volteado, dtype=np.float32),
            "attenuation": np.asarray(attenuation_photo_map, dtype=np.float32),
            "transmittance": np.asarray(tau_photo_map, dtype=np.float32),
            "shadow_coverage_pct": float(analisis_foto["coverage_pct"]),
            "shadow_attenuation_pct": float(analisis_foto["attenuation_pct"]),
            "effective_radiation": np.asarray(radiacion_efectiva, dtype=np.float32),
            "delta_tmrt": np.asarray(delta_tmrt_map, dtype=np.float32),
            "tmrt_sun": float(tmrt_sol),
            "global_radiation": float(radiacion_global),
            "tmrt_min": tmrt_min,
            "tmrt_max": tmrt_max,
        }
        self.curvas_nivel_creadas = True
        self._curve_pinned_pixel = None

        canvas_widget = self.canvas2.get_tk_widget()
        if not canvas_widget.winfo_ismapped():
            canvas_widget.pack(fill="both", expand=True)
        self._setup_hover_tmrt_map(ax, self.canvas2)
        self.canvas2.draw_idle()

        project = self.project_manager.current_project
        if not self.current_analysis_id:
            self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
        artifact_paths = project.layout.element_paths(self.current_analysis_id)

        curve_path = artifact_paths["curve"]
        self.fig2.savefig(curve_path, format="png", dpi=150, bbox_inches="tight", pad_inches=0.1)
        self.curva_img_pil_original = None
        self.last_curve_path = str(curve_path)

        hist_path = artifact_paths["histogram"]
        hist_fig, hist_ax = plt.subplots()
        area_hist = np.asarray(self.shape_selector.area_seleccionada)
        mask_hist = self.shape_selector.area_seleccionada_mask
        if mask_hist is not None and np.asarray(mask_hist).shape == area_hist.shape:
            values = area_hist[np.asarray(mask_hist, dtype=bool)]
        else:
            values = area_hist[np.isfinite(area_hist)]
        if analisis_foto.get('exclusion_mask') is not None:
            values=area_hist[np.isfinite(analisis_foto['shadow_mask'])]
        counts, bins, patches = hist_ax.hist(values, bins=50, alpha=0.95)
        cmap = plt.get_cmap(CMAP_HISTOGRAMA)
        max_count = max(counts) if len(counts) else 1
        for c, patch in zip(counts, patches):
            patch.set_facecolor(cmap(c / max_count if max_count else 0))
        hist_ax.set_xlabel("Nivel de gris")
        hist_ax.set_ylabel("Frecuencia (cantidad de píxeles)")
        hist_ax.set_title(f"Histograma — {self.current_image_stem}")
        anotar_estadisticas(hist_ax, values)
        hist_fig.tight_layout()
        anotar_metadatos(hist_fig, f"Generado: {timestamp}")
        hist_fig.savefig(hist_path, dpi=150)
        plt.close(hist_fig)

        self.last_histogram_path = str(hist_path)
        captured=self._registrar_histograma_en_carrusel()

        excel_path = artifact_paths["matrix"]
        pd.DataFrame(self.shape_selector.area_seleccionada).to_excel(excel_path, index=False)
        self.last_matrix_path = str(excel_path)
        if captured is not None:self.photo_exclusions_pending=False
        if hasattr(self,'photo_exclusion_button'):self.photo_exclusion_button.config(state=tk.NORMAL if captured is not None else tk.DISABLED)
        self.mark_dirty()


    def _setup_hover_tmrt_map(self, ax, canvas):
        """Activa lectura local del mapa Tmrt bajo el mouse.

        El cuadro muestra únicamente las variables locales útiles:
        Tmrt, temperatura del aire local estimada, clasificación sombra/sol,
        atenuación óptica local y radiación efectiva. La anotación cambia de
        cuadrante según la posición del cursor para mantenerse dentro del
        área de datos y no invadir los ejes.

        Clic izquierdo fija el punto; clic derecho lo libera.
        """
        if self._curve_hover_canvas is not None:
            if self._curve_hover_cid is not None:
                try:
                    self._curve_hover_canvas.mpl_disconnect(self._curve_hover_cid)
                except Exception:
                    pass
            if self._curve_click_cid is not None:
                try:
                    self._curve_hover_canvas.mpl_disconnect(self._curve_click_cid)
                except Exception:
                    pass

        self._curve_hover_canvas = canvas
        self._curve_pinned_pixel = None

        annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(0.02, 0.98),
            textcoords="axes fraction",
            fontsize=8,
            ha="left",
            va="bottom",
            bbox=dict(boxstyle="round", fc="white", ec="0.35", alpha=0.94),
            arrowprops=dict(arrowstyle="->", color="0.35", lw=0.7),
            zorder=25,
        )
        annotation.set_visible(False)
        self._curve_hover_annotation = annotation

        marker, = ax.plot(
            [], [],
            marker="o", markersize=4.5,
            markerfacecolor="white", markeredgecolor="black",
            linestyle="none", zorder=20,
        )
        marker.set_visible(False)

        def _valor_texto(x, y):
            data = self.tmrt_hover_data
            if not data:
                return None
            tmrt = data["tmrt"]
            if not (0 <= y < tmrt.shape[0] and 0 <= x < tmrt.shape[1]):
                return None
            value = float(tmrt[y, x])
            if not np.isfinite(value):
                return None
            sombra = float(data["shadow"][y, x])
            atenuacion = float(data["attenuation"][y, x])
            rad_eff = float(data["effective_radiation"][y, x])
            aire_local = float(data["local_air_est"][y, x])
            estado = "Sombra" if sombra >= 50.0 else "Sol"
            return (
                f"Tmrt local: {value:.2f} °C\n"
                f"T aire local estimada: {aire_local:.2f} °C\n"
                f"Clasificación: {estado}\n"
                f"Atenuación local: {atenuacion:.1f} %\n"
                f"Radiación efectiva: {rad_eff:.0f} W/m²"
            )

        def _posicionar_dentro_del_mapa(x, y):
            """Mantiene el tooltip completamente dentro del área del mapa.

            El texto usa coordenadas relativas a los ejes (0..1), no un
            desplazamiento en píxeles. Se ubica en el cuadrante opuesto al
            cursor; así la caja nunca invade ticks/etiquetas de los ejes y
            además deja visible la zona que se está inspeccionando.
            """
            data = self.tmrt_hover_data or {}
            tmrt = data.get("tmrt")
            if tmrt is None:
                return
            h, w = tmrt.shape[:2]

            if x < (w - 1) / 2.0:
                tx = 0.98
                annotation.set_ha("right")
            else:
                tx = 0.02
                annotation.set_ha("left")

            if y < (h - 1) / 2.0:
                ty = 0.98
                annotation.set_va("top")
            else:
                ty = 0.02
                annotation.set_va("bottom")

            annotation.set_position((tx, ty))

        def _mostrar(x, y):
            text = _valor_texto(x, y)
            if text is None:
                annotation.set_visible(False)
                marker.set_visible(False)
                canvas.draw_idle()
                return False
            annotation.xy = (x, y)
            _posicionar_dentro_del_mapa(x, y)
            annotation.set_text(text)
            annotation.set_visible(True)
            marker.set_data([x], [y])
            marker.set_visible(True)
            canvas.draw_idle()
            return True

        def on_move(event):
            # Si hay un punto fijado, mover el mouse no lo reemplaza.
            if self._curve_pinned_pixel is not None:
                _mostrar(*self._curve_pinned_pixel)
                return

            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if annotation.get_visible() or marker.get_visible():
                    annotation.set_visible(False)
                    marker.set_visible(False)
                    canvas.draw_idle()
                return
            x = int(round(event.xdata))
            y = int(round(event.ydata))
            _mostrar(x, y)

        def on_click(event):
            if event.button == 3:
                self._curve_pinned_pixel = None
                if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
                    _mostrar(int(round(event.xdata)), int(round(event.ydata)))
                else:
                    annotation.set_visible(False)
                    marker.set_visible(False)
                    canvas.draw_idle()
                return

            if event.button != 1 or event.inaxes != ax or event.xdata is None or event.ydata is None:
                return
            x = int(round(event.xdata))
            y = int(round(event.ydata))
            if _valor_texto(x, y) is not None:
                self._curve_pinned_pixel = (x, y)
                _mostrar(x, y)

        self._curve_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)
        self._curve_click_cid = canvas.mpl_connect("button_press_event", on_click)


    def _setup_hover_shadow_percent_photo(self, ax, canvas, rgb_img):
        if self._shadow_hover_canvas is not None and self._shadow_hover_cid is not None:
            self._shadow_hover_canvas.mpl_disconnect(self._shadow_hover_cid)
        self._shadow_hover_canvas = canvas
        if self._shadow_hover_annotation is not None and self._shadow_hover_annotation.axes != ax:
            self._shadow_hover_annotation.set_visible(False)
            try:
                self._shadow_hover_annotation.remove()
            except (NotImplementedError, ValueError):
                pass
            self._shadow_hover_annotation = None        
        if self._shadow_hover_annotation is None or self._shadow_hover_annotation.axes != ax:
            self._shadow_hover_annotation = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=8,
                bbox=dict(boxstyle="round", fc="white", alpha=0.7),
            )
            self._shadow_hover_annotation.set_visible(False)

        def on_move(event):
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if self._shadow_hover_annotation.get_visible():
                    self._shadow_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            x, y = int(event.xdata), int(event.ydata)
            if y < 0 or x < 0 or y >= rgb_img.shape[0] or x >= rgb_img.shape[1]:
                if self._shadow_hover_annotation.get_visible():
                    self._shadow_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            pixel = rgb_img[y, x]
            r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            ref_gray = self.ref_gray_mean
            if ref_gray is None or ref_gray <= 0:
                text = "Ref no definida"
            else:
                sombra = (ref_gray - gray) / ref_gray
                sombra = max(0, min(sombra, 1)) * 100
                text = f"Atenuación fotométrica local: {sombra:.2f}%"

            self._shadow_hover_annotation.xy = (event.xdata, event.ydata)
            self._shadow_hover_annotation.set_text(text)
            self._shadow_hover_annotation.set_visible(True)
            canvas.draw_idle()

        self._shadow_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)


