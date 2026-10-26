"""Carga/guardado de la escena Excel y sincronización de sus controles."""
from __future__ import annotations
import os
from tkinter import filedialog
import pandas as pd
from core.crown_shapes import DEFAULT_CANOPY_SHAPE
from tkinter import messagebox
from core.excel_scene import save_scene_excel, load_scene_excel, apply_parameters_to_vars
from core.surface_model import Arbol, Estructura, _surface_model_mode

def _aplicar_parametros_app_desde_excel(vars, parametros):
    """Sincroniza controles de la UI con los parámetros cargados.

    ``vars`` incluye ``_app_instance`` en la aplicación real; los tests y usos
    sin GUI simplemente ignoran esta parte.
    """
    app = vars.get('_app_instance') if isinstance(vars, dict) else None
    if app is None:
        return

    modo = str(parametros.get('modo_calculo', '') or '').strip().lower()
    if modo in {'simple', 'advanced'} and hasattr(app, 'modo_modelo'):
        app.modo_modelo.set(modo)

    surface_mode = str(parametros.get('surface_model_mode', '') or '').strip().lower()
    if surface_mode in {'standard', 'advanced', 'advanced_vegetation'} and hasattr(app, 'surface_model_mode'):
        app.surface_model_mode.set(surface_mode)

    for key in ("ground_vegetation_fraction", "vegetation_water_availability", "canopy_water_availability"):
        if key in parametros and hasattr(app, "settings"):
            try:
                app.settings[key] = float(parametros[key])
            except (TypeError, ValueError):
                pass

    if 'simple_temp_air_c' in parametros and hasattr(app, 'simple_temp_air_c'):
        try:
            app.simple_temp_air_c.set(float(parametros['simple_temp_air_c']))
        except (TypeError, ValueError):
            pass
    elif 'T_amb_base_K' in parametros and hasattr(app, 'simple_temp_air_c'):
        try:
            app.simple_temp_air_c.set(float(parametros['T_amb_base_K']) - 273.15)
        except (TypeError, ValueError):
            pass

    if 'simple_rh_pct' in parametros and hasattr(app, 'simple_rh'):
        try:
            app.simple_rh.set(float(parametros['simple_rh_pct']))
        except (TypeError, ValueError):
            pass
    elif 'humedad_relativa_pct' in parametros and hasattr(app, 'simple_rh'):
        try:
            app.simple_rh.set(float(parametros['humedad_relativa_pct']))
        except (TypeError, ValueError):
            pass

    for key, attr in (
        ('nubosidad', 'simple_cloudiness'),
        ('simple_country', 'simple_country'),
        ('simple_city', 'simple_city'),
    ):
        if key in parametros and hasattr(app, attr):
            try:
                getattr(app, attr).set(str(parametros[key]))
            except Exception:
                pass

    if parametros.get("radiation_source_mode") and hasattr(app, "radiation_source_mode"):
        mode_rad = str(parametros.get("radiation_source_mode")).strip().lower()
        if mode_rad in {"clear_sky", "manual_measured", "manual_scenario", "observed_series"}:
            app.radiation_source_mode.set(mode_rad)
    met_name = str(parametros.get("meteorology_csv", "") or "").strip()
    if met_name and hasattr(app, "meteorology_service"):
        candidates = [met_name]
        project = getattr(getattr(app, "project_manager", None), "current_project", None)
        if project is not None:
            candidates.insert(0, os.path.join(project.layout.meteorology_dir, os.path.basename(met_name)))
        for met_path in candidates:
            if os.path.exists(met_path):
                try:
                    app.meteorology_service.load_series(met_path, timezone=app._timezone_actual())
                    app.meteorology_series_path = met_path
                    break
                except Exception:
                    pass
    try:
        app._refresh_meteorology_status()
    except Exception:
        pass

    try:
        app._toggle_modelo_mode()
    except Exception:
        pass


def cargar_excel(vars, filepath=None):
    """Carga geometría y, si existen, parámetros térmicos del Excel.

    Compatibilidad:
    - archivos nuevos: restauran escena + condiciones de cálculo;
    - archivos viejos sin ``Parametros``: cargan la escena y conservan los
      parámetros actuales de la UI;
    - hojas ``Estructuras``/``Árboles`` vacías sin encabezados: se aceptan
      como listas vacías en vez de producir KeyError.
    """
    if filepath is None:
        filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not filepath:
        return None
    try:
        libro = load_scene_excel(filepath)

        vars['arboles'] = []
        for _, row in libro.arboles.iterrows():
            arbol = Arbol(
                row['X'], row['Y'], row['Altura (m)'],
                row['Densidad_copa (0-1)'], row['Radio_copa (m)'],
                forma_copa=row.get('Forma_copa', DEFAULT_CANOPY_SHAPE)
            )
            especie = row.get('Especie', '')
            if pd.notna(especie) and str(especie).strip():
                arbol.especie = str(especie).strip()
            vars['arboles'].append(arbol)

        vars['estructuras'] = []
        for _, row in libro.estructuras.iterrows():
            vars['estructuras'].append(Estructura(
                tipo=row['Tipo'],
                x1=row['X_inicial'], y1=row['Y_inicial'],
                x2=row['X_final'], y2=row['Y_final'],
                altura=row['Altura (m)'],
                opacidad=row['Opacidad (0-1)'],
                material=row['Material'],
            ))

        if libro.parametros:
            apply_parameters_to_vars(vars, libro.parametros)
            _aplicar_parametros_app_desde_excel(vars, libro.parametros)

        messagebox.showinfo(
            "Éxito",
            "Datos cargados correctamente" +
            (" con sus parámetros de cálculo." if libro.parametros else
             ". Archivo antiguo: se conservaron los parámetros actuales del modelo.")
        )
        vars['_update_required'] = True
        return filepath
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
        return None


def guardar_excel(vars, filepath=None, app=None, notify=True):
    """Guarda el estado ACTUAL del modelo, no una mera copia del Excel fuente."""
    if app is None and isinstance(vars, dict):
        app = vars.get('_app_instance')

    if filepath is None:
        project = getattr(getattr(app, "project_manager", None), "current_project", None) if app is not None else None
        if project is not None:
            filepath = project.layout.model_excel
        else:
            filepath = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel files', '*.xlsx')],
            )
    if not filepath:
        return None

    try:
        modo = vars.get('_modo_modelo', 'advanced') if isinstance(vars, dict) else 'advanced'
        if hasattr(modo, 'get'):
            modo = modo.get()
        if app is not None and hasattr(app, 'modo_modelo'):
            modo = app.modo_modelo.get()
        modo = str(modo or 'advanced').lower()
        if modo not in {'simple', 'advanced'}:
            modo = 'advanced'

        save_scene_excel(
            filepath,
            vars.get('arboles', []),
            vars.get('estructuras', []),
            vars,
            calculation_mode=modo,
            origin='modelo',
            app=app,
            extra_parameters={
                'modo_ui_origen': modo,
                'surface_model_mode': _surface_model_mode(vars),
                'ground_vegetation_fraction': getattr(app, 'settings', {}).get('ground_vegetation_fraction', 0.50) if app else 0.50,
                'vegetation_water_availability': getattr(app, 'settings', {}).get('vegetation_water_availability', 0.75) if app else 0.75,
                'canopy_water_availability': getattr(app, 'settings', {}).get('canopy_water_availability', 0.75) if app else 0.75,
                'radiation_source_mode': getattr(getattr(app, 'radiation_source_mode', None), 'get', lambda: 'clear_sky')() if app else 'clear_sky',
                'radiation_source_label': (getattr(app, 'last_meteorology_data', None) or {}).get('source_label', '' ) if app else '',
                'radiation_quality': (getattr(app, 'last_meteorology_data', None) or {}).get('quality', '' ) if app else '',
                'meteorology_csv': os.path.basename(getattr(app, 'meteorology_series_path', '') or '') if app else '',
                'ghi_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('ghi', '' ) if app else '',
                'dni_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('dni', '' ) if app else '',
                'dhi_wm2': (getattr(app, 'last_meteorology_data', None) or {}).get('dhi', '' ) if app else '',
            },
        )
        if notify:
            messagebox.showinfo(
                'Modelo',
                'Excel guardado con la escena y los parámetros actuales del cálculo.'
            )
        return filepath
    except Exception as e:
        messagebox.showerror('Error', f'Error al guardar archivo:\n{str(e)}')
        return None

