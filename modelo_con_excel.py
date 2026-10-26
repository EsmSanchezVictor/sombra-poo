import os
from core.effective_scenario import scenario_date, effective_model
from core.climate_profile import velocidad_viento, viento_categoria_a_ms
from core.surface_energy import surface_diagnostics_summary
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import math
from core.scene_objects import adaptar_objetos_escena
from core.species import color_copa, propiedades_especie
from core.crown_shapes import CANOPY_SHAPES, DEFAULT_CANOPY_SHAPE, normalize_canopy_shape
from ui.canopy_rendering import draw_canopy_2d
from core.climate_profile import temperatura_diurna_ciclo, VIENTO_CATEGORIA_MS
from core.solar_math import (
    solar_declination_deg, equation_of_time_degrees, standard_meridian_deg,
    timezone_offset_hours, solar_elevation_deg, solar_azimuth_deg,
)
from tkinter import messagebox
from plot_style import CMAP_TEMPERATURA
from core.excel_scene import save_scene_excel, load_scene_excel, apply_parameters_to_vars
from core.materials import get_surface_material, effective_structure_transmittance
from core.surface_energy import (
    solve_surface_energy_balance, cloud_fraction_from_label, downwelling_longwave,
)
from ui.scene3d import render_scene_3d
from ui.solar_indicator import add_solar_indicator_2d
from ui.modal_style import prepare_dialog, dialog_header
from core.vegetation import (
    VegetationConfig, phenology_factor, ground_latent_heat_flux_wm2,
    species_canopy_latent_flux_wm2,
)

# Constantes
# API histórica: las implementaciones físicas viven en core.surface_model.
from core.surface_model import (
    sigma,
    Material,
    Arbol,
    Estructura,
    materiales,
    MATERIAL_CHOICES,
    _norm_material_display,
    _MATERIAL_DISPLAY_BY_NORM,
    material_display_name,
    MATERIALES_LOWER,
    declinacion_solar,
    ecuacion_del_tiempo,
    _meridiano_estandar,
    _huso_desde_timezone,
    angulo_solar,
    azimut_solar,
    temperatura_ambiente,
    calcular_sombra_arboles,
    _punto_en_poligono,
    sombra_estructuras,
    _VIENTO_CATEGORIA_A_MS,
    calcular_coeficiente_conveccion,
    asignar_materiales_grilla,
    asignar_propiedades_avanzadas_grilla,
    _mascara_sombra_estructura,
    transmitancia_estructuras_avanzada,
    _vegetation_config_from_vars,
    _ground_vegetation_fraction_field,
    calcular_sombra_arboles_fenologica,
    _canopy_et_diagnostics,
    _surface_model_mode,
    _var_value,
    _longwave_local_avanzada,
    calcular_campo_termico_superficie
)


def generar_grafico(vars, frame):
    if '_update_required' not in vars or not vars['_update_required']:
        return

    from services.scenario_service import prepare_surface_scenario
    scenario = prepare_surface_scenario(vars)
    for widget in frame.winfo_children():
        widget.destroy()

    # FIX (bug #8, parte 1): cerrar cualquier figura anterior antes de crear
    # una nueva, para no acumular figuras de matplotlib en memoria en
    # sesiones largas de uso de la GUI.
    fig_anterior = vars.get('_current_fig')
    if fig_anterior is not None:
        plt.close(fig_anterior)

    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    vars['_current_fig'] = fig
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Configuración del espacio
    x = y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)

    # Cálculos principales
    theta_sol = np.radians(scenario['solar_elevation'])
    azimut_sol = np.radians(scenario['solar_azimuth'])
    # v29: metadatos SOLO visuales para orientar la iluminación VTK.
    vars["_render_solar_altitude_deg"] = float(np.degrees(theta_sol))
    vars["_render_solar_azimuth_deg"] = float(np.degrees(azimut_sol))
    # v14: radiación observada/manual puede entrar como GHI del instante.
    # Si no hay override, se conserva EXACTAMENTE el comportamiento legacy
    # del Panel 4: I_sol_base * sin(elevación).
    _rad_override = vars.get("_radiation_override_ghi")
    if hasattr(_rad_override, "get"):
        _rad_override = _rad_override.get()
    if _rad_override is None or _rad_override == "":
        I_sol = vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
        radiation_source = scenario["source_label"]
        radiation_quality = scenario["quality"]
    else:
        I_sol = max(0.0, float(_rad_override))
        radiation_source = str(vars.get("_radiation_source_label", "Radiación externa"))
        radiation_quality = str(vars.get("_radiation_quality", "external"))

    vars["_scene_objects"] = adaptar_objetos_escena(vars.get("arboles", []), vars.get("estructuras", []))
    debug_flag = vars.get("debug", False)
    debug = bool(debug_flag.get()) if hasattr(debug_flag, "get") else bool(debug_flag)

    # Temperatura del aire del instante. Una Ta observada tiene prioridad
    # porque corresponde exactamente al instante de la serie; si no existe,
    # modo simple usa T_amb_base y modo detallado conserva el ciclo Tmin/Tmax.
    modo_modelo = vars.get("_modo_modelo", "advanced")
    if hasattr(modo_modelo, "get"):
        modo_modelo = modo_modelo.get()
    air_override = vars.get("_air_temp_override_k")
    if hasattr(air_override, "get"):
        air_override = air_override.get()
    if air_override not in (None, ""):
        T_amb = float(air_override)
    elif str(modo_modelo).lower() == "simple":
        T_amb = float(vars["T_amb_base"].get())
    else:
        T_amb = temperatura_ambiente(vars["hora"].get(), vars["T_min"].get(), vars["T_max"].get())

    thermal = calcular_campo_termico_superficie(
        vars, X, Y, theta_sol, azimut_sol, I_sol, T_amb, debug=debug
    )
    T = thermal["T"]
    sombra_total = thermal["tau"]
    q_solar = thermal["q_solar"]
    h_c = thermal["h_c"]
    h_r = thermal["h_r"]
    surface_mode = thermal["model"]
    surface_model_label = thermal["model_label"]
    surface_diag = thermal.get("diagnostics", {})

    # Guardar datos para 3D
    vars["X"] = X
    vars["Y"] = Y
    vars["T"] = T

    app_instance = vars.get('_app_instance')
    temp_unit = app_instance.get_temperature_unit_symbol() if app_instance else "K"
    distance_unit = app_instance.get_distance_unit() if app_instance else "m"
    T_display = app_instance.convert_temperature_for_display(T) if app_instance else T

    # Configuración del gráfico. Edición y Modelo deben usar exactamente
    # el mismo rango visual: mínimo/máximo reales de la matriz, sin sumar
    # márgenes arbitrarios que hacían parecer distintos dos cálculos iguales.
    tmin = float(np.nanmin(T_display))
    tmax = float(np.nanmax(T_display))

    if debug:
        print("T min/max:", tmin, tmax)
        print("Sombra total min/max:", np.min(sombra_total), np.max(sombra_total))
        print("Radiación efectiva min/max:", np.min(q_solar), np.max(q_solar))

    if not np.isfinite(tmin) or not np.isfinite(tmax):
        tmin, tmax = 290.0, 310.0
    if np.isclose(tmin, tmax):
        niveles = np.linspace(tmin - 0.5, tmax + 0.5, 3)
    else:
        niveles = np.linspace(tmin, tmax, 20)
    niveles = np.sort(np.unique(niveles))

    contorno = ax.contourf(X, Y, T_display, niveles, cmap=CMAP_TEMPERATURA, alpha=0.8)
    ax.contour(X, Y, T_display, niveles, colors='k', linewidths=0.5)
    fig.colorbar(contorno, ax=ax, orientation='horizontal', pad=0.12).set_label(f'Temperatura superficial ({temp_unit})')
    add_solar_indicator_2d(
        ax, vars.get("_render_solar_azimuth_deg"), vars.get("_render_solar_altitude_deg"),
        corner="upper-right",
    )
    ax.set_xlabel(f'Distancia ({distance_unit})')
    ax.set_ylabel(f'Distancia ({distance_unit})')

    if debug:
        print(f"Min T: {np.nanmin(T)}, Max T: {np.nanmax(T)}")

    # Dibujar los objetos con la misma convención visual que Edición.
    if vars.get('arboles'):
        for idx, arbol in enumerate(vars['arboles']):
            draw_canopy_2d(
                ax, arbol, facecolor=color_copa(getattr(arbol, "especie", "")),
                edgecolor="darkgreen", alpha=0.68, zorder=6,
                label="Árboles" if idx == 0 else None,
            )
    for estructura in vars.get('estructuras', []):
        if estructura.tipo == 'Sendero':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1, estructura.y2 - estructura.y1,
                color='gray', alpha=0.3, label=f"Sendero ({estructura.material})",
            ))
        elif estructura.tipo == 'Pared':
            ax.plot(
                [estructura.x1, estructura.x2], [estructura.y1, estructura.y2],
                color='black', linewidth=2, label=f"Pared ({estructura.material})",
            )
        elif estructura.tipo == 'Galeria':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1, estructura.y2 - estructura.y1,
                color='saddlebrown', alpha=0.35, hatch='//',
                label=f"Galería ({estructura.material})",
            ))

    ax.set_title(f'Distribución de temperatura superficial\n{surface_model_label} · fuente radiativa: {radiation_source}')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        vistos = dict(zip(labels, handles))
        ax.legend(vistos.values(), vistos.keys(), loc='upper right', fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.5)

    # Función para manejar clics
    def on_click(event):
        if event.inaxes != ax:
            return

        if 'arboles' in vars:
            for arbol in vars['arboles']:
                if math.dist((event.xdata, event.ydata), (arbol.x, arbol.y)) < 5:
                    editar_elemento(vars, arbol=arbol)
                    temp_sombra = T[int(arbol.y), int(arbol.x)]
                    temp_sombra_display = app_instance.convert_temperature_for_display(temp_sombra) if app_instance else temp_sombra
                    detalles = (
                        f"Árbol en ({arbol.x}, {arbol.y})\n"
                        f"Temperatura: {temp_sombra_display:.2f} {temp_unit}\n"
                        f"Altura: {arbol.h} m\n"
                        f"Densidad copa: {arbol.rho_copa}\n"
                        f"Forma de copa: {normalize_canopy_shape(getattr(arbol, 'forma_copa', DEFAULT_CANOPY_SHAPE))}"
                    )
                    ax.set_title(detalles)
                    fig.canvas.draw_idle()
                    return

        if 'estructuras' in vars:
            for estructura in vars['estructuras']:
                if (estructura.x1 <= event.xdata <= estructura.x2 and estructura.y1 <= event.ydata <= estructura.y2):
                    editar_elemento(vars, estructura=estructura)
                    return

        if surface_mode in {"advanced", "advanced_vegetation"}:
            info_text = (
                f"Balance avanzado:\n"
                f"SW absorbida: {np.mean(surface_diag.get('q_shortwave_absorbed', q_solar)):.1f} W/m²\n"
                f"LW cielo: {surface_diag.get('longwave_down_wm2', 0.0):.1f} W/m²\n"
                f"Emisividad cielo: {surface_diag.get('sky_emissivity', 0.0):.3f}\n"
                f"Coef. convección: {h_c:.1f} W/m²K\n"
                f"LE suelo medio: {np.mean(surface_diag.get('q_latent', 0.0)):.1f} W/m²\n"
                f"Residuo máx.: {np.max(np.abs(surface_diag.get('residual_wm2', 0.0))):.3g} W/m²\n"
                f"Convergente: {surface_diag.get('converged')} · límite: {surface_diag.get('boundary_clipped')} · iter.: {surface_diag.get('iterations')}"
            )
        else:
            info_text = (
                f"Balance estándar:\n"
                f"Radiación solar absorbida: {q_solar.mean():.1f} W/m²\n"
                f"Coef. convección: {h_c:.1f} W/m²K\n"
                f"Coef. radiativo: {h_r.mean():.1f} W/m²K"
            )
        ax.text(0.05, 0.95, info_text, transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8), verticalalignment='top')

    canvas.mpl_connect('button_press_event', on_click)
    canvas.draw()

    # FIX (bug #8, parte 2): se eliminó el bloque que volvía a destruir los
    # widgets del frame y recreaba un segundo FigureCanvasTkAgg del mismo
    # `fig` justo después de dibujar el primero (código residual de un
    # refactor anterior). Con el fix de arriba queda un único canvas por
    # llamada, ya conectado a `on_click`.
    vars['_update_required'] = True

    return {
        "T": T,
        "shadow": sombra_total,
        "meta": {
            "hora": vars["hora"].get() if hasattr(vars.get("hora"), "get") else vars.get("hora"),
            "dia": vars["dia"].get() if hasattr(vars.get("dia"), "get") else vars.get("dia"),
            "lat": vars["lat"].get() if hasattr(vars.get("lat"), "get") else vars.get("lat"),
            "lon": vars["lon"].get() if hasattr(vars.get("lon"), "get") else vars.get("lon"),
            "I_sol": float(I_sol),
            "radiation_source": radiation_source,
            "radiation_quality": radiation_quality,
            "radiation_dni": vars.get("_radiation_override_dni"),
            "radiation_dhi": vars.get("_radiation_override_dhi"),
            "cloud_fraction": vars.get("_cloud_fraction_override"),
            "surface_model": surface_mode,
            "date_iso": scenario["date_iso"],
            "surface_diagnostics": surface_diagnostics_summary(surface_diag),
            "effective_scenario": vars.get("_effective_scenario"),
            "surface_model_label": surface_model_label,
            "sky_emissivity": (float(surface_diag.get("sky_emissivity")) if surface_mode in {"advanced", "advanced_vegetation"} else None),
            "energy_residual_max_wm2": (float(np.max(np.abs(surface_diag.get("residual_wm2", 0.0)))) if surface_mode in {"advanced", "advanced_vegetation"} else None),
            "latent_heat_mean_wm2": (float(np.mean(surface_diag.get("q_latent", 0.0))) if surface_mode == "advanced_vegetation" else 0.0),
        },
    }


