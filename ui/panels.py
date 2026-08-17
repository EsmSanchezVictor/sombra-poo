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
from tkinter import ttk, messagebox

import modelo_con_excel as modelo


def _build_controles(vars_dict):
    return [
        ("Fecha (AAAA-MM-DD)", vars_dict["dia"], 1, None, True),  # es_fecha=True
        ("Latitud (°)", vars_dict["lat"], 2, [-90, 90], False),
        ("Longitud (°)", vars_dict["lon"], 3, [-180, 180], False),
        ("Hora Local", vars_dict["hora"], 4, [0, 24], False),
        ("Humedad (%)", vars_dict["humedad"], 5, [0, 100], False),
        ("Temp. Base (K)", vars_dict["T_amb_base"], 6, [250, 350], False),
        ("Radiación (W/m²)", vars_dict["I_sol_base"], 7, [0, 1500], False),
        ("Temp. Mín (K)", vars_dict["T_min"], 8, [250, 350], False),
        ("Temp. Máx (K)", vars_dict["T_max"], 9, [250, 350], False),
    ]


def setup_panel_1(app):
    """Configura el contenido del Panel 1."""
    panel = app.panel_frames[0]

    labels = ["Temperatura ambiente (°C):", "Hora del día (0-23):", "Fecha (YYYY-MM-DD):", "Latitud:", "Longitud:"]
    app.entries = []
    app.entry_temp = None
    app.entry_time = None
    app.entry_date = None
    app.entry_lat = None
    app.entry_lon = None

    for label_text in labels:
        label = tk.Label(panel, text=label_text, bg=panel.cget("bg"), fg="black")
        label.pack(fill="x", padx=20, pady=5)
        entry = tk.Entry(panel)
        entry.pack(fill="x", padx=20, pady=5)
        app.entries.append(entry)

    app.entry_temp = app.entries[0]
    app.entry_time = app.entries[1]
    app.entry_date = app.entries[2]
    app.entry_lat = app.entries[3]
    app.entry_lon = app.entries[4]

    # NUEVO: porcentaje de sombra manual. Antes "Calcular temperatura
    # en sombra" exigía haber cargado una imagen y procesado la
    # selección en el Panel 2 (app.porcentaje_sombra solo se
    # llenaba ahí). Con este campo se puede calcular Tmrt para
    # cualquier % de sombra hipotético sin pasar por una imagen —
    # útil para explorar escenarios ("¿y si hubiera 60% de sombra
    # acá?") o cuando no se tiene una foto todavía. Si se deja vacío,
    # se sigue usando el % calculado desde la imagen, como antes.
    manual_label = tk.Label(
        panel, text="Porcentaje de sombra manual:",
        bg=panel.cget("bg"), fg="black",
    )
    manual_label.pack(fill="x", padx=20, pady=(15, 5))
    app.entry_porcentaje_manual = tk.Entry(panel)
    app.entry_porcentaje_manual.pack(fill="x", padx=20, pady=5)
    manual_hint = tk.Label(
        panel,
        text="Si se completa,\n se usa en vez del % calculado \n en el Panel 2.",
        bg=panel.cget("bg"), fg="#666666", font=("Arial", 8),
    )
    manual_hint.pack(fill="x", padx=20, pady=(0, 5))

    app.calculate_temp_button = tk.Button(
        panel,
        text="Calcular temperatura en sombra",
        command=app.calculate_temperature_in_shade,
    )
    app.calculate_temp_button.pack(fill="x", padx=20, pady=20)


def crear_control(app, panel, texto, var, fila, rango=None, es_fecha=False):
    # Columna del control con peso: el entry/scale se estira hasta
    # el ancho disponible del panel (antes quedaba fijo al tamaño
    # pedido y el panel avanzado desbordaba el contenedor).
    panel.grid_columnconfigure(1, weight=1)
    tk.Label(panel, text=texto, anchor="w", font=("Arial", 8), width=18).grid(
        row=fila, column=0, sticky="ew", padx=0, pady=10)
    if es_fecha:
        entry = tk.Entry(panel, width=12)
        entry.grid(row=fila, column=1, sticky="ew", padx=0)
        # FIX: el binding original llamaba a `actualizar_dia` como nombre
        # global (no existía) y habría dado NameError al presionar Enter;
        # ahora usa el método real de la app (app_ui.actualizar_dia).
        entry.bind("<Return>", lambda e: app.actualizar_dia(entry.get(), var))
    elif rango:
        scale = tk.Scale(panel, from_=rango[0], to=rango[1], variable=var,
                         orient=tk.HORIZONTAL, length=1, width=5)
        scale.grid(row=fila, column=1, sticky="ew", padx=0)


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
    contenido = panel

    diseno_label = tk.Label(contenido, text="Modelo", bg=panel.cget("bg"), fg="black")
    diseno_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

    modo_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    modo_frame.grid(row=1, column=0, sticky="w", pady=4)
    app.simple_mode_radio = tk.Radiobutton(
        modo_frame,
        text="Modo Simple",
        variable=app.modo_modelo,
        value="simple",
        bg=panel.cget("bg"),
        command=app._toggle_modelo_mode,
    )
    app.simple_mode_radio.grid(row=0, column=0, sticky="w")
    app.advanced_mode_radio = tk.Radiobutton(
        modo_frame,
        text="Modo Avanzado",
        variable=app.modo_modelo,
        value="advanced",
        bg=panel.cget("bg"),
        command=app._toggle_modelo_mode,
    )
    app.advanced_mode_radio.grid(row=1, column=0, sticky="w", pady=(2, 0))

    acciones_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    acciones_frame.grid(row=4, column=0, sticky="ew", pady=(6, 0))
    acciones_frame.grid_columnconfigure(0, weight=1)
    app.apply_location_button = tk.Button(
        acciones_frame,
        text="Aplicar ubicación",
        command=lambda: app._apply_location(True),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
        state="normal" if app.locations_data else "disabled",
    )
    app.apply_location_button.grid(row=0, column=0, sticky="ew", padx=0, pady=3)
    tk.Button(
        acciones_frame,
        text="Cargar Excel",
        command=app.cargar_excel_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=1, column=0, sticky="ew", padx=0, pady=3)
    tk.Button(
        acciones_frame,
        text="Guardar Excel",
        command=app.guardar_excel_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=2, column=0, sticky="ew", padx=0, pady=3)
    tk.Button(
        acciones_frame,
        text="Generar Gráfico",
        command=app.generar_grafico_modelo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=3, column=0, sticky="ew", padx=0, pady=3)
    tk.Button(
        acciones_frame,
        text="Vista 3D",
        command=lambda: modelo.generar_3d(app.vars_modelo),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=4, column=0, sticky="ew", padx=0, pady=3)

    app.simple_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    app.simple_frame.grid(row=2, column=0, sticky="nsew", pady=6)
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
    app.country_combo.grid(row=2, column=0, sticky="ew", pady=(2, 6), padx=5)
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
    app.city_combo.grid(row=4, column=0, sticky="ew", pady=(2, 6), padx=5)
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
    ).grid(row=6, column=0, sticky="ew", pady=(2, 6), padx=5)

    tk.Label(app.simple_frame, text="Temperatura aire (°C)", bg=panel.cget("bg")).grid(
        row=7, column=0, sticky="w", pady=(2, 0))
    tk.Entry(app.simple_frame, textvariable=app.simple_temp_air_c).grid(
        row=8, column=0, sticky="ew", pady=(2, 6), padx=0
    )
    tk.Label(app.simple_frame, text="Viento", bg=panel.cget("bg")).grid(
        row=9, column=0, sticky="w", pady=(2, 0))
    ttk.Combobox(
        app.simple_frame,
        textvariable=app.vars_modelo["viento"],
        values=["nulo", "moderado", "fuerte"],
    ).grid(row=10, column=0, sticky="ew", pady=(2, 6), padx=5)

    tk.Label(app.simple_frame, text="Humedad relativa (%)", bg=panel.cget("bg")).grid(
        row=11, column=0, sticky="w", pady=(2, 0)
    )
    tk.Entry(app.simple_frame, textvariable=app.simple_rh).grid(
        row=12, column=0, sticky="ew", pady=(2, 6), padx=5
    )

    # Herramientas de confort y calibración (análisis térmico)
    herramientas = tk.Frame(contenido, bg=panel.cget("bg"))
    herramientas.grid(row=3, column=0, sticky="ew", pady=(2, 6))
    herramientas.grid_columnconfigure(0, weight=1)
    tk.Label(herramientas, text="Herramientas", bg=panel.cget("bg"),
             font=("Arial", 9, "bold"), anchor="w").grid(
        row=0, column=0, sticky="ew", pady=(0, 4))
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
                  font=("Arial", 8, "bold")).grid(
            row=fila_btn, column=0, sticky="ew", pady=2)
        fila_btn += 1

    app.advanced_frame = tk.Frame(contenido, bg=panel.cget("bg"))
    app.advanced_frame.grid(row=2, column=0, sticky="nsew", pady=6)
    app.advanced_frame.grid_columnconfigure(1, weight=1)

    tk.Label(app.advanced_frame, text="Viento", bg=panel.cget("bg")).grid(
        row=0, column=0, sticky="w", pady=2)
    ttk.Combobox(
        app.advanced_frame,
        textvariable=app.vars_modelo["viento"],
        values=["nulo", "moderado", "fuerte"],
    ).grid(row=0, column=1, sticky="ew", pady=2, padx=(8, 5))

    tk.Label(app.advanced_frame, text="Configuraciones rápidas", bg=panel.cget("bg")).grid(
        row=1, column=0, sticky="w", pady=6
    )
    tk.Button(
        app.advanced_frame,
        text="Soleado",
        command=lambda: modelo.cargar_preset("soleado", app.vars_modelo),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=2, column=0, sticky="w", padx=0, pady=3)
    tk.Button(
        app.advanced_frame,
        text="Verano",
        command=lambda: modelo.cargar_preset("verano", app.vars),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=2, column=1, sticky="w", padx=10, pady=3)
    tk.Button(
        app.advanced_frame,
        text="Soleado",
        command=lambda: modelo.cargar_preset("soleado", app.vars),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=3, column=0, sticky="w", padx=0, pady=3)
    tk.Button(
        app.advanced_frame,
        text="Nublado",
        command=lambda: modelo.cargar_preset("nublado", app.vars),
        bg="#4CAF50",
        fg="white",
        font=("Arial", 8, "bold"),
    ).grid(row=3, column=1, sticky="w", padx=10, pady=3)

    panelin = tk.Frame(app.advanced_frame, bg=panel.cget("bg"))
    panelin.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)
    for texto, var, fila, rango, es_fecha in app.controles_modelo:
        crear_control(app, panelin, texto, var, fila, rango, es_fecha)
    app.vars_modelo["graph_frame"] = app.frame11
    _update_city_options(app)
    if app.locations_error:
        app.modo_modelo.set("advanced")
        app.simple_mode_radio.config(state="disabled")
    _toggle_modelo_mode(app)


def _toggle_modelo_mode(app):
    if app.modo_modelo.get() == "simple" and not app.locations_error:
        app.advanced_frame.grid_remove()
        app.simple_frame.grid()
    else:
        app.simple_frame.grid_remove()
        app.advanced_frame.grid()


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
        app.matriz_size.set(480)
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
    app.vars_modelo["_update_required"] = True
    if show_message:
        messagebox.showinfo("Ubicación aplicada",
                            f"Lat/Lon: {location['lat']}, {location['lon']}")