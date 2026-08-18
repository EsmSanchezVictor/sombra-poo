"""Servicio para guardar snapshots del flujo de proyecto."""

from __future__ import annotations

import os
import shutil
from tkinter import messagebox

import pandas as pd


class SnapshotService:
    """Guarda imágenes, curvas y matrices asociadas a un proyecto."""

    def __init__(self, app, project_manager):
        self.app = app
        self.project_manager = project_manager

    def save_snapshot(self) -> None:
        """Guarda los artefactos del último cálculo en la estructura del proyecto."""
        project = self.project_manager.current_project
        if not project:
            messagebox.showwarning("Proyecto", "No hay un proyecto abierto para guardar snapshot.")
            return
        project.ensure_structure()
        n = project.allocate_n()

        # Definir rutas destino
        img_path = os.path.join(project.root_path, "imagenes", f"elemento{n}.png")
        curve_path = os.path.join(project.root_path, "curvas", f"Celemento{n}.png")
        matrix_path = os.path.join(project.root_path, "matrices", f"MAelemento{n}.xlsx")
        mask_path = os.path.join(project.root_path, "mascaras", f"Melemento{n}.xlsx")
        model_excel = os.path.join(project.root_path, "excels", "modelo.xlsx")
        edit_excel = os.path.join(project.root_path, "excels", "edicion.xlsx")
        histogram_path = os.path.join(project.root_path, "resultados", "histogramas", f"helemento{n}.png")

        # Guardar figuras disponibles
        if getattr(self.app, "fig1", None) is not None:
            self.app.fig1.savefig(img_path, dpi=150, bbox_inches="tight")
            self.app.last_image_path = img_path
        # CORRECCIÓN: mostrar_curvas_nivel() ya no dibuja el contorno en
        # self.ax2/self.fig2 (esos quedaron como el lienzo vacío inicial
        # del panel) — ahora genera su propia figura local con el mapa de
        # temperatura calculado y la guarda directamente en
        # self.last_curve_path. El chequeo de self.app.fig2 de acá nunca
        # se cumplía, así que la curva nunca se copiaba al historial de
        # snapshots. Se copia desde last_curve_path en su lugar.
        self._copy_if_exists(getattr(self.app, "last_curve_path", None), curve_path, "curva de nivel")
        if os.path.exists(curve_path):
            self.app.last_curve_path = curve_path

        # Guardar matrices si están presentes en la selección
        if getattr(self.app, "shape_selector", None) is not None:
            if getattr(self.app.shape_selector, "area_seleccionada", None) is not None:
                pd.DataFrame(self.app.shape_selector.area_seleccionada).to_excel(matrix_path, index=False)
                self.app.last_matrix_path = matrix_path
            if getattr(self.app.shape_selector, "area_referencia", None) is not None:
                pd.DataFrame(self.app.shape_selector.area_referencia).to_excel(mask_path, index=False)
                self.app.last_mask_path = mask_path

        if getattr(self.app, "last_histogram_path", None):
            self._copy_if_exists(self.app.last_histogram_path, histogram_path, "histograma")
            self.app.last_histogram_path = histogram_path
            
        # Copiar artefactos adicionales si existen
        self._copy_if_exists(self.app.last_model_excel_path, model_excel, "excel modelo")
        self._copy_if_exists(self.app.last_edit_excel_path, edit_excel, "excel edición")

        # NUEVO: registrar este snapshot en el historial del proyecto,
        # con rutas RELATIVAS a project.root_path (para que el proyecto
        # se pueda mover/copiar sin romper el historial) y los resultados
        # calculados en ese momento (% sombra, Tmrt sol/sombra/delta,
        # temperatura ambiente usada). Esto es lo que permite listar
        # todos los elementos analizados y volver a cargar cualquiera
        # con un click, en vez de solo el último.
        def _rel(path):
            if not path or not os.path.exists(path):
                return None
            return os.path.relpath(path, project.root_path)

        entry = {
            "n": n,
            "timestamp": pd.Timestamp.now().isoformat(),
            "label": getattr(self.app, "current_image_stem", None) or f"elemento{n}",
            "image": _rel(img_path),
            "curve": _rel(curve_path),
            "matrix": _rel(matrix_path),
            "reference": _rel(mask_path),
            "histogram": _rel(histogram_path),
            "porcentaje_sombra": getattr(self.app, "porcentaje_sombra", None),
            "poly_calculo": self._serializar_patch(
                getattr(getattr(self.app, "shape_selector", None),
                        "shape_patch_calculo", None)),
            "poly_referencia": self._serializar_patch(
                getattr(getattr(self.app, "shape_selector", None),
                        "shape_patch_referencia", None)),
            "temp_ambient": None,
            "tmrt_sol": None,
            "tmrt_sombra": None,
            "delta_tmrt": None,
        }
        tmrt_result = getattr(self.app, "tmrt_result", None)
        if tmrt_result:
            entry["tmrt_sol"] = tmrt_result.get("Tmrt_sol")
            entry["tmrt_sombra"] = tmrt_result.get("Tmrt_sombra")
            entry["delta_tmrt"] = tmrt_result.get("Delta_Tmrt")
        if hasattr(self.app, "entry_temp"):
            try:
                entry["temp_ambient"] = float(self.app.entry_temp.get().replace('\ufeff', '').strip())
            except (ValueError, AttributeError):
                pass

        if not hasattr(self.app, "snapshots") or self.app.snapshots is None:
            self.app.snapshots = []
        # La entrada provisional del carrusel (creada al generar el
        # histograma, ver _registrar_histograma_en_carrusel) se
        # reemplaza por la formal del mismo elemento al guardar.
        label = entry["label"]
        self.app.snapshots = [
            e for e in self.app.snapshots
            if not (e.get("provisional") and e.get("label") == label)]
        self.app.snapshots.append(entry)
        if hasattr(self.app, "poblar_lista_snapshots"):
            self.app.poblar_lista_snapshots()

        # Guardar el JSON del proyecto actualizado
        self.project_manager.save_project()

    def _copy_if_exists(self, source: str | None, target: str, label: str) -> None:
        """Copia un archivo si existe en origen, mostrando aviso si falta."""
        if not source:
            return
        if not os.path.exists(source):
            messagebox.showwarning("Snapshot", f"No se encontró {label} para guardar.")
            return
        shutil.copy(source, target)

    def _serializar_patch(self, patch) -> dict | None:
        """Serializa el área dibujada sobre la foto (polígono, rectángulo
        o círculo) para poder redibujarla al recargar el snapshot."""
        if patch is None:
            return None
        import matplotlib.patches as mpatches
        if isinstance(patch, mpatches.Polygon):
            return {"tipo": "poligono",
                    "puntos": [list(p) for p in patch.get_xy()]}
        if isinstance(patch, mpatches.Rectangle):
            x, y = patch.get_xy()
            return {"tipo": "rectangulo",
                    "puntos": [float(x), float(y),
                               float(patch.get_width()), float(patch.get_height())]}
        if isinstance(patch, mpatches.Circle):
            cx, cy = patch.center
            return {"tipo": "circulo",
                    "puntos": [float(cx), float(cy), float(patch.radius)]}
        return None