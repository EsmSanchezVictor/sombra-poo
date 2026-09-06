"""Constructores de contenido de paneles extraídos de SombraApp
(ui/app_ui.py) — refactor por controladores (README_CAMBIOS.md §6).

Cada función recibe la instancia de la app (`app`) y la usa solo para
leer/escribir estado y atributos de widget; no conocen la clase
SombraApp entera. SombraApp conserva delegados de un renglón con los
mismos nombres para que los call sites internos y externos
(settings_manager.py, app_state.py) no cambien.
"""
from __future__ import annotations

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
    """Panel Temperatura con entrada simple y opciones avanzadas ocultables."""
    panel = app.panel_frames[0]

    tk.Label(
        panel, text="Temperatura", bg=panel.cget("bg"), fg="black",
        font=("Arial", 9, "bold"), anchor="w",
    ).pack(fill="x", padx=10, pady=(2, 3))

    mode_frame = tk.Frame(panel, bg=panel.cget("bg"))
    mode_frame.pack(fill="x", padx=10, pady=(0, 5))
    tk.Radiobutton(
        mode_frame, text="Entrada simple", variable=app.modo_temperatura,
        value="simple", bg=panel.cget("bg"), command=app._toggle_temperatura_mode,
    ).pack(anchor="w")
    tk.Radiobutton(
        mode_frame, text="Entrada avanzada", variable=app.modo_temperatura,
        value="advanced", bg=panel.cget("bg"), command=app._toggle_temperatura_mode,
    ).pack(anchor="w")

    base_frame = tk.Frame(panel, bg=panel.cget("bg"))
    base_frame.pack(fill="x")
    labels = [
        "Temperatura ambiente (°C):", "Hora del día (0-23):",
        "Fecha (YYYY-MM-DD):", "Latitud:", "Longitud:",
    ]
    app.entries = []
    for label_text in labels:
        tk.Label(base_frame, text=label_text, bg=panel.cget("bg"), fg="black").pack(
            fill="x", padx=10, pady=(4, 0)
        )
        entry = tk.Entry(base_frame)
        entry.pack(fill="x", padx=10, pady=(0, 4))
        app.entries.append(entry)
    app.entry_temp, app.entry_time, app.entry_date, app.entry_lat, app.entry_lon = app.entries

    # Es una entrada básica alternativa al porcentaje fotográfico, por eso
    # permanece disponible también en modo simple.
    tk.Label(
        base_frame, text="Porcentaje de sombra manual:",
        bg=panel.cget("bg"), fg="black",
    ).pack(fill="x", padx=10, pady=(7, 3))
    app.entry_porcentaje_manual = tk.Entry(base_frame)
    app.entry_porcentaje_manual.pack(fill="x", padx=10, pady=(0, 3))
    tk.Label(
        base_frame, text="Opcional: reemplaza el % de sombra calculado en el Panel 2.",
        bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
        justify="left", wraplength=210,
    ).pack(fill="x", padx=10, pady=(0, 3))

    app.temperature_advanced_frame = tk.Frame(panel, bg=panel.cget("bg"))
    adv = app.temperature_advanced_frame

    tk.Label(
        adv, text="Fuente radiativa / meteorológica:",
        bg=panel.cget("bg"), fg="black", font=("Arial", 8, "bold"), anchor="w",
    ).pack(fill="x", padx=10, pady=(8, 2))
    source_frame = tk.Frame(adv, bg=panel.cget("bg"))
    source_frame.pack(fill="x", padx=10, pady=(0, 3))
    for text, value in (
        ("Cielo despejado modelado", "clear_sky"),
        ("Medición puntual", "manual_measured"),
        ("Escenario manual", "manual_scenario"),
        ("Serie meteorológica CSV", "observed_series"),
    ):
        tk.Radiobutton(
            source_frame, text=text, variable=app.radiation_source_mode, value=value,
            bg=panel.cget("bg"), anchor="w", justify="left",
            command=app._refresh_meteorology_status,
        ).pack(fill="x", anchor="w")

    tk.Checkbutton(
        adv, text="En cielo despejado: usar pvlib/Ineichen si está disponible",
        variable=app.use_pvlib_engine, bg=panel.cget("bg"), fg="black",
        anchor="w", justify="left", wraplength=210,
        command=app._refresh_meteorology_status,
    ).pack(fill="x", padx=10, pady=(0, 4))

    manual_frame = tk.Frame(adv, bg=panel.cget("bg"))
    manual_frame.pack(fill="x", padx=10, pady=(0, 4))
    tk.Label(manual_frame, text="GHI manual (W/m²)", bg=panel.cget("bg"), font=("Arial", 7)).grid(row=0, column=0, sticky="w")
    tk.Entry(manual_frame, textvariable=app.manual_ghi, width=8).grid(row=0, column=1, sticky="ew", padx=(4, 0))
    tk.Label(manual_frame, text="DNI opcional (Tmrt avanzado)", bg=panel.cget("bg"), font=("Arial", 7)).grid(row=1, column=0, sticky="w")
    tk.Entry(manual_frame, textvariable=app.manual_dni, width=8).grid(row=1, column=1, sticky="ew", padx=(4, 0))
    tk.Label(manual_frame, text="DHI opcional (Tmrt avanzado)", bg=panel.cget("bg"), font=("Arial", 7)).grid(row=2, column=0, sticky="w")
    tk.Entry(manual_frame, textvariable=app.manual_dhi, width=8).grid(row=2, column=1, sticky="ew", padx=(4, 0))
    manual_frame.grid_columnconfigure(1, weight=1)

    tk.Button(
        adv, text="Importar serie meteorológica CSV…",
        command=app.cargar_serie_meteorologica,
    ).pack(fill="x", padx=10, pady=(0, 3))
    app.meteorology_status_label = tk.Label(
        adv, bg=panel.cget("bg"), fg="#555555", font=("Arial", 7),
        anchor="w", justify="left", wraplength=210,
    )
    app.meteorology_status_label.pack(fill="x", padx=10, pady=(0, 6))
    app.radiation_source_mode.trace_add("write", lambda *_: app._refresh_meteorology_status())

    tk.Label(
        adv, text="Modelo Tmrt:", bg=panel.cget("bg"), fg="black",
        font=("Arial", 8, "bold"), anchor="w",
    ).pack(fill="x", padx=10, pady=(2, 0))
    tmrt_mode_frame = tk.Frame(adv, bg=panel.cget("bg"))
    tmrt_mode_frame.pack(fill="x", padx=10, pady=(1, 2))
    tk.Radiobutton(
        tmrt_mode_frame, text="Estándar", variable=app.tmrt_model_mode, value="standard",
        bg=panel.cget("bg"), anchor="w",
    ).pack(anchor="w")
    tk.Radiobutton(
        tmrt_mode_frame, text="Avanzado radiativo", variable=app.tmrt_model_mode, value="advanced",
        bg=panel.cget("bg"), anchor="w",
    ).pack(anchor="w")
    app.tmrt_model_status_label = tk.Label(
        adv, bg=panel.cget("bg"), fg="#555555", font=("Arial", 8), anchor="w",
        justify="left", wraplength=210,
    )
    app.tmrt_model_status_label.pack(fill="x", padx=10, pady=(0, 6))

    def _refresh_tmrt_model_status(*_args):
        if not app.tmrt_model_status_label.winfo_exists():
            return
        texto = (
            "Avanzado · balance radiativo v1"
            if app.tmrt_model_mode.get() == "advanced"
            else "Estándar · empírico calibrable (predeterminado)"
        )
        app.tmrt_model_status_label.config(text=texto)

    app.tmrt_model_mode.trace_add("write", _refresh_tmrt_model_status)
    _refresh_tmrt_model_status()
    app._refresh_meteorology_status()

    app.calculate_temp_button = tk.Button(
        panel, text="Calcular temperatura en sombra",
        command=app.calculate_temperature_in_shade,
    )
    app.calculate_temp_button.pack(fill="x", padx=10, pady=8)
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
    tk.Label(panel, text=texto, anchor="w", font=("Arial", 7), width=18).grid(
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
        entry = tk.Entry(panel, width=12, textvariable=date_text)
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
                         orient=tk.HORIZONTAL, length=1, width=5)
        scale.grid(row=fila, column=1, sticky="ew", padx=(0, 12))


