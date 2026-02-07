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
        if getattr(self.app, "fig2", None) is not None:
            self.app.fig2.savefig(curve_path, dpi=150, bbox_inches="tight")
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