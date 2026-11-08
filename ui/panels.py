"""Constructores de contenido de paneles extraídos de SombraApp
(ui/app_ui.py) — refactor por controladores (README_CAMBIOS.md §6).

Cada función recibe la instancia de la app (`app`) y la usa solo para
leer/escribir estado y atributos de widget; no conocen la clase
SombraApp entera. SombraApp conserva delegados de un renglón con los
mismos nombres para que los call sites internos y externos
(settings_manager.py, app_state.py) no cambien.
"""
from __future__ import annotations
from ui.theme import FONT, PALETA
from ui.panel_chrome import panel_body, panel_button, panel_field, panel_note, panel_section

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox

import modelo_con_excel as modelo
from image_processor import DEFAULT_MATRIX_SIZE


def _build_controles(vars_dict):
    return [
        ("Fecha (AAAA-MM-DD)", vars_dict["dia"], 1, None, True),
        ("Latitud (°)", vars_dict["lat"], 2, [-90, 90], False),
        ("Longitud (°)", vars_dict["lon"], 3, [-180, 180], False),
        ("Hora Local", vars_dict["hora"], 4, [0, 24], False),
        ("Humedad (%)", vars_dict["humedad"], 5, [0, 100], False),
        ("Radiación (W/m²)", vars_dict["I_sol_base"], 6, [0, 1500], False),
        ("Temp. Mín (K)", vars_dict["T_min"], 7, [250, 350], False),
        ("Temp. Máx (K)", vars_dict["T_max"], 8, [250, 350], False),
    ]


def setup_panel_1(app):
    """Temperatura: condiciones del cálculo y meteorología avanzada."""
    body = panel_body(app.panel_frames[0], "Temperatura")
    mode = panel_section(body, 1, "Configuración")
    ttk.Radiobutton(mode, text="Entrada simple", variable=app.modo_temperatura, value="simple",
                    command=app._toggle_temperatura_mode).grid(row=0, column=0, sticky="w", pady=1)
    ttk.Radiobutton(mode, text="Entrada avanzada", variable=app.modo_temperatura, value="advanced",
                    command=app._toggle_temperatura_mode).grid(row=1, column=0, sticky="w", pady=1)

    data = panel_section(body, 2, "Datos de entrada")
    app.entries = [
        panel_field(data, 2 * i, label)
        for i, label in enumerate(("Temperatura del aire (°C)", "Hora del día (0–23)",
                                   "Fecha (AAAA-MM-DD)", "Latitud (°)", "Longitud (°)"))
    ]
    app.entry_temp, app.entry_time, app.entry_date, app.entry_lat, app.entry_lon = app.entries
    app.entry_porcentaje_manual = panel_field(data, 10, "Sombra manual (%)")
    panel_note(data, 12, "Opcional. Reemplaza la cobertura de sombra calculada con la foto.")

    app.temperature_advanced_frame = adv = panel_section(body, 3, "Meteorología y Tmrt")
    ttk.Label(adv, text="Fuente de radiación", style="DialogSection.TLabel").grid(
        row=0, column=0, sticky="w", pady=(2, 4))
    for row, (text, value) in enumerate((
        ("Cielo despejado modelado", "clear_sky"),
        ("Medición puntual", "manual_measured"),
        ("Escenario manual", "manual_scenario"),
        ("Serie meteorológica CSV", "observed_series"),
    ), start=1):
        ttk.Radiobutton(adv, text=text, variable=app.radiation_source_mode, value=value,
                        command=app._refresh_meteorology_status).grid(row=row, column=0, sticky="w", pady=1)
    ttk.Checkbutton(adv, text="Usar pvlib/Ineichen", variable=app.use_pvlib_engine,
                    command=app._refresh_meteorology_status).grid(row=5, column=0, sticky="w", pady=(4, 0))
    panel_note(adv, 6, "Se usa para cielo despejado si está disponible.")
    panel_field(adv, 7, "GHI manual (W/m²)", textvariable=app.manual_ghi)
    panel_field(adv, 9, "DNI opcional (W/m²)", textvariable=app.manual_dni)
    panel_field(adv, 11, "DHI opcional (W/m²)", textvariable=app.manual_dhi)
    panel_note(adv, 13, "DNI y DHI se usan con el modelo Tmrt avanzado.")
    panel_button(adv, 14, "Importar serie CSV…", app.cargar_serie_meteorologica)
    app.meteorology_status_label = panel_note(adv, 15)
    app.radiation_source_mode.trace_add("write", lambda *_: app._refresh_meteorology_status())

    ttk.Label(adv, text="Modelo de Tmrt", style="DialogSection.TLabel").grid(
        row=16, column=0, sticky="w", pady=(7, 3))
    for row, (text, value) in enumerate((("Estándar", "standard"), ("Avanzado radiativo", "advanced")), start=17):
        ttk.Radiobutton(adv, text=text, variable=app.tmrt_model_mode, value=value).grid(
            row=row, column=0, sticky="w", pady=1)
    app.tmrt_model_status_label = panel_note(adv, 19)

    def _refresh_tmrt_model_status(*_args):
        if app.tmrt_model_status_label.winfo_exists():
            app.tmrt_model_status_label.config(text=(
                "Avanzado · balance radiativo v2"
                if app.tmrt_model_mode.get() == "advanced"
                else "Estándar · empírico calibrable (predeterminado)"
            ))

    app.tmrt_model_mode.trace_add("write", _refresh_tmrt_model_status)
    _refresh_tmrt_model_status()
    app._refresh_meteorology_status()
    calc = panel_section(body, 4, "Cálculo")
    app.calculate_temp_button = panel_button(calc, 0, "Calcular en sombra",
                                             app.calculate_temperature_in_shade, style="Primary.TButton")
    _toggle_temperatura_mode(app)


