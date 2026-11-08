"""Presentación del análisis de sombra, sin modificar sus estados de cálculo."""
import tkinter as tk
from tkinter import ttk

from image_processor import MATRIX_SIZE_OPTIONS
from ui.panel_chrome import panel_body, panel_button, panel_note, panel_section


_ACTIONS = (
    ("curve_button", "Generá las curvas de nivel para ver el mapa de Tmrt."),
    ("confirm_button", "Confirmá las dos áreas para estimar la sombra."),
    ("area_ref_button", "Marcá una referencia iluminada de la misma superficie."),
    ("area_calc_button", "Delimitá el área donde querés calcular la sombra."),
    ("cargar_imagen_button", "Cargá una imagen para empezar."),
)


def refresh_photo_workflow(app):
    note = getattr(app, "photo_workflow_label", None)
    if note is None:
        return
    next_step = None
    image_loaded = getattr(app, "img_rgb", None) is not None
    for name, text in _ACTIONS:
        button = getattr(app, name)
        available = (image_loaded or name == "cargar_imagen_button") and not button.instate(("disabled",))
        primary = next_step is None and available
        button.configure(style="Primary.TButton" if primary else "TButton")
        if primary:
            next_step = text
    note.configure(text=next_step or _ACTIONS[-1][1])


def setup_photo_panel(app):
    body = panel_body(app.panel_frames[1], "Sombra")
    image = panel_section(body, 1, "1. Imagen")
    app.cargar_imagen_button = panel_button(image, 0, "Cargar imagen", app.cargar_imagen)
    app.photo_workflow_label = panel_note(image, 1)
    selection = panel_section(body, 2, "2. Áreas de análisis")
    app.area_calc_button = panel_button(selection, 0, "Marcar área de cálculo",
                                       app.shape_selector.select_area_calculo, state=tk.DISABLED)
    app.area_ref_button = panel_button(selection, 1, "Marcar referencia iluminada",
                                      app.shape_selector.select_area_referencia, state=tk.DISABLED)
    app.confirm_button = panel_button(selection, 2, "Confirmar y calcular",
                                     app.confirmar_seleccion, state=tk.DISABLED)

    results = panel_section(body, 3, "3. Resultados")
    app.curve_button = panel_button(results, 0, "Generar curva de nivel",
                                   app.mostrar_curvas_nivel, state=tk.DISABLED)
    app.shadow_mask_button = panel_button(results, 1, "Ver máscara sombra / sol",
                                         app.mostrar_mascara_sombra, state=tk.DISABLED)
    app.photo_exclusion_button = panel_button(results, 2, "Excluir materiales",
                                             app.editar_exclusiones_fotograficas, state=tk.DISABLED)
    app.save_dataset_button = panel_button(results, 3, "Respaldar dataset",
                                           app.save_dataset, state=tk.DISABLED)

    options = panel_section(body, 4, "Opciones de análisis")
    app.panel2_advanced_check = ttk.Checkbutton(
        options, text="Resolución avanzada", variable=app.panel2_advanced_mode,
        command=app._toggle_panel2_advanced,
    )
    app.panel2_advanced_check.grid(row=0, column=0, sticky="w", pady=2)
    ttk.Label(options, text="Resolución de matriz (N × N)").grid(
        row=1, column=0, sticky="w", pady=(3, 1))
    app.matrix_size_combo = ttk.Combobox(options, textvariable=app.matriz_size,
                                         values=MATRIX_SIZE_OPTIONS, width=12, state="readonly")
    app.matrix_size_combo.grid(row=2, column=0, sticky="ew")
    panel_note(options, 3, "Predeterminada: 128 × 128. Avanzada: 64 a 640, en pasos de 32.")
    app.shadow_detector_check = ttk.Checkbutton(
        options, text="Detector fotométrico", variable=app.shadow_detector_enabled,
    )
    app.shadow_detector_check.grid(row=4, column=0, sticky="w", pady=2)
    panel_note(options, 5, "Experimental: estima la cobertura en la imagen.")
    app._toggle_panel2_advanced()
    refresh_photo_workflow(app)