def setup_panel_4(app):
    """Configura el contenido del Panel 4 (Modelo)."""
    panel = app.panel_frames[3]

    # BUG CORREGIDO ("controles del Panel 4 ocultos"): antes acá se
    # creaba un SEGUNDO canvas scrolleable anidado (vía
    # _build_scrollable_content) dentro del frame de contenido que
    # YA vive en un canvas con scrollbar. El canvas anidado quedaba
    # con altura propia chica (solo alcanzaba a mostrar el título y
    # los radiobuttons) y SIN rueda del mouse — los botones y
    # controles de abajo quedaban fuera de vista, "ocultos". Ahora
    # se usan los widgets directamente sobre `panel` (igual que los
    # paneles 1/2), que ya tiene scroll + rueda funcionando.
    for widget in panel.winfo_children():
        widget.destroy()

    panel.grid_columnconfigure(0, weight=1)
    # FIX ("el panel no se ajusta al alto"): sticky="nsew" en simple_frame /
    # advanced_frame (fila 2, más abajo) no alcanza si la fila no tiene
    # weight — grid solo reparte el espacio sobrante entre filas con
    # weight>0. Sin esto, aunque el frame del panel creciera, esa fila
    # se queda con su alto natural y el resto queda vacío abajo. (El otro
    # lado de este fix está en app_ui.py: _crear_panel_desplazable /
    # _on_canvas_resize, que debe sincronizar también el alto del Canvas,
    # no solo el ancho — si no, nunca hay "espacio sobrante" que repartir.)
    panel.grid_rowconfigure(2, weight=1)
    contenido = panel

    diseno_label = tk.Label(contenido, text="Modelo", bg=panel.cget("bg"), fg="black")
    diseno_label.grid(row=0, column=0, sticky="w", pady=(0, 3))

    modo_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    modo_frame.grid(row=1, column=0, sticky="w", pady=2)
    app.simple_mode_radio = tk.Radiobutton(
        modo_frame,
        text="Entrada simple",
        variable=app.modo_modelo,
        value="simple",
        bg=panel.cget("bg"),
        command=app._toggle_modelo_mode,
    )
    app.simple_mode_radio.grid(row=0, column=0, sticky="w")
    app.advanced_mode_radio = tk.Radiobutton(
        modo_frame,
        text="Entrada detallada",
        variable=app.modo_modelo,
        value="advanced",
        bg=panel.cget("bg"),
        command=app._toggle_modelo_mode,
    )
    app.advanced_mode_radio.grid(row=1, column=0, sticky="w", pady=(2, 0))

    app.model_meteorology_status_label = tk.Label(
        contenido, bg=panel.cget("bg"), fg="#555555", font=("Arial", 7),
        anchor="w", justify="left", wraplength=220,
    )
    app.model_meteorology_status_label.grid(row=0, column=0, sticky="e", padx=(70, 12))
    app._refresh_meteorology_status()

    acciones_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    acciones_frame.grid(row=4, column=0, sticky="ew", pady=(6, 0))
    acciones_frame.grid_columnconfigure(0, weight=1)
    app.apply_location_button = tk.Button(
        acciones_frame,
        text="Aplicar ubicación",
        command=lambda: app._apply_location(True),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 7, "bold"),
        state="normal" if app.locations_data else "disabled",
    )
    app.apply_location_button.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=3)
    tk.Button(
        acciones_frame,
        text="Cargar Excel",
        command=app.cargar_excel_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 7, "bold"),
    ).grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=3)
    tk.Button(
        acciones_frame,
        text="Respaldar Excel",
        command=app.guardar_excel_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 7, "bold"),
    ).grid(row=2, column=0, sticky="ew", padx=(0, 12), pady=3)
    tk.Button(
        acciones_frame,
        text="Generar Gráfico",
        command=app.generar_grafico_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 7, "bold"),
    ).grid(row=3, column=0, sticky="ew", padx=(0, 12), pady=3)
    tk.Button(
        acciones_frame,
        text="Vista 3D",
        command=app.mostrar_vista_3d_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 7, "bold"),
    ).grid(row=4, column=0, sticky="ew", padx=(0, 12), pady=3)

    app.simple_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    app.simple_frame.grid(row=2, column=0, sticky="nsew", pady=3)
    app.simple_frame.grid_columnconfigure(0, weight=1)

    if app.locations_error:
        app._locations_error_label = tk.Label(
            app.simple_frame,
            text=app.locations_error,
            fg="red",
            bg=panel.cget("bg"),
            wraplength=max(120, app.simple_frame.winfo_width() - 40),
            justify="left",
        )
        app._locations_error_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=4)
        # Ajuste dinámico: el texto de error se re-envuelve al ancho
        # real del frame (el ancho del panel puede variar) en vez de
        # quedar fijo en 260px y desbordar el contenedor.
        app.simple_frame.bind(
            "<Configure>",
            lambda e: app._locations_error_label.config(
                wraplength=max(120, e.width - 40)),
        )

    tk.Label(app.simple_frame, text="País", bg=panel.cget("bg")).grid(
        row=1, column=0, sticky="w", pady=(2, 0))
    app.country_combo = ttk.Combobox(
        app.simple_frame,
        textvariable=app.simple_country,
        values=app.locations_data["countries"] if app.locations_data else [],
        state="readonly" if app.locations_data else "disabled",
    )
    app.country_combo.grid(row=2, column=0, sticky="ew", pady=(1, 3), padx=5)
    app.country_combo.bind("<<ComboboxSelected>>",
                           lambda _e: app._update_city_options())

    tk.Label(app.simple_frame, text="Ciudad", bg=panel.cget("bg")).grid(
        row=3, column=0, sticky="w", pady=(2, 0))
    app.city_combo = ttk.Combobox(
        app.simple_frame,
        textvariable=app.simple_city,
        values=[],
        state="normal" if app.locations_data else "disabled",
    )
    app.city_combo.grid(row=4, column=0, sticky="ew", pady=(1, 3), padx=5)
    app.city_combo.bind("<<ComboboxSelected>>",
                        lambda _e: app._apply_location(False))
    app.city_combo.bind("<KeyRelease>", app._filter_city_options)

    tk.Label(app.simple_frame, text="Nubosidad", bg=panel.cget("bg")).grid(
        row=5, column=0, sticky="w", pady=(2, 0))
    ttk.Combobox(
        app.simple_frame,
        textvariable=app.simple_cloudiness,
        values=["Despejado", "Parcial", "Nublado"],
        state="readonly",
    ).grid(row=6, column=0, sticky="ew", pady=(1, 3), padx=5)

    tk.Label(app.simple_frame, text="Temperatura aire (°C)", bg=panel.cget("bg")).grid(
        row=7, column=0, sticky="w", pady=(2, 0))
    tk.Entry(app.simple_frame, textvariable=app.simple_temp_air_c).grid(
        row=8, column=0, sticky="ew", pady=(1, 3), padx=(0, 12)
    )
    tk.Label(app.simple_frame, text="Viento", bg=panel.cget("bg")).grid(
        row=9, column=0, sticky="w", pady=(2, 0))
    ttk.Combobox(
        app.simple_frame,
        textvariable=app.vars_modelo["viento"],
        values=["nulo", "moderado", "fuerte"],
    ).grid(row=10, column=0, sticky="ew", pady=(1, 3), padx=5)

    tk.Label(app.simple_frame, text="Humedad relativa (%)", bg=panel.cget("bg")).grid(
        row=11, column=0, sticky="w", pady=(2, 0)
    )
    tk.Entry(app.simple_frame, textvariable=app.simple_rh).grid(
        row=12, column=0, sticky="ew", pady=(1, 3), padx=5
    )

    # Herramientas de confort y calibración (análisis térmico)
    herramientas = tk.Frame(contenido, bg=panel.cget("bg"))
    app.model_tools_frame = herramientas
    herramientas.grid(row=3, column=0, sticky="ew", pady=(2, 3))
    herramientas.grid_columnconfigure(0, weight=1)
    tk.Label(herramientas, text="Herramientas", bg=panel.cget("bg"),
             font=("Arial", 9, "bold"), anchor="w").grid(
        row=0, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
    herramientas_estado = {
        "Calibrar k_factor": app._dialogo_calibrar_k_factor,
        "Confort térmico": app._dialogo_confort,
        "Escenario A/B": app._dialogo_escenario_ab,
        "Validar CSV": app._dialogo_validar_csv,
        "Especies": app._dialogo_especies,
        "Ranking árboles": app._dialogo_ranking_arboles,
    }
    fila_btn = 1
    for texto, comando in herramientas_estado.items():
        tk.Button(herramientas, text=texto, command=comando,
                  anchor="w", bg="#2196F3", fg="white",
                  font=("Arial", 7, "bold")).grid(
            row=fila_btn, column=0, sticky="ew", padx=(0, 12), pady=2)
        fila_btn += 1

    app.advanced_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    app.advanced_frame.grid(row=2, column=0, sticky="nsew", pady=3)
    app.advanced_frame.grid_columnconfigure(1, weight=1)

    tk.Label(app.advanced_frame, text="Viento", bg=panel.cget("bg")).grid(
        row=0, column=0, sticky="w", pady=2)
    ttk.Combobox(
        app.advanced_frame,
        textvariable=app.vars_modelo["viento"],
        values=["nulo", "moderado", "fuerte"],
        state="normal",
    ).grid(row=0, column=1, sticky="ew", pady=2, padx=(8, 5))
    tk.Label(
        app.advanced_frame,
        text="Categoría o m/s: nulo≈0.5 · moderado≈4 · fuerte≈10",
        bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
    ).grid(row=1, column=0, columnspan=2, sticky="w")

    tk.Label(app.advanced_frame, text="Nubosidad", bg=panel.cget("bg")).grid(
        row=2, column=0, sticky="w", pady=2)
    ttk.Combobox(
        app.advanced_frame,
        textvariable=app.vars_modelo["nubosidad"],
        values=["Despejado", "Parcial", "Nublado"],
        state="readonly",
    ).grid(row=2, column=1, sticky="ew", pady=2, padx=(8, 5))

    tk.Label(app.advanced_frame, text="Modelo de superficie", bg=panel.cget("bg")).grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(5, 1))
    surface_frame = tk.Frame(app.advanced_frame, bg=panel.cget("bg"))
    surface_frame.grid(row=4, column=0, columnspan=2, sticky="w")
    for label, value in (
        ("Estándar", "standard"),
        ("Avanzado seco", "advanced"),
        ("Vegetación + ET", "advanced_vegetation"),
    ):
        tk.Radiobutton(
            surface_frame, text=label, variable=app.surface_model_mode, value=value,
            bg=panel.cget("bg"), anchor="w",
        ).pack(anchor="w")
    tk.Label(
        app.advanced_frame,
        text="Humedad y nubosidad intervienen plenamente en los balances avanzados; el modo Estándar conserva el modelo histórico.",
        bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
        justify="left", wraplength=210,
    ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(1, 3))

    tk.Label(app.advanced_frame, text="Configuraciones rápidas", bg=panel.cget("bg")).grid(
        row=6, column=0, columnspan=2, sticky="w", pady=(5, 2)
    )
    preset_frame = tk.Frame(app.advanced_frame, bg=panel.cget("bg"))
    preset_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=(0, 5), pady=(0, 3))
    preset_frame.grid_columnconfigure(0, weight=1)
    preset_frame.grid_columnconfigure(1, weight=1)
    for idx, (label, preset) in enumerate((
        ("Verano", "verano"), ("Invierno", "invierno"),
        ("Soleado", "soleado"), ("Nublado", "nublado"),
    )):
        tk.Button(
            preset_frame, text=label,
            command=lambda p=preset: modelo.cargar_preset(p, app.vars_modelo),
            bg="#4CAF50", fg="white", font=("Arial", 7, "bold"),
        ).grid(row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=2)
    tk.Label(
        app.advanced_frame,
        text="Verano/Invierno adaptan la fecha al hemisferio. Soleado/Nublado ajustan radiación y nubosidad. Con serie observada prevalecen los datos medidos disponibles.",
        bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
        justify="left", wraplength=210,
    ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 3))

    panelin = tk.Frame(app.advanced_frame, bg=panel.cget("bg"))
    panelin.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=(0, 12), pady=3)
    for texto, var, fila, rango, es_fecha in app.controles_modelo:
        crear_control(app, panelin, texto, var, fila, rango, es_fecha)
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
        frame.pack(fill="x", before=app.calculate_temp_button, pady=(0, 2))
    else:
        frame.pack_forget()


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