def crear_control(app, panel, texto, var, fila, rango=None, es_fecha=False):
    # Columna del control con peso: el entry/scale se estira hasta
    # el ancho disponible del panel (antes quedaba fijo al tamaño
    # pedido y el panel avanzado desbordaba el contenedor).
    panel.grid_columnconfigure(1, weight=1)
    # FIX ("elementos ajustados al alto de la ventana"): pady=10 acá
    # (20px extra por fila, arriba+abajo) multiplicado por las 9 filas
    # de controles de Modo Avanzado sumaba ~180px solo en separación,
    # antes de contar los botones y "Herramientas" de más abajo — la
    # razón principal por la que había que scrollear tanto para ver
    # todo el panel. pady=3 sigue siendo legible pero deja que
    # bastante más contenido entre en pantalla sin scroll.
    tk.Label(panel, text=texto, anchor="w", font=(FONT, 7), width=18).grid(
        row=fila, column=0, sticky="ew", padx=0, pady=3)
    if es_fecha:
        source_vars = app.vars_modelo if app.vars_modelo.get("dia") is var else app.vars
        iso_value = source_vars.get("_date_iso")
        if hasattr(iso_value, "get"):
            iso_value = iso_value.get()
        try:
            day = max(1, min(int(float(var.get())), 366))
            year = int(source_vars.get("_year", datetime.now().year))
            initial_date = str(iso_value or (datetime(year, 1, 1) + timedelta(days=day - 1)).date().isoformat())
        except Exception:
            initial_date = datetime.now().date().isoformat()
        date_text = tk.StringVar(value=initial_date)
        entry = ttk.Entry(panel, width=12, textvariable=date_text)
        entry.grid(row=fila, column=1, sticky="ew", padx=(0, 12))

        def apply_date(_event=None):
            app.actualizar_dia(date_text.get(), var)

        def sync_from_day(*_args):
            try:
                day_now = max(1, min(int(float(var.get())), 366))
                year_now = int(source_vars.get("_year", datetime.now().year))
                date_text.set((datetime(year_now, 1, 1) + timedelta(days=day_now - 1)).date().isoformat())
            except Exception:
                pass

        entry.bind("<Return>", apply_date)
        entry.bind("<FocusOut>", apply_date)
        try:
            var.trace_add("write", sync_from_day)
        except Exception:
            pass
    elif rango:
        scale = tk.Scale(panel, from_=rango[0], to=rango[1], variable=var,
                         orient=tk.HORIZONTAL, length=1, width=7,
                         bg=PALETA["panel"], fg=PALETA["texto"],
                         troughcolor=PALETA["selected"], activebackground=PALETA["accent"],
                         highlightbackground=PALETA["panel"], highlightcolor=PALETA["focus"])
        scale.grid(row=fila, column=1, sticky="ew", padx=(0, 12))


def setup_panel_4(app):
    """Modelo: modos de entrada, vistas y herramientas de análisis."""
    body = panel_body(app.panel_frames[3], "Modelo")
    modes = panel_section(body, 1, "Configuración")
    app.simple_mode_radio = ttk.Radiobutton(
        modes, text="Entrada simple", variable=app.modo_modelo, value="simple", command=app._toggle_modelo_mode)
    app.simple_mode_radio.grid(row=0, column=0, sticky="w", pady=1)
    app.advanced_mode_radio = ttk.Radiobutton(
        modes, text="Entrada avanzada", variable=app.modo_modelo, value="advanced", command=app._toggle_modelo_mode)
    app.advanced_mode_radio.grid(row=1, column=0, sticky="w", pady=1)
    app.model_meteorology_status_label = panel_note(modes, 2)
    if app.locations_error:
        app._locations_error_label = panel_note(modes, 3, app.locations_error, color=PALETA["peligro"])

    app.apply_location_button = panel_button(
        modes, 4, "Aplicar ubicación", lambda: app._apply_location(True),
        state="normal" if app.locations_data else "disabled")

    views = panel_section(body, 2, "Simulación")
    panel_button(views, 0, "Ejecutar modelo", app.generar_grafico_modelo, style="Primary.TButton")
    panel_button(views, 1, "Generar vista 3D", app.mostrar_vista_3d_modelo)

    app.simple_frame = simple = panel_section(body, 3, "Datos del escenario")
    app.country_combo = panel_field(
        simple, 0, "País", ttk.Combobox, textvariable=app.simple_country,
        values=app.locations_data["countries"] if app.locations_data else (),
        state="readonly" if app.locations_data else "disabled",
    )
    app.country_combo.bind("<<ComboboxSelected>>", lambda _e: app._update_city_options())
    app.city_combo = panel_field(
        simple, 2, "Ciudad", ttk.Combobox, textvariable=app.simple_city, values=(),
        state="normal" if app.locations_data else "disabled",
    )
    app.city_combo.bind("<<ComboboxSelected>>", lambda _e: app._apply_location(False))
    app.city_combo.bind("<KeyRelease>", app._filter_city_options)
    panel_field(simple, 4, "Nubosidad", ttk.Combobox, textvariable=app.simple_cloudiness,
                values=["Despejado", "Parcial", "Nublado"], state="readonly")
    panel_field(simple, 6, "Temperatura del aire (°C)", textvariable=app.simple_temp_air_c)
    panel_field(simple, 8, "Viento", ttk.Combobox, textvariable=app.vars_modelo["viento"],
                values=["nulo", "moderado", "fuerte"])
    panel_field(simple, 10, "Humedad relativa (%)", textvariable=app.simple_rh)

    app.advanced_frame = advanced = panel_section(body, 3, "Parámetros avanzados")
    panel_field(advanced, 0, "Viento", ttk.Combobox, textvariable=app.vars_modelo["viento"],
                values=["nulo", "moderado", "fuerte"], state="normal")
    panel_note(advanced, 2, "Categoría o m/s: nulo ≈ 0,5 · moderado ≈ 4 · fuerte ≈ 10.")
    panel_field(advanced, 3, "Nubosidad", ttk.Combobox, textvariable=app.vars_modelo["nubosidad"],
                values=["Despejado", "Parcial", "Nublado"], state="readonly")

    ttk.Label(advanced, text="Modelo de superficie", style="DialogSection.TLabel").grid(
        row=5, column=0, sticky="w", pady=(7, 3))
    for row, (label, value) in enumerate((
        ("Estándar", "standard"), ("Avanzado seco", "advanced"), ("Vegetación + ET", "advanced_vegetation"),
    ), start=6):
        ttk.Radiobutton(advanced, text=label, variable=app.surface_model_mode, value=value).grid(
            row=row, column=0, sticky="w", pady=1)
    panel_note(advanced, 9, "Humedad y nubosidad intervienen plenamente en los balances avanzados. Estándar conserva el modelo histórico.")

    ttk.Label(advanced, text="Configuraciones rápidas", style="DialogSection.TLabel").grid(
        row=10, column=0, sticky="w", pady=(7, 3))
    preset_frame = ttk.Frame(advanced)
    preset_frame.grid(row=11, column=0, sticky="ew")
    preset_frame.columnconfigure((0, 1), weight=1, uniform="preset")
    for idx, (label, preset) in enumerate((
        ("Verano", "verano"), ("Invierno", "invierno"),
        ("Soleado", "soleado"), ("Nublado", "nublado"),
    )):
        ttk.Button(preset_frame, text=label, command=lambda p=preset: modelo.cargar_preset(p, app.vars_modelo)).grid(
            row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=2)
    panel_note(advanced, 12, "Las estaciones ajustan la fecha al hemisferio. Si hay una serie observada, prevalecen los datos medidos disponibles.")
    controls = ttk.Frame(advanced)
    controls.grid(row=13, column=0, sticky="ew", pady=(4, 0))
    for texto, var, fila, rango, es_fecha in app.controles_modelo:
        crear_control(app, controls, texto, var, fila, rango, es_fecha)

    files = panel_section(body, 4, "Archivos del modelo")
    panel_button(files, 0, "Abrir Excel", app.cargar_excel_modelo)
    panel_button(files, 1, "Respaldar Excel", app.guardar_excel_modelo)

    herramientas = panel_section(body, 5, "Herramientas de análisis")
    app.model_tools_frame = herramientas
    for row, (texto, comando) in enumerate((
        ("Calibrar k_factor", app._dialogo_calibrar_k_factor),
        ("Confort térmico", app._dialogo_confort),
        ("Escenario A/B", app._dialogo_escenario_ab),
        ("Validar CSV", app._dialogo_validar_csv),
        ("Especies", app._dialogo_especies),
        ("Ranking de árboles", app._dialogo_ranking_arboles),
    )):
        panel_button(herramientas, row, texto, comando)

    app.vars_modelo["graph_frame"] = app.frame11
    _update_city_options(app)
    if app.locations_error:
        app.modo_modelo.set("advanced")
        app.simple_mode_radio.config(state="disabled")
    _toggle_modelo_mode(app)


