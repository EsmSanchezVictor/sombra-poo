"""Presentación del modo Edición: herramientas, parámetros y vista inicial."""
import tkinter as tk
from tkinter import ttk

import diseno as design
import modelo_con_excel as modelo
from ui.theme import PALETA
from ui.panel_chrome import panel_body, panel_section


def setup_editing_panel(app):
    body = panel_body(app.panel_frames[2], "Edición de escena")
    scene = panel_section(body, 1, "Herramientas de escena")

    def edit_tool(mode):
        app._run_with_project("editar la escena", lambda: design.establecer_modo(mode, app))

    for row, (label, mode) in enumerate((
        ("Añadir árbol", "arbol"), ("Añadir estructura", "estructura"), ("Seleccionar", None),
    )):
        ttk.Button(scene, text=label, command=lambda mode=mode: edit_tool(mode)).grid(
            row=row, column=0, sticky="ew", pady=2)

    def draw():
        app._run_with_project("generar el gráfico de edición", lambda: app.actualizar_grafico_diseno(app.frame7))

    views = panel_section(body, 2, "Visualización")
    ttk.Button(views, text="Generar plano 2D", command=draw, style="Primary.TButton").grid(
        row=0, column=0, sticky="ew", pady=2)
    ttk.Button(views, text="Generar vista 3D", command=app.mostrar_vista_3d_diseno).grid(
        row=1, column=0, sticky="ew", pady=2)

    files = panel_section(body, 3, "Archivos de escena")
    ttk.Button(files, text="Abrir Excel", command=app.abrir_excel_edicion).grid(
        row=0, column=0, sticky="ew", pady=2)

    def save_excel():
        app._run_with_project("respaldar el archivo de edición", lambda: design.guardar(
            app.vars, app, filepath=app.project_manager.current_project.layout.edit_excel))

    ttk.Button(files, text="Respaldar Excel", command=save_excel).grid(
        row=1, column=0, sticky="ew", pady=2)

    settings = panel_section(body, 4, "Configuración")
    for row, (label, value) in enumerate((("Modo simple", "simple"), ("Modo avanzado", "advanced"))):
        ttk.Radiobutton(settings, text=label, variable=app.modo_edicion, value=value,
                        command=app._toggle_edicion_mode).grid(row=row, column=0, sticky="w", pady=1)

    # Los dos paneles comparten la misma celda. Conservan las variables y
    # el cambio de modo existentes; el scroll sigue perteneciendo al lateral.
    simple = app.simple_edit_frame = ttk.Frame(body)
    advanced = app.advanced_edit_frame = ttk.Frame(body)
    for frame in (simple, advanced):
        frame.grid(row=5, column=0, sticky="ew", pady=(0, 4))
        frame.columnconfigure(1, weight=1)

    def note(parent, text, row):
        tk.Label(parent, text=text, fg=PALETA["texto_suave"], anchor="w",
                 justify="left", wraplength=186).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(3, 4))

    ttk.Label(simple, text="Ubicación del proyecto", style="DialogSection.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
    app.edit_location_label = tk.Label(simple, text="Sin proyecto", anchor="w",
                                       justify="left", wraplength=186)
    app.edit_location_label.grid(row=1, column=0, columnspan=2, sticky="ew")
    app.edit_latlon_label = tk.Label(simple, fg=PALETA["texto_suave"], anchor="w",
                                    justify="left", wraplength=186)
    app.edit_latlon_label.grid(row=2, column=0, columnspan=2, sticky="ew")

    ttk.Label(advanced, text="Viento").grid(row=0, column=0, sticky="w", padx=(0, 6))
    ttk.Combobox(advanced, textvariable=app.vars["viento"], width=12,
                 values=["nulo", "moderado", "fuerte"], state="normal").grid(
        row=0, column=1, sticky="ew", pady=2)
    note(advanced, "Categoría o m/s: nulo ≈ 0,5 · moderado ≈ 4 · fuerte ≈ 10.", 1)
    ttk.Label(advanced, text="Nubosidad").grid(row=2, column=0, sticky="w", padx=(0, 6))
    ttk.Combobox(advanced, textvariable=app.vars["nubosidad"], width=12,
                 values=["Despejado", "Parcial", "Nublado"], state="readonly").grid(
        row=2, column=1, sticky="ew", pady=2)

    ttk.Label(advanced, text="Modelo de superficie", style="DialogSection.TLabel").grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(9, 3))
    for row, (label, value) in enumerate((
        ("Estándar", "standard"), ("Avanzado seco", "advanced"),
        ("Vegetación + ET", "advanced_vegetation"),
    ), start=4):
        ttk.Radiobutton(advanced, text=label, variable=app.surface_model_mode, value=value).grid(
            row=row, column=0, columnspan=2, sticky="w")
    note(advanced, "Humedad y nubosidad intervienen plenamente en los balances avanzados; Estándar conserva el modelo histórico.", 7)

    ttk.Label(advanced, text="Configuraciones rápidas", style="DialogSection.TLabel").grid(
        row=8, column=0, columnspan=2, sticky="w", pady=(7, 3))
    presets = ttk.Frame(advanced)
    presets.grid(row=9, column=0, columnspan=2, sticky="ew")
    presets.columnconfigure((0, 1), weight=1, uniform="preset")
    for idx, (label, preset) in enumerate((
        ("Verano", "verano"), ("Invierno", "invierno"), ("Soleado", "soleado"), ("Nublado", "nublado"),
    )):
        ttk.Button(presets, text=label, command=lambda p=preset: modelo.cargar_preset(p, app.vars)).grid(
            row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=2)
    note(advanced, "Verano e Invierno ajustan la fecha al hemisferio. Soleado y Nublado ajustan radiación y nubosidad.", 10)

    controls = ttk.Frame(advanced)
    controls.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    for texto, var, fila, rango, es_fecha in app.controles:
        app.crear_control(controls, texto, var, fila, rango, es_fecha)
    app._toggle_edicion_mode()


def show_empty_editing_view(parent, *, title, description):
    """Guía inicial que el renderer reemplaza por el plano o la escena."""
    parent.configure(bg=PALETA["background"])
    card = tk.Frame(parent, bg=PALETA["panel"], padx=24, pady=18, highlightthickness=1,
                    highlightbackground=PALETA["border"])
    card.pack(expand=True, padx=16, pady=16)
    ttk.Label(card, text=title, style="Heading.TLabel").pack(pady=(0, 6))
    ttk.Label(card, text=description, style="Muted.TLabel", justify="center", wraplength=325).pack()


def show_empty_3d_view(parent):
    show_empty_editing_view(
        parent, title="Vista 3D de la escena",
        description="Elegí Generar vista 3D en el panel lateral para recorrer el diseño.",
    )
