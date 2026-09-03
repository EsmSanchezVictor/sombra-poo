"""Persistencia de un análisis completo del Panel 2.

Desde v17 el carrusel no es un historial de acciones: cada miniatura apunta a
un registro estable en ``analisis/analisis.sqlite3``. Recalcular o guardar el
mismo árbol actualiza ese registro (UPSERT) y seleccionar una miniatura solo
lee/restaura datos; nunca vuelve a ejecutar el análisis.
"""
from __future__ import annotations

import os
import shutil
from tkinter import messagebox

import numpy as np
import pandas as pd

from core.model_registry import SCIENTIFIC_RELEASE, SCIENTIFIC_SCHEMA
from services.analysis_record_store import AnalysisRecordStore


class SnapshotService:
    """Guarda foto, curvas, máscaras, matrices y métricas de cada árbol."""

    def __init__(self, app, project_manager):
        self.app = app
        self.project_manager = project_manager

    # ------------------------------------------------------------------ API
    def save_snapshot(self) -> None:
        """Guardado explícito: actualiza el análisis y luego el proyecto."""
        entry = self.capture_analysis_record(auto=False)
        if entry is not None:
            self.project_manager.save_project()

    def capture_analysis_record(self, *, auto: bool = True) -> dict | None:
        """Crea/actualiza el registro completo asociado a la foto actual.

        ``auto=True`` se usa al terminar de generar la curva de nivel: no
        muestra diálogos ni marca el proyecto como guardado, pero la SQLite se
        escribe inmediatamente. ``auto=False`` corresponde a "Guardar
        snapshot…" y además conserva copias de los Excel auxiliares.
        """
        project = self.project_manager.current_project
        if not project:
            if not auto:
                messagebox.showwarning("Proyecto", "No hay un proyecto abierto para guardar snapshot.")
            return None
        project.ensure_structure()
        store = self.app._get_analysis_store() if hasattr(self.app, "_get_analysis_store") else AnalysisRecordStore(project.root_path)

        analysis_id = getattr(self.app, "current_analysis_id", None)
        if not analysis_id:
            analysis_id = AnalysisRecordStore.new_analysis_id()
            self.app.current_analysis_id = analysis_id
        existing = store.get(analysis_id)
        if existing:
            n = int(existing.get("n") or store.next_n())
            timestamp = existing.get("timestamp") or pd.Timestamp.now().isoformat()
        else:
            n = max(int(getattr(project, "next_n", 1)), int(store.next_n()))
            project.next_n = n + 1
            timestamp = pd.Timestamp.now().isoformat()

        # v19: todos los artefactos derivados del árbol viven juntos bajo
        # analisis/elementos/<analysis_id>/. El número ``n`` queda solo como
        # orden visual/histórico y ya no determina la ubicación en disco.
        paths = project.layout.element_paths(analysis_id)
        curve_path = paths["curve"]
        matrix_path = paths["matrix"]
        reference_path = paths["reference"]
        calc_data_path = paths["calc_data"]
        reference_data_path = paths["reference_data"]
        photo_analysis_path = paths["photo_analysis_data"]
        tmrt_data_path = paths["tmrt_data"]
        histogram_path = paths["histogram"]
        classification_path = paths["shadow_classification"]
        temperature_summary_path = paths["temperature_summary"]
        model_excel = project.layout.model_excel
        edit_excel = project.layout.edit_excel

        # La foto del registro es la FOTO ORIGINAL copiada al proyecto al
        # cargarla, no un screenshot de Matplotlib con ejes/overlays.
        image_path = self._current_source_image(project.root_path)

        self._copy_if_exists(getattr(self.app, "last_curve_path", None), curve_path, silent=auto)
        self._copy_if_exists(getattr(self.app, "last_histogram_path", None), histogram_path, silent=auto)
        self._copy_if_exists(getattr(self.app, "last_shadow_classification_path", None), classification_path, silent=auto)

        selector = getattr(self.app, "shape_selector", None)
        if selector is not None:
            self._save_area_bundle(
                calc_data_path,
                getattr(selector, "area_seleccionada", None),
                getattr(selector, "area_seleccionada_mask", None),
                getattr(selector, "mask_calculo_full", None),
            )
            self._save_area_bundle(
                reference_data_path,
                getattr(selector, "area_referencia", None),
                getattr(selector, "area_referencia_mask", None),
                getattr(selector, "mask_referencia_full", None),
            )
            # Compatibilidad con herramientas históricas que esperan xlsx.
            if getattr(selector, "area_seleccionada", None) is not None:
                pd.DataFrame(selector.area_seleccionada).to_excel(matrix_path, index=False)
                self.app.last_matrix_path = matrix_path
            if getattr(selector, "area_referencia", None) is not None:
                pd.DataFrame(selector.area_referencia).to_excel(reference_path, index=False)
                self.app.last_mask_path = reference_path

        self._save_photo_analysis(photo_analysis_path)
        self._save_tmrt_hover(tmrt_data_path)

        if os.path.exists(curve_path):
            self.app.last_curve_path = curve_path
        if os.path.exists(histogram_path):
            self.app.last_histogram_path = histogram_path
        if os.path.exists(classification_path):
            self.app.last_shadow_classification_path = classification_path

        if not auto:
            self._copy_if_exists(getattr(self.app, "last_model_excel_path", None), model_excel, silent=True)
            self._copy_if_exists(getattr(self.app, "last_edit_excel_path", None), edit_excel, silent=True)

        def _rel(path):
            if not path or not os.path.exists(path):
                return None
            return os.path.relpath(path, project.root_path)

        photo = getattr(self.app, "shadow_photo_analysis", None) or {}
        cobertura = getattr(self.app, "cobertura_sombra", None)
        atenuacion = getattr(self.app, "atenuacion_sombra", None)
        tau_eff = photo.get("effective_transmittance")
        selector = getattr(self.app, "shape_selector", None)

        # El carrusel v17 muestra SOLO registros capaces de restaurarse de
        # forma completa. Si falta alguno de estos componentes no se crea una
        # miniatura engañosa/incompleta.
        complete_ready = all([
            image_path and os.path.exists(image_path),
            os.path.exists(curve_path),
            selector is not None and getattr(selector, "area_seleccionada", None) is not None,
            selector is not None and getattr(selector, "area_referencia", None) is not None,
            cobertura is not None,
            atenuacion is not None,
            tau_eff is not None,
            os.path.exists(calc_data_path),
            os.path.exists(reference_data_path),
            os.path.exists(photo_analysis_path),
            os.path.exists(tmrt_data_path),
        ])
        if not complete_ready:
            if not auto:
                messagebox.showwarning(
                    "Análisis incompleto",
                    "Para guardar este elemento en el carrusel primero deben existir "
                    "la foto, las dos áreas, el análisis de sombra y la curva de nivel.",
                )
            return None
        area_calc_mask = getattr(selector, "mask_calculo_full", None) if selector else None
        area_ref_mask = getattr(selector, "mask_referencia_full", None) if selector else None
        area_calc_px = self._mask_count(area_calc_mask, getattr(selector, "area_seleccionada_mask", None) if selector else None)
        area_ref_px = self._mask_count(area_ref_mask, getattr(selector, "area_referencia_mask", None) if selector else None)

        entry = {
            "analysis_id": analysis_id,
            "n": n,
            "timestamp": timestamp,
            "scientific_release": SCIENTIFIC_RELEASE,
            "scientific_schema": SCIENTIFIC_SCHEMA,
            "label": getattr(self.app, "current_image_stem", None) or (existing or {}).get("label") or f"elemento{n}",
            "image": _rel(image_path),
            "curve": _rel(curve_path),
            "matrix": _rel(matrix_path),
            "reference": _rel(reference_path),
            "calc_data": _rel(calc_data_path),
            "reference_data": _rel(reference_data_path),
            "photo_analysis_data": _rel(photo_analysis_path),
            "tmrt_data": _rel(tmrt_data_path),
            "histogram": _rel(histogram_path),
            "shadow_classification": _rel(classification_path),
            "temperature_summary": _rel(temperature_summary_path),
            "poly_calculo": self._serializar_patch(getattr(selector, "shape_patch_calculo", None) if selector else None),
            "poly_referencia": self._serializar_patch(getattr(selector, "shape_patch_referencia", None) if selector else None),
            "area_calculo_text": self._label_text("lbl_dimensiones_calculo"),
            "area_referencia_text": self._label_text("lbl_dimensiones_referencia"),
            "area_calculo_px": area_calc_px,
            "area_referencia_px": area_ref_px,
            "promedio_gris": self._to_float(getattr(self.app, "ref_gray_mean", None)),
            "promedio_gris_calculo": self._mean_area(
                getattr(selector, "area_seleccionada", None) if selector else None,
                getattr(selector, "area_seleccionada_mask", None) if selector else None,
            ),
            "porcentaje_sombra": self._to_float(cobertura),
            "cobertura_sombra": self._to_float(cobertura),
            "atenuacion_sombra": self._to_float(atenuacion),
            "transmitancia_sombra": self._to_float(photo.get("shadow_transmittance")),
            "transmitancia_efectiva": self._to_float(tau_eff),
            "atenuacion_efectiva": self._to_float(photo.get("effective_attenuation_pct")),
            "umbral_sombra_ratio": self._to_float(photo.get("threshold_ratio")),
            "algoritmo_sombra": photo.get("algorithm"),
            "indice_sombra_legacy": self._to_float(photo.get("legacy_shadow_index_pct")),
            "temp_ambient": None,
            "tmrt_sol": None,
            "tmrt_sombra": None,
            "delta_tmrt": None,
            "modelo_tmrt": None,
            "modelo_superficie": getattr(getattr(self.app, "surface_model_mode", None), "get", lambda: "standard")(),
            "fraccion_suelo_vegetado": float(getattr(self.app, "settings", {}).get("ground_vegetation_fraction", 0.50)),
            "disponibilidad_hidrica_suelo": float(getattr(self.app, "settings", {}).get("vegetation_water_availability", 0.75)),
            "disponibilidad_hidrica_copa": float(getattr(self.app, "settings", {}).get("canopy_water_availability", 0.75)),
            "fuente_radiativa": getattr(getattr(self.app, "radiation_source_mode", None), "get", lambda: "clear_sky")(),
            "complete": True,
        }

        met = getattr(self.app, "last_meteorology_data", None) or {}
        if met:
            entry.update({
                "fuente_radiativa_label": met.get("source_label"),
                "calidad_meteorologica": met.get("quality"),
                "ghi_wm2": met.get("ghi"),
                "dni_wm2": met.get("dni"),
                "dhi_wm2": met.get("dhi"),
                "componentes_radiativos_derivados": met.get("derived_components", []),
            })

        tmrt_result = getattr(self.app, "tmrt_result", None)
        if tmrt_result:
            entry["tmrt_sol"] = tmrt_result.get("Tmrt_sol")
            entry["tmrt_sombra"] = tmrt_result.get("Tmrt_sombra")
            entry["delta_tmrt"] = tmrt_result.get("Delta_Tmrt")
            entry["modelo_tmrt"] = tmrt_result.get("Modelo_Tmrt_label", tmrt_result.get("Modelo_Tmrt"))
            unc = tmrt_result.get("Incertidumbre_operativa") or {}
            shade_unc = unc.get("tmrt_shade") or {}
            entry["tmrt_sombra_p05"] = shade_unc.get("p05")
            entry["tmrt_sombra_p95"] = shade_unc.get("p95")
            entry["incertidumbre_metodo"] = unc.get("method")
            entry["incertidumbre_supuestos"] = unc.get("assumptions")
            entry["incertidumbre_sensibilidad"] = (unc.get("sensitivity") or [])[:4]

        if met.get("source_mode") == "observed_series" and met.get("ta_c") is not None:
            entry["temp_ambient"] = float(met["ta_c"])
        elif hasattr(self.app, "entry_temp"):
            try:
                entry["temp_ambient"] = float(self.app.entry_temp.get().replace("\ufeff", "").strip())
            except (ValueError, AttributeError):
                pass

        saved = store.upsert(entry, complete=True)
        self.app.snapshots = store.list_entries(complete_only=True)
        if hasattr(self.app, "poblar_lista_snapshots"):
            self.app.poblar_lista_snapshots(selected_analysis_id=analysis_id)
        return saved

    # ------------------------------------------------------------- artefactos
    def _current_source_image(self, project_root: str) -> str | None:
        candidates = [
            getattr(self.app, "current_image_path", None),
            getattr(self.app, "last_image_path", None),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                # Si ya está dentro del proyecto no se duplica.
                return os.path.abspath(path)
        return None

    def _save_area_bundle(self, path, values, valid_mask, full_mask) -> None:
        if values is None:
            return
        arr = np.asarray(values)
        vm = np.asarray(valid_mask, dtype=bool) if valid_mask is not None and np.asarray(valid_mask).shape == arr.shape else np.ones(arr.shape, dtype=bool)
        fm = np.asarray(full_mask, dtype=bool) if full_mask is not None else np.empty((0, 0), dtype=bool)
        np.savez_compressed(path, values=arr, valid_mask=vm, full_mask=fm)

    def _save_photo_analysis(self, path) -> None:
        analysis = getattr(self.app, "shadow_photo_analysis", None) or {}
        arrays = {}
        for key in ("shadow_mask", "local_transmittance_map", "local_attenuation_map", "ratio_map"):
            value = analysis.get(key)
            if value is not None:
                arr = np.asarray(value)
                arrays[key] = arr.astype(np.float32, copy=False) if np.issubdtype(arr.dtype, np.floating) else arr
        if arrays:
            np.savez_compressed(path, **arrays)

    def _save_tmrt_hover(self, path) -> None:
        data = getattr(self.app, "tmrt_hover_data", None) or {}
        arrays = {}
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                arrays[key] = value.astype(np.float32, copy=False) if np.issubdtype(value.dtype, np.floating) else value
            elif isinstance(value, (int, float, np.number)):
                arrays[key] = np.asarray(value)
        if arrays:
            np.savez_compressed(path, **arrays)

    def _copy_if_exists(self, source: str | None, target: str, *, silent=True) -> None:
        if not source or not os.path.exists(source):
            return
        if os.path.abspath(source) == os.path.abspath(target):
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)

    # --------------------------------------------------------------- métricas
    @staticmethod
    def _to_float(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _label_text(self, name: str) -> str | None:
        label = getattr(self.app, name, None)
        try:
            return label.cget("text") if label is not None else None
        except Exception:
            return None

    @staticmethod
    def _mask_count(full_mask, crop_mask) -> int | None:
        if full_mask is not None and np.asarray(full_mask).size:
            return int(np.count_nonzero(np.asarray(full_mask, dtype=bool)))
        if crop_mask is not None and np.asarray(crop_mask).size:
            return int(np.count_nonzero(np.asarray(crop_mask, dtype=bool)))
        return None

    @staticmethod
    def _mean_area(values, valid_mask) -> float | None:
        if values is None:
            return None
        arr = np.asarray(values, dtype=float)
        if valid_mask is not None and np.asarray(valid_mask).shape == arr.shape:
            vals = arr[np.asarray(valid_mask, dtype=bool)]
        else:
            vals = arr[np.isfinite(arr)]
        vals = vals[np.isfinite(vals)]
        return float(np.mean(vals)) if vals.size else None

    def _serializar_patch(self, patch) -> dict | None:
        if patch is None:
            return None
        import matplotlib.patches as mpatches
        if isinstance(patch, mpatches.Polygon):
            return {"tipo": "poligono", "puntos": [list(map(float, p)) for p in patch.get_xy()]}
        if isinstance(patch, mpatches.Rectangle):
            x, y = patch.get_xy()
            return {"tipo": "rectangulo", "puntos": [float(x), float(y), float(patch.get_width()), float(patch.get_height())]}
        if isinstance(patch, mpatches.Circle):
            cx, cy = patch.center
            return {"tipo": "circulo", "puntos": [float(cx), float(cy), float(patch.radius)]}
        return None