def _toggle_temperatura_mode(app):
    frame = getattr(app, "temperature_advanced_frame", None)
    if frame is None or not frame.winfo_exists():
        return
    if getattr(app, "modo_temperatura", None) is not None and app.modo_temperatura.get() == "advanced":
        frame.grid()
    else:
        frame.grid_remove()


def _toggle_modelo_mode(app):
    tools = getattr(app, "model_tools_frame", None)
    if app.modo_modelo.get() == "simple" and not app.locations_error:
        app.advanced_frame.grid_remove()
        app.simple_frame.grid()
        if tools is not None and tools.winfo_exists():
            tools.grid_remove()
    else:
        app.simple_frame.grid_remove()
        app.advanced_frame.grid()
        if tools is not None and tools.winfo_exists():
            tools.grid()
    try:
        app._refresh_meteorology_status()
    except Exception:
        pass


def _toggle_edicion_mode(app):
    if app.modo_edicion.get() == "simple":
        app.advanced_edit_frame.grid_remove()
        app.simple_edit_frame.grid()
    else:
        app.simple_edit_frame.grid_remove()
        app.advanced_edit_frame.grid()


def _toggle_panel2_advanced(app):
    if app.panel2_advanced_mode.get():
        app.matrix_size_combo.config(state="readonly")
    else:
        app.matriz_size.set(DEFAULT_MATRIX_SIZE)
        app.matrix_size_combo.config(state="disabled")


def _update_city_options(app):
    if not app.locations_data:
        return
    country = app.simple_country.get()
    cities = app.locations_data["cities"].get(country, [])
    app.city_combo["values"] = cities
    if cities and app.simple_city.get() not in cities:
        app.simple_city.set(cities[0])


def _filter_city_options(app, event):
    if not app.locations_data:
        return
    country = app.simple_country.get()
    query = app.simple_city.get().lower().strip()
    cities = app.locations_data["cities"].get(country, [])
    if query:
        filtered = [city for city in cities if query in city.lower()]
    else:
        filtered = cities
    app.city_combo["values"] = filtered


def _apply_location(app, show_message):
    if not app.locations_data:
        return
    city_label = app.simple_city.get().strip()
    location = app.locations_data["lookup"].get(city_label)
    if not location:
        if show_message:
            messagebox.showwarning("Ubicación", "Seleccione una ciudad válida.")
        return
    app.vars_modelo["lat"].set(location["lat"])
    app.vars_modelo["lon"].set(location["lon"])
    tz = location.get("tz") or "America/Argentina/Buenos_Aires"
    if "timezone" in app.vars_modelo and hasattr(app.vars_modelo["timezone"], "set"):
        app.vars_modelo["timezone"].set(tz)
    if "timezone" in app.vars and hasattr(app.vars["timezone"], "set"):
        app.vars["timezone"].set(tz)
    app.current_location = dict(location)
    try:
        app.solar_engine.set_timezone(tz)
    except Exception:
        pass
    app.vars_modelo["_update_required"] = True
    if show_message:
        messagebox.showinfo("Ubicación aplicada",
                            f"Lat/Lon: {location['lat']}, {location['lon']}")
