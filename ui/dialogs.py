"""Diálogos de herramientas de análisis térmico, extraídos de SombraApp
(ui/app_ui.py) — refactor por controladores (README_CAMBIOS.md §6).

`HerramientasDialogs` recibe la app en el constructor y opera sobre
`self.app.<atributo>`; SombraApp conserva los seis métodos `_dialogo_*`
como bound methods (asignados en __init__) para que menú, ribbon y
Panel 4 no cambien.
"""
from __future__ import annotations
from ui.validation_dialogs import ValidationDialogsMixin
from core.effective_scenario import effective_model

import os
import queue
import shutil
import threading
import time
from datetime import datetime

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.modal_style import prepare_dialog, dialog_container, dialog_header, ask_text

from core import scenario as scenario_tools
from core import thermal_comfort
from core.climate_profile import viento_categoria_a_ms
from core.species import (
    eliminar_especie, guardar_especie, nombres_especies,
    propiedades_especie, validar_especie,
)
from core.scientific_audit import run_scientific_audit, format_audit_text, save_audit_json
from core.validation import (
    evaluar_modelos,
    exportar_reporte_validacion,
    guardar_plantilla_csv,
    k_factor_desde_mediciones,
    leer_csv_mediciones,
    metricas,
)
from shadow_temp import Temperatura
from ui.calibration_dialogs import CalibrationDialogsMixin
from ui.comfort_dialogs import ComfortDialogsMixin
from ui.species_dialogs import SpeciesDialogsMixin


def ask_project_name(root: tk.Tk) -> str | None:
    """Solicita el nombre del proyecto."""
    return ask_text(root, "Nuevo proyecto", "Ingresá el nombre del proyecto:", accept_text="Crear proyecto")


def ask_project_location(root: tk.Tk, locations_data: dict | None) -> dict | None:
    """Solicita la ubicación con el mismo formulario visual que Árbol/Estructura."""
    if not locations_data:
        return None

    result: dict | None = None
    dialog = tk.Toplevel(root)
    dialog.title("Ubicación del proyecto")
    prepare_dialog(dialog, root, modal=True, resizable=False)
    cont = dialog_container(dialog)
    dialog_header(
        cont,
        "Ubicación del proyecto",
        "Seleccioná país y ciudad. Podés filtrar la lista escribiendo parte del nombre.",
    )

    form = ttk.Frame(cont)
    form.pack(fill="x")
    form.columnconfigure(1, weight=1)

    country_var = tk.StringVar(value=locations_data["countries"][0] if locations_data["countries"] else "")
    city_var = tk.StringVar()
    search_var = tk.StringVar()

    ttk.Label(form, text="País:").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
    country_combo = ttk.Combobox(
        form, textvariable=country_var, values=locations_data["countries"], state="readonly", width=32,
    )
    country_combo.grid(row=0, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Ciudad:").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
    city_combo = ttk.Combobox(form, textvariable=city_var, values=[], width=32)
    city_combo.grid(row=1, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Buscar:").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=6)
    search_entry = ttk.Entry(form, textvariable=search_var, width=34)
    search_entry.grid(row=2, column=1, sticky="ew", pady=6)

    def update_cities(*_args):
        cities = locations_data["cities"].get(country_var.get(), [])
        city_combo["values"] = cities
        if cities:
            city_var.set(cities[0])

    def filter_cities(*_args):
        query = search_var.get().lower().strip()
        cities = locations_data["cities"].get(country_var.get(), [])
        filtered = [city for city in cities if query in city.lower()] if query else cities
        city_combo["values"] = filtered
        if filtered:
            city_var.set(filtered[0])

    def on_accept():
        nonlocal result
        location = locations_data["lookup"].get(city_var.get().strip())
        if location:
            result = location
            dialog.destroy()

    country_combo.bind("<<ComboboxSelected>>", lambda _e: update_cities())
    city_combo.bind("<<ComboboxSelected>>", lambda _e: search_var.set(""))
    search_entry.bind("<KeyRelease>", lambda _e: filter_cities())
    update_cities()

    buttons = ttk.Frame(cont)
    buttons.pack(fill="x", pady=(16, 0))
    ttk.Button(buttons, text="Cancelar", command=dialog.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Aceptar", command=on_accept, style="DialogPrimary.TButton").pack(side="right")
    dialog.bind("<Return>", lambda _e: on_accept())
    country_combo.focus_set()
    dialog.wait_window()
    return result


class HerramientasDialogs(ValidationDialogsMixin, CalibrationDialogsMixin, ComfortDialogsMixin, SpeciesDialogsMixin):
    def __init__(self, app):
        self.app = app

    # ---------------------------------------------------------------- calibrador


    # ---------------------------------------------------------------- confort


    # ---------------------------------------------------------------- escenario A/B


    # ---------------------------------------------------------------- validación CSV


    # Métodos históricos conservados como aliases internos para plugins/código
    # que pudiera invocarlos directamente.

    def _dialogo_auditoria_cientifica(self):
        """Ejecuta la auditoría interna de preparación científica v16.

        No sustituye una validación de campo: separa fallas internas,
        advertencias metodológicas y evidencia experimental faltante.
        """
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        report = run_scientific_audit(
            project_root=(project.root_path if project else None),
            settings=getattr(self.app, "settings", {}),
            snapshots=getattr(self.app, "snapshots", []),
            validation_summary=getattr(self.app, "last_validation_summary", None),
        )
        self.app.last_scientific_audit = report.to_dict()
        if project is not None:
            os.makedirs(project.layout.validation_results_dir, exist_ok=True)
            save_audit_json(project.layout.audit_json, report)
            with open(project.layout.audit_txt, "w", encoding="utf-8") as handle:
                handle.write(format_audit_text(report))
            self.app.mark_dirty()

        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(720, 560))
        dlg.title("Auditoría científica y preparación para validación")
        dlg.geometry("820x640")
        dlg.transient(self.app.root)

        counts = report.counts
        tk.Label(
            dlg,
            text=report.readiness,
            font=("Arial", 11, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(
            dlg,
            text=(
                f"Release {report.scientific_release} · "
                f"OK {counts.get('pass', 0)} · advertencias {counts.get('warning', 0)} · "
                f"fallas {counts.get('fail', 0)}"
            ),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        text = tk.Text(dlg, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(dlg, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", pady=(0, 8))
        text.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 8))
        text.insert("1.0", format_audit_text(report))
        text.configure(state="disabled")

        pie = tk.Frame(dlg)
        pie.pack(fill="x", padx=12, pady=(0, 10))

        def export_json():
            if project is None:
                return
            save_audit_json(project.layout.audit_json, report)
            messagebox.showinfo("Auditoría", f"Auditoría actualizada en:\n{project.layout.audit_json}", parent=dlg)

        def export_txt():
            if project is None:
                return
            with open(project.layout.audit_txt, "w", encoding="utf-8") as handle:
                handle.write(format_audit_text(report))
            messagebox.showinfo("Auditoría", f"Auditoría actualizada en:\n{project.layout.audit_txt}", parent=dlg)

        tk.Button(pie, text="Guardar JSON", command=export_json).pack(side="left")
        tk.Button(pie, text="Guardar TXT", command=export_txt).pack(side="left", padx=6)
        tk.Button(pie, text="Cerrar", command=dlg.destroy).pack(side="right")

    # ---------------------------------------------------------------- especies y ranking