def editar_elemento(vars, arbol=None, estructura=None):
    """Editor del Modelo con el mismo lenguaje visual que Edición (v35.6)."""
    app = vars.get("_app_instance") if isinstance(vars, dict) else None
    parent = getattr(app, "root", None)
    dialog = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
    dialog.title("Editar elemento")
    prepare_dialog(dialog, parent, modal=True, resizable=False)

    cont = ttk.Frame(dialog, padding=(18, 16, 18, 16))
    cont.pack(fill="both", expand=True)
    cont.columnconfigure(0, weight=1)
    es_arbol = arbol is not None
    dialog_header(
        cont,
        "Editar árbol" if es_arbol else "Editar estructura",
        "Ajustá los datos del elemento y guardá para regenerar el Modelo.",
        layout="grid",
    )
    form = ttk.Frame(cont)
    form.grid(row=1, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)
    entries = {}

    if es_arbol:
        fields = [
            ("X", arbol.x), ("Y", arbol.y), ("Altura (m)", arbol.h),
            ("Densidad Copa", arbol.rho_copa), ("Radio Copa", arbol.radio_copa),
        ]
    else:
        fields = [
            ("X1", estructura.x1), ("Y1", estructura.y1),
            ("X2", estructura.x2), ("Y2", estructura.y2),
            ("Altura (m)", estructura.altura), ("Opacidad", estructura.opacidad),
            ("Material", estructura.material),
        ]

    for i, (label, value) in enumerate(fields):
        ttk.Label(form, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=(0, 14), pady=6)
        if label == "Material":
            entry = ttk.Combobox(form, values=MATERIAL_CHOICES, state="readonly", width=32)
            entry.set(material_display_name(value))
        else:
            entry = ttk.Entry(form, width=34)
            entry.insert(0, str(value))
        entry.grid(row=i, column=1, sticky="ew", pady=6)
        entries[label] = entry

    combo_forma = None
    if es_arbol:
        row_forma = len(fields)
        ttk.Label(form, text="Forma de copa:").grid(row=row_forma, column=0, sticky="w", padx=(0, 14), pady=6)
        combo_forma = ttk.Combobox(form, values=CANOPY_SHAPES, state="readonly", width=32)
        combo_forma.set(normalize_canopy_shape(getattr(arbol, "forma_copa", DEFAULT_CANOPY_SHAPE)))
        combo_forma.grid(row=row_forma, column=1, sticky="ew", pady=6)

    def guardar_cambios():
        try:
            if es_arbol:
                x = float(entries["X"].get()); y = float(entries["Y"].get())
                h = float(entries["Altura (m)"].get())
                rho = float(entries["Densidad Copa"].get())
                radio = float(entries["Radio Copa"].get())
                if h <= 0 or radio <= 0:
                    raise ValueError("altura_radio")
                if not 0 <= rho <= 1:
                    raise ValueError("densidad")
                arbol.x, arbol.y, arbol.h = x, y, h
                arbol.rho_copa, arbol.radio_copa = rho, radio
                if combo_forma is not None:
                    arbol.forma_copa = normalize_canopy_shape(combo_forma.get())
            else:
                x1 = float(entries["X1"].get()); y1 = float(entries["Y1"].get())
                x2 = float(entries["X2"].get()); y2 = float(entries["Y2"].get())
                altura = float(entries["Altura (m)"].get())
                opacidad = float(entries["Opacidad"].get())
                if altura < 0:
                    raise ValueError("altura")
                if not 0 <= opacidad <= 1:
                    raise ValueError("opacidad")
                estructura.x1, estructura.y1, estructura.x2, estructura.y2 = x1, y1, x2, y2
                estructura.altura, estructura.opacidad = altura, opacidad
                estructura.material = entries["Material"].get()
            dialog.destroy()
            vars["_update_required"] = True
            generar_grafico(vars, vars["graph_frame"])
            if app is not None and hasattr(app, "mark_dirty"):
                app.mark_dirty()
        except ValueError as exc:
            msg = {
                "altura_radio": "La altura y el radio de copa deben ser mayores que cero.",
                "densidad": "La densidad de copa debe estar entre 0 y 1.",
                "altura": "La altura no puede ser negativa.",
                "opacidad": "La opacidad debe estar entre 0 y 1.",
            }.get(str(exc), "Revisá los valores numéricos ingresados.")
            messagebox.showerror("Valores inválidos", msg, parent=dialog)

    actions = ttk.Frame(cont)
    actions.grid(row=2, column=0, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancelar", command=dialog.destroy).pack(side="left", padx=(0, 8))
    ttk.Button(actions, text="Guardar cambios", command=guardar_cambios, style="DialogPrimary.TButton").pack(side="left")
    dialog.bind("<Return>", lambda _e: guardar_cambios())
    next(iter(entries.values())).focus_set()


def generar_3d(vars, frame=None):
    """Renderiza la escena 3D del Modelo en el contenedor compartido.

    Usa VTK embebido cuando está disponible y Matplotlib embebido como
    fallback. X/Y/T provienen del cálculo 2D ya ejecutado.
    """
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return None

    app = vars.get("_app_instance")
    if frame is None and app is not None and hasattr(app, "_get_scene_view_frames"):
        _view2d, frame, notebook = app._get_scene_view_frames("modelo")
        notebook.select(frame)
    if frame is None:
        messagebox.showerror(
            "Vista 3D",
            "No se encontró el contenedor 3D embebido. Regenere el gráfico desde el Panel Modelo.",
        )
        return None

    try:
        return render_scene_3d(vars, frame, title="Vista 3D — Modelo · sombra y temperatura")
    except Exception as exc:
        messagebox.showerror("Vista 3D", f"No se pudo generar la vista 3D:\n{exc}")
        return None

def cargar_preset(config, vars):
    """Aplica configuraciones rápidas coherentes con hemisferio y nubosidad."""
    config = str(config or "").strip().lower()
    lat_value = vars.get("lat", 0.0) if isinstance(vars, dict) else 0.0
    if hasattr(lat_value, "get"):
        try:
            lat_value = lat_value.get()
        except Exception:
            lat_value = 0.0
    try:
        southern = float(lat_value) < 0.0
    except (TypeError, ValueError):
        southern = False

    # 21 Jun ~= día 172; 21 Dic ~= día 355.
    summer_day = 355 if southern else 172
    winter_day = 172 if southern else 355
    presets = {
        "verano": {"T_min": 298, "T_max": 315, "I_sol_base": 1000, "dia": summer_day},
        "invierno": {"T_min": 275, "T_max": 290, "I_sol_base": 600, "dia": winter_day},
        "soleado": {"I_sol_base": 1200, "nubosidad": "Despejado"},
        "nublado": {"I_sol_base": 300, "nubosidad": "Nublado"},
    }
    if config not in presets:
        raise ValueError(f"Preset desconocido: {config}")

    for key, value in presets[config].items():
        target = vars.get(key) if isinstance(vars, dict) else None
        if hasattr(target, "set"):
            target.set(value)
        elif isinstance(vars, dict):
            vars[key] = value

    # Mantener la fecha ISO sincronizada: _fecha_modelo_actual prioriza este
    # campo sobre el día juliano y de otro modo un preset estacional podía
    # quedar visualmente cambiado pero calcular con una fecha anterior.
    if isinstance(vars, dict) and config in {"verano", "invierno"}:
        year_value = vars.get("_year", datetime.now().year)
        if hasattr(year_value, "get"):
            try:
                year_value = year_value.get()
            except Exception:
                year_value = datetime.now().year
        try:
            year = int(year_value)
        except (TypeError, ValueError):
            year = datetime.now().year
        day_value = vars.get("dia")
        day = int(day_value.get() if hasattr(day_value, "get") else day_value)
        date_value = (datetime(year, 1, 1) + timedelta(days=max(1, day) - 1)).date()
        vars["_date_iso"] = date_value.isoformat()
        vars["_year"] = year

    if isinstance(vars, dict):
        vars["_update_required"] = True

from ui.model_excel import _aplicar_parametros_app_desde_excel, cargar_excel, guardar_excel
