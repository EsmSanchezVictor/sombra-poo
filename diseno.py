import os
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import math
from core.scene_objects import adaptar_objetos_escena
from core.species import color_copa, nombres_especies, propiedades_especie
from core.crown_shapes import CANOPY_SHAPES, DEFAULT_CANOPY_SHAPE, normalize_canopy_shape
from ui.canopy_rendering import draw_canopy_2d
from plot_style import CMAP_TEMPERATURA
from core.excel_scene import save_scene_excel, load_scene_excel, apply_parameters_to_vars
from ui.scene3d import render_scene_3d
from ui.solar_indicator import add_solar_indicator_2d
from ui.modal_style import prepare_dialog, center_dialog, dialog_header

# Constantes físicas
sigma = 5.67e-8  # Constante de Stefan-Boltzmann
# variables
elemento_temporal = None

modo=None
archivo_actual = None 

# CAMBIO: las clases Arbol/Estructura/Material, el diccionario de
# materiales y TODAS las funciones físicas se importan de
# modelo_con_excel.py — diseño.py tenía copias propias con los bugs
# ya corregidos allá (alpha=1e-7 para composites, ángulo horario con
# (lon/15), seno sin desfase térmico, convección por categoría fija,
# sombras circulares sin elongación, bounding box de paredes, lookup
# de materiales que fallaba con mayúsculas). Una sola fuente de verdad.
from modelo_con_excel import (
    Arbol, Estructura, Material, materiales, MATERIALES_LOWER,
    MATERIAL_CHOICES, material_display_name,
    asignar_materiales_grilla, calcular_campo_termico_superficie,
    angulo_solar as _angulo_solar,
    azimut_solar as _azimut_solar,
    temperatura_ambiente as _temperatura_ambiente,
    calcular_coeficiente_conveccion as _calcular_coeficiente_conveccion,
    calcular_sombra_arboles as _calcular_sombra_arboles,
    sombra_estructuras as _sombra_estructuras,
    _huso_desde_timezone,
)


def _huso_horas(vars):
    """Devuelve el huso real de la fecha si hay timezone disponible.

    Edición y Modelo deben usar la misma geometría solar. Antes Edición
    caía en la heurística por longitud mientras Modelo usaba timezone, por
    lo que un mismo Excel podía cambiar de sombra/temperatura al recargarse.
    """
    huso = vars.get("huso_horas")
    huso_val = huso.get() if hasattr(huso, "get") else huso

    tz = vars.get("timezone")
    tz_name = tz.get() if hasattr(tz, "get") else tz
    if tz_name:
        dia = vars.get("dia")
        hora = vars.get("hora")
        dia_val = dia.get() if hasattr(dia, "get") else dia
        hora_val = hora.get() if hasattr(hora, "get") else hora
        try:
            calculado = _huso_desde_timezone(str(tz_name), int(dia_val), float(hora_val))
            if calculado is not None:
                return calculado
        except Exception:
            pass
    return huso_val


def crear_area_grafico(vars, frame, app):
    """Crea una única figura de edición.

    v17 ejecutaba ``actualizar_grafico`` dos veces y además creaba una
    figura intermedia que quedaba retenida por pyplot. v18 delega todo en
    una sola actualización y devuelve exactamente el canvas visible.
    """
    # v29: si ``frame`` es una pestaña de ttk.Notebook ya tiene gestor
    # geométrico propio; no intentar reubicarlo con grid().
    manager_fn = getattr(frame, "winfo_manager", None)
    if manager_fn is None or not manager_fn():
        frame.grid(row=1, column=1, sticky="nsew")
    vars['_app_instance'] = app
    return actualizar_grafico(vars, frame)
""" def crear_menu(self):
    menubar = tk.Menu(self.root)
    archivo_menu = tk.Menu(menubar, tearoff=0)
    archivo_menu.add_command(label="Abrir", command=self.abrir_archivo)
    archivo_menu.add_command(label="Guardar", command=self.guardar)
    archivo_menu.add_command(label="Guardar Como", command=self.guardar_como)
    menubar.add_cascade(label="Archivo", menu=archivo_menu)
    self.root.config(menu=menubar) """
def establecer_modo(modos, app):
    app.modo = modos
    elemento_temporal = None
def manejar_click(event, app):
    if not event.inaxes:
        return
        
    x, y = event.xdata, event.ydata
    
    if  app.modo == 'arbol':
        mostrar_dialogo_arbol(x, y,app)
    elif  app.modo == 'estructura':
        if not hasattr(app, 'elemento_temporal') or app.elemento_temporal is None:
            app.elemento_temporal = (x, y)
            messagebox.showinfo("Instrucción", "Haz clic donde quieras colocar el extremo final de la estructura")
        else:
            x1, y1 = app.elemento_temporal
            mostrar_dialogo_estructura(x1, y1, x, y,app)
            app.elemento_temporal = None
    else:
        seleccionar_elemento(x, y,app.vars,app)
def _combo_especie(parent, entries, fila, prefijo=""):
    """Combobox de especie que autocompleta Altura/Densidad/Radio con
    las propiedades documentadas de la biblioteca (core/species.py).
    El usuario puede sobreescribir los valores después del autocompletado."""
    ttk.Label(parent, text="Especie:").grid(row=fila, column=0, sticky="w", padx=(0, 14), pady=6)
    combo = ttk.Combobox(parent, values=nombres_especies(), state="readonly")
    combo.set("Plátano (Platanus × acerifolia)")

    def aplicar(_event=None):
        p = propiedades_especie(combo.get())
        for clave, valor in (("Altura (m):", p["altura_tipica"]),
                             ("Densidad Copa (0-1):", p["rho_copa"]),
                             ("Radio Copa (m):", p["radio_copa_tipico"])):
            entry = entries.get(clave)
            if entry is None:
                continue
            entry.delete(0, "end")
            entry.insert(0, str(valor))

    combo.bind("<<ComboboxSelected>>", aplicar)
    combo.grid(row=fila, column=1, sticky="ew", pady=6)
    aplicar()
    return combo


def _centrar_dialogo(dialogo, parent=None):
    """Compatibilidad: delegado al centrado visual común de v35.6."""
    center_dialog(dialogo, parent)


def _crear_dialogo_unico(app, attr_name, titulo):
    """Crea un único Toplevel modal por tipo de editor.

    Además de evitar ventanas duplicadas por dobles eventos de Matplotlib,
    ``grab_set`` impide que el usuario siga actuando sobre la escena mientras
    hay un formulario incompleto abierto.
    """
    existente = getattr(app, attr_name, None)
    try:
        if existente is not None and existente.winfo_exists():
            existente.deiconify()
            existente.lift()
            existente.focus_force()
            return None, None
    except tk.TclError:
        pass

    parent = getattr(app, "root", None)
    dialogo = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
    setattr(app, attr_name, dialogo)
    dialogo.title(titulo)
    prepare_dialog(dialogo, parent, modal=False, resizable=False, escape_closes=False)

    def cerrar():
        if getattr(app, attr_name, None) is dialogo:
            setattr(app, attr_name, None)
        try:
            dialogo.grab_release()
        except tk.TclError:
            pass
        try:
            dialogo.destroy()
        except tk.TclError:
            pass

    dialogo.protocol("WM_DELETE_WINDOW", cerrar)
    dialogo.bind("<Escape>", lambda _e: cerrar())
    dialogo.after_idle(lambda: _centrar_dialogo(dialogo, parent))
    try:
        dialogo.grab_set()
    except tk.TclError:
        pass
    return dialogo, cerrar


def _titulo_dialogo(parent, titulo, subtitulo):
    return dialog_header(parent, titulo, subtitulo, layout="grid")


def mostrar_dialogo_arbol(x, y, app):
    dialogo, cerrar_dialogo = _crear_dialogo_unico(app, "_dialogo_arbol", "Nuevo Árbol")
    if dialogo is None:
        return

    cont = ttk.Frame(dialogo, padding=(18, 16, 18, 16))
    cont.pack(fill="both", expand=True)
    cont.columnconfigure(0, weight=1)
    _titulo_dialogo(
        cont,
        "Añadir árbol",
        f"Posición seleccionada: X {x:.2f} · Y {y:.2f}",
    )

    form = ttk.Frame(cont)
    form.grid(row=1, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)

    campos = [
        ('Altura (m):', '5'),
        ('Densidad Copa (0-1):', '0.8'),
        ('Radio Copa (m):', '3')
    ]

    entries = {}
    for i, (label, valor) in enumerate(campos):
        fila = i + 2
        ttk.Label(form, text=label).grid(
            row=fila, column=0, sticky="w", padx=(0, 14), pady=6
        )
        entry = ttk.Entry(form, width=32)
        entry.insert(0, valor)
        entry.grid(row=fila, column=1, sticky="ew", pady=6)
        entries[label] = entry

    combo_especie = _combo_especie(form, entries, 0)
    combo_especie.configure(width=34)

    ttk.Label(form, text="Forma de copa:").grid(
        row=1, column=0, sticky="w", padx=(0, 14), pady=6
    )
    combo_forma = ttk.Combobox(
        form,
        values=CANOPY_SHAPES,
        state="readonly",
        width=32,
    )
    combo_forma.set(DEFAULT_CANOPY_SHAPE)
    combo_forma.grid(row=1, column=1, sticky="ew", pady=6)

    def guardar():
        try:
            altura = float(entries['Altura (m):'].get())
            densidad = float(entries['Densidad Copa (0-1):'].get())
            radio = float(entries['Radio Copa (m):'].get())
            if altura <= 0 or radio <= 0:
                raise ValueError("altura_radio")
            if not 0.0 <= densidad <= 1.0:
                raise ValueError("densidad")
            nuevo_arbol = Arbol(
                x=x,
                y=y,
                h=altura,
                rho_copa=densidad,
                radio_copa=radio,
                forma_copa=combo_forma.get(),
                especie=combo_especie.get(),
            )
            app.vars['arboles'].append(nuevo_arbol)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(app.vars, target_frame)
            cerrar_dialogo()
        except ValueError as exc:
            if str(exc) == "densidad":
                msg = "La densidad de copa debe estar entre 0 y 1."
            elif str(exc) == "altura_radio":
                msg = "La altura y el radio de copa deben ser mayores que cero."
            else:
                msg = "Revisá los valores numéricos ingresados."
            messagebox.showerror("Valores inválidos", msg, parent=dialogo)

    acciones = ttk.Frame(cont)
    acciones.grid(row=2, column=0, sticky="e", pady=(16, 0))
    ttk.Button(acciones, text="Cancelar", command=cerrar_dialogo).pack(side="left", padx=(0, 8))
    ttk.Button(acciones, text="Guardar árbol", command=guardar).pack(side="left")

    dialogo.bind("<Return>", lambda _e: guardar())
    combo_especie.focus_set()


def mostrar_dialogo_estructura(x1, y1, x2, y2, app):
    dialogo, cerrar_dialogo = _crear_dialogo_unico(app, "_dialogo_estructura", "Nueva Estructura")
    if dialogo is None:
        return

    cont = ttk.Frame(dialogo, padding=(18, 16, 18, 16))
    cont.pack(fill="both", expand=True)
    cont.columnconfigure(0, weight=1)
    _titulo_dialogo(
        cont,
        "Añadir estructura",
        f"Inicio: ({x1:.2f}, {y1:.2f}) · Fin: ({x2:.2f}, {y2:.2f})",
    )

    form = ttk.Frame(cont)
    form.grid(row=1, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)

    ttk.Label(form, text="Tipo:").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
    tipo = ttk.Combobox(form, values=("Pared", "Galeria", "Sendero"), state="readonly", width=34)
    tipo.set("Pared")
    tipo.grid(row=0, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Altura (m):").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
    altura = ttk.Entry(form, width=36)
    altura.insert(0, "0")
    altura.grid(row=1, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Opacidad (0-1):").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=6)
    opacidad = ttk.Entry(form, width=36)
    opacidad.insert(0, "1")
    opacidad.grid(row=2, column=1, sticky="ew", pady=6)

    ttk.Label(form, text="Material:").grid(row=3, column=0, sticky="w", padx=(0, 14), pady=6)
    material = ttk.Combobox(form, values=MATERIAL_CHOICES, state="readonly", width=34)
    material.set("Hormigón")
    material.grid(row=3, column=1, sticky="ew", pady=6)

    def guardar():
        try:
            altura_val = float(altura.get())
            opacidad_val = float(opacidad.get())
            if altura_val < 0:
                raise ValueError("altura")
            if not 0.0 <= opacidad_val <= 1.0:
                raise ValueError("opacidad")
            nueva_estructura = Estructura(
                tipo=tipo.get(),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                altura=altura_val,
                opacidad=opacidad_val,
                material=material.get(),
            )
            app.vars['estructuras'].append(nueva_estructura)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(app.vars, target_frame)
            cerrar_dialogo()
        except ValueError as exc:
            if str(exc) == "opacidad":
                msg = "La opacidad debe estar entre 0 y 1."
            elif str(exc) == "altura":
                msg = "La altura no puede ser negativa."
            else:
                msg = "Revisá los valores numéricos ingresados."
            messagebox.showerror("Valores inválidos", msg, parent=dialogo)

    acciones = ttk.Frame(cont)
    acciones.grid(row=2, column=0, sticky="e", pady=(16, 0))
    ttk.Button(acciones, text="Cancelar", command=cerrar_dialogo).pack(side="left", padx=(0, 8))
    ttk.Button(acciones, text="Guardar estructura", command=guardar).pack(side="left")

    dialogo.bind("<Return>", lambda _e: guardar())
    tipo.focus_set()

def seleccionar_elemento(x, y,vars,app):
    for arbol in vars['arboles']:
        if math.dist((x, y), (arbol.x, arbol.y)) < 5:
            mostrar_dialogo_edicion(arbol=arbol, vars=vars, app=app)
            return
            
    for estructura in vars['estructuras']:
        if (estructura.x1 <= x <= estructura.x2 and 
            estructura.y1 <= y <= estructura.y2):
            mostrar_dialogo_edicion(estructura=estructura, vars=vars, app=app)
            return
def mostrar_dialogo_edicion(arbol=None, estructura=None, vars=None, app=None):
    """Editor homogéneo de árboles/estructuras (v35.6)."""
    if app is not None:
        dialogo, cerrar_dialogo = _crear_dialogo_unico(app, "_dialogo_edicion", "Editar elemento")
        if dialogo is None:
            return
    else:
        dialogo = tk.Toplevel()
        dialogo.title("Editar elemento")
        prepare_dialog(dialogo, None, modal=True, resizable=False)
        cerrar_dialogo = dialogo.destroy

    es_arbol = arbol is not None
    obj = arbol if es_arbol else estructura
    cont = ttk.Frame(dialogo, padding=(18, 16, 18, 16))
    cont.pack(fill="both", expand=True)
    cont.columnconfigure(0, weight=1)
    _titulo_dialogo(
        cont,
        "Editar árbol" if es_arbol else "Editar estructura",
        "Modificá los valores y guardá los cambios. También podés eliminar el elemento de la escena.",
    )

    form = ttk.Frame(cont)
    form.grid(row=1, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)
    entries = {}
    combo_especie = None
    combo_forma = None

    if es_arbol:
        campos = [
            ("X:", arbol.x),
            ("Y:", arbol.y),
            ("Altura (m):", arbol.h),
            ("Densidad Copa (0-1):", arbol.rho_copa),
            ("Radio Copa (m):", arbol.radio_copa),
        ]
        # Crear primero los Entry para que el selector de especie pueda autocompletar.
        for i, (label, valor) in enumerate(campos, start=2):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=(0, 14), pady=6)
            entry = ttk.Entry(form, width=32)
            entry.insert(0, str(valor))
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            entries[label] = entry

        combo_especie = _combo_especie(form, entries, 0)
        combo_especie.configure(width=34)
        especie_actual = getattr(arbol, "especie", None)
        if especie_actual in nombres_especies():
            combo_especie.set(especie_actual)

        ttk.Label(form, text="Forma de copa:").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
        combo_forma = ttk.Combobox(form, values=CANOPY_SHAPES, state="readonly", width=32)
        combo_forma.set(normalize_canopy_shape(getattr(arbol, "forma_copa", DEFAULT_CANOPY_SHAPE)))
        combo_forma.grid(row=1, column=1, sticky="ew", pady=6)

        # Restaurar los valores reales del ejemplar tras el autocompletado de especie.
        for label, valor in (("Altura (m):", arbol.h),
                             ("Densidad Copa (0-1):", arbol.rho_copa),
                             ("Radio Copa (m):", arbol.radio_copa)):
            entries[label].delete(0, "end")
            entries[label].insert(0, str(valor))
    else:
        campos = [
            ("X1:", estructura.x1),
            ("Y1:", estructura.y1),
            ("X2:", estructura.x2),
            ("Y2:", estructura.y2),
            ("Altura (m):", estructura.altura),
            ("Opacidad (0-1):", estructura.opacidad),
            ("Material:", estructura.material),
        ]
        for i, (label, valor) in enumerate(campos):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=(0, 14), pady=6)
            if label == "Material:":
                entry = ttk.Combobox(form, values=MATERIAL_CHOICES, state="readonly", width=32)
                entry.set(material_display_name(valor))
            else:
                entry = ttk.Entry(form, width=34)
                entry.insert(0, str(valor))
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            entries[label] = entry

    def guardar():
        try:
            if es_arbol:
                x = float(entries["X:"].get())
                y = float(entries["Y:"].get())
                h = float(entries["Altura (m):"].get())
                rho = float(entries["Densidad Copa (0-1):"].get())
                radio = float(entries["Radio Copa (m):"].get())
                if h <= 0 or radio <= 0:
                    raise ValueError("altura_radio")
                if not 0.0 <= rho <= 1.0:
                    raise ValueError("densidad")
                arbol.x, arbol.y, arbol.h = x, y, h
                arbol.rho_copa, arbol.radio_copa = rho, radio
                arbol.especie = combo_especie.get() if combo_especie is not None else getattr(arbol, "especie", "")
                arbol.forma_copa = normalize_canopy_shape(combo_forma.get()) if combo_forma is not None else DEFAULT_CANOPY_SHAPE
            else:
                x1 = float(entries["X1:"].get())
                y1 = float(entries["Y1:"].get())
                x2 = float(entries["X2:"].get())
                y2 = float(entries["Y2:"].get())
                altura = float(entries["Altura (m):"].get())
                opacidad = float(entries["Opacidad (0-1):"].get())
                if altura < 0:
                    raise ValueError("altura")
                if not 0.0 <= opacidad <= 1.0:
                    raise ValueError("opacidad")
                estructura.x1, estructura.y1, estructura.x2, estructura.y2 = x1, y1, x2, y2
                estructura.altura, estructura.opacidad = altura, opacidad
                estructura.material = entries["Material:"].get()

            if app is not None:
                target_frame = getattr(app, "frame7", app.frame2)
                actualizar_grafico(vars, target_frame)
                if hasattr(app, "mark_dirty"):
                    app.mark_dirty()
            cerrar_dialogo()
        except ValueError as exc:
            code = str(exc)
            mensajes = {
                "altura_radio": "La altura y el radio de copa deben ser mayores que cero.",
                "densidad": "La densidad de copa debe estar entre 0 y 1.",
                "altura": "La altura no puede ser negativa.",
                "opacidad": "La opacidad debe estar entre 0 y 1.",
            }
            messagebox.showerror("Valores inválidos", mensajes.get(code, "Revisá los valores numéricos ingresados."), parent=dialogo)

    def eliminar():
        if not messagebox.askyesno("Eliminar elemento", "¿Eliminar este elemento de la escena?", parent=dialogo):
            return
        if es_arbol:
            vars["arboles"].remove(obj)
        else:
            vars["estructuras"].remove(obj)
        if app is not None:
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(vars, target_frame)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
        cerrar_dialogo()

    acciones = ttk.Frame(cont)
    acciones.grid(row=2, column=0, sticky="ew", pady=(16, 0))
    ttk.Button(acciones, text="Eliminar", command=eliminar).pack(side="left")
    ttk.Button(acciones, text="Cancelar", command=cerrar_dialogo).pack(side="right", padx=(8, 0))
    ttk.Button(acciones, text="Guardar cambios", command=guardar, style="DialogPrimary.TButton").pack(side="right")

    dialogo.bind("<Return>", lambda _e: guardar())
    if combo_especie is not None:
        combo_especie.focus_set()
    else:
        next(iter(entries.values())).focus_set()

def actualizar_grafico(vars, frame):
    # Cerrar figura anterior ANTES de destruir el widget Tk. Esto rompe las
    # referencias de artistas/canvas y evita crecimiento de RAM al editar.
    fig_anterior = vars.pop('_current_fig', None)
    if fig_anterior is not None:
        try:
            plt.close(fig_anterior)
        except Exception:
            pass
    for widget in frame.winfo_children():
        widget.destroy()
    
    # Configuración del espacio de simulación
    x = y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)
    
    # Cálculos principales
    theta_sol = angulo_solar(vars)
    azimut_sol = azimut_solar(vars, theta_sol)
    # v29: metadatos SOLO visuales para orientar la iluminación VTK.
    # Son los mismos ángulos ya calculados; no participan en la física.
    vars["_render_solar_altitude_deg"] = float(np.degrees(theta_sol))
    vars["_render_solar_azimuth_deg"] = float(np.degrees(azimut_sol))
    I_sol = vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
    
    # Cálculo térmico unificado con Modelo. El modo de superficie se lee
    # de Preferencias; estándar preserva la física legacy y avanzado usa
    # el balance no lineal/materiales ópticos de la v12.
    vars["_scene_objects"] = adaptar_objetos_escena(vars.get("arboles", []), vars.get("estructuras", []))
    T_amb = temperatura_ambiente(vars)
    thermal = calcular_campo_termico_superficie(
        vars, X, Y, theta_sol, azimut_sol, I_sol, T_amb, debug=False
    )
    T = thermal["T"]
    sombra_total = thermal["tau"]
    q_solar = thermal["q_solar"]
    h_c = thermal["h_c"]
    surface_model_label = thermal["model_label"]
    
    app_instance = vars.get('_app_instance')
    temp_unit = app_instance.get_temperature_unit_symbol() if app_instance else "K"
    distance_unit = app_instance.get_distance_unit() if app_instance else "m"
    T_display = app_instance.convert_temperature_for_display(T) if app_instance else T    
    
    # Configuración de niveles para el contorno
    nivel_min = np.nanmin(T_display)
    nivel_max = np.nanmax(T_display)
    
    # Manejo de casos especiales
    if np.isnan(nivel_min) or np.isnan(nivel_max):
        nivel_min, nivel_max = 290, 310  # Valores por defecto si hay NaNs
    
    if nivel_min == nivel_max:
        # Crear un pequeño rango artificial si todos los valores son iguales
        niveles = np.linspace(nivel_min - 0.5, nivel_max + 0.5, 3)
    else:
        # Generar niveles normales
        niveles = np.linspace(nivel_min, nivel_max, 20)
    
    # Asegurar niveles únicos y ordenados
    niveles = np.sort(np.unique(niveles))
    
    # Configurar el gráfico
    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    vars['_current_fig'] = fig
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Crear el gráfico de contorno
    #
    # CAMBIO: usaba 'viridis' hardcodeado acá, mientras que generar_3d()
    # ya usaba CMAP_TEMPERATURA — dos paletas distintas para representar
    # el mismo dato (temperatura) en 2D y 3D del mismo modo edición.
    # Unificado a CMAP_TEMPERATURA para que el plano y la vista 3D se
    # lean como la misma escala.
    try:
        contorno = ax.contourf(X, Y, T_display, niveles, cmap=CMAP_TEMPERATURA, alpha=0.8)
        ax.contour(X, Y, T_display, niveles, colors='k', linewidths=0.5)
    except ValueError as e:
        messagebox.showerror("Error", f"Problema al generar el gráfico: {str(e)}")
        return
    
    # Barra de color
    cbar = fig.colorbar(contorno, ax=ax, orientation='horizontal', pad=0.12)
    cbar.set_label(f'Temperatura superficial ({temp_unit})')
    add_solar_indicator_2d(
        ax, vars.get("_render_solar_azimuth_deg"), vars.get("_render_solar_altitude_deg"),
        corner="upper-right",
    )
    
    # Dibujar elementos del modelo
    #
    # CAMBIOS:
    # - Los árboles ahora se dibujan con un tamaño proporcional a su
    #   radio de copa real (antes todos los puntos eran del mismo
    #   tamaño fijo, sin relación con el radio_copa que sí se usa para
    #   calcular la sombra — visualmente no se podía distinguir un
    #   árbol chico de uno grande).
    # - Se agrega el dibujo de estructuras tipo "Galeria", que antes no
    #   se dibujaban en absoluto pese a que sí proyectan sombra en
    #   calcular_sombra_estructuras(). Un usuario podía agregar una
    #   galería, ver que afecta el cálculo, y no verla nunca en pantalla.
    if vars['arboles']:
        for idx, arbol in enumerate(vars['arboles']):
            draw_canopy_2d(
                ax, arbol, facecolor=color_copa(getattr(arbol, "especie", "")),
                edgecolor="darkgreen", alpha=0.68, zorder=6,
                label="Árboles" if idx == 0 else None,
            )

    for estructura in vars['estructuras']:
        if estructura.tipo == 'Sendero':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1,
                estructura.y2 - estructura.y1,
                color='gray', alpha=0.3,
                label=f"Sendero ({estructura.material})"
            ))
        elif estructura.tipo == 'Pared':
            ax.plot([estructura.x1, estructura.x2],
                [estructura.y1, estructura.y2],
                color='black', linewidth=2,
                label=f"Pared ({estructura.material})")
        elif estructura.tipo == 'Galeria':
            ax.add_patch(plt.Rectangle(
                (estructura.x1, estructura.y1),
                estructura.x2 - estructura.x1,
                estructura.y2 - estructura.y1,
                color='saddlebrown', alpha=0.35, hatch='//',
                label=f"Galería ({estructura.material})"
            ))
    
    # Configuración adicional del gráfico
    ax.set_title(f'Distribución de temperatura superficial\n{surface_model_label}')
    ax.set_xlabel(f'Distancia ({distance_unit})')
    ax.set_ylabel(f'Distancia ({distance_unit})')
    # CAMBIO: la leyenda estaba comentada — las etiquetas 'Árboles',
    # 'Pared (...)', 'Galería (...)', etc. se definían en cada elemento
    # pero nunca se mostraban en pantalla. Se activa con deduplicación
    # (si hay 5 paredes del mismo material, sale una sola entrada).
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        vistos = dict(zip(labels, handles))
        ax.legend(vistos.values(), vistos.keys(), loc='upper right', fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Información técnica
    info_text = (
        f"Parámetros actuales:\n"
        f"Hora: { vars['hora'].get():.1f}\n"
        f"Radiación solar: {I_sol:.1f} W/m²\n"
        f"Viento: { vars['viento'].get()}\n"
        f"Temp ambiente: {(app_instance.convert_temperature_for_display(T_amb) if app_instance else T_amb):.1f} {temp_unit}\n"
        f"Superficie: {surface_model_label}"
    )
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    
    # Conectar eventos
    #canvas.mpl_connect('button_press_event', lambda e: manejar_click(e, app)) 
    canvas.mpl_connect('button_press_event', lambda e: manejar_click(e, vars.get('_app_instance')))
    #canvas.mpl_connect('button_press_event',  manejar_click)
    canvas.draw()
    
    # Actualizar variables de estado
    vars['_update_required'] = False
    vars["X"] = X
    vars["Y"] = Y
    vars["T"] = T
    # v36 fase 1: conservar el estado científico del último cuadro para
    # construir una secuencia diurna sin recalcular durante la reproducción.
    vars["_last_shadow"] = np.asarray(sombra_total, dtype=np.float32).copy()
    vars["_last_meta"] = {
        "hora": float(vars["hora"].get()),
        "dia": int(vars["dia"].get()),
        "I_sol": float(I_sol),
        "surface_model_label": surface_model_label,
        "solar_altitude_deg": float(np.degrees(theta_sol)),
        "solar_azimuth_deg": float(np.degrees(azimut_sol)),
    }
    return fig, ax, canvas
def angulo_solar(vars):
    return _angulo_solar(
        vars["lat"].get(), vars["lon"].get(), vars["dia"].get(),
        vars["hora"].get(), _huso_horas(vars),
    )

def azimut_solar(vars, theta_sol):
    return _azimut_solar(
        vars["lat"].get(), vars["lon"].get(), vars["dia"].get(),
        vars["hora"].get(), theta_sol, _huso_horas(vars),
    )

def temperatura_ambiente(vars):
    return _temperatura_ambiente(
        vars["hora"].get(), vars["T_min"].get(), vars["T_max"].get(),
    )

def coeficiente_conveccion(vars):
    return _calcular_coeficiente_conveccion(vars["viento"].get())

def calcular_sombra_arboles(vars, X, Y, theta_sol, azimut_sol):
    return _calcular_sombra_arboles(X, Y, vars.get('arboles', []), theta_sol, azimut_sol)

def calcular_sombra_estructuras(vars, X, Y, theta_sol, azimut_sol):
    return _sombra_estructuras(X, Y, vars.get('estructuras', []), theta_sol, azimut_sol)
def generar_3d(vars, frame=None):
    """Renderiza la escena 3D dentro del contenedor compartido 2D/3D.

    v29 reemplaza la ventana ``Toplevel`` de Matplotlib por el backend VTK
    embebido cuando está disponible. La función consume X/Y/T ya calculados
    y no modifica ninguna ecuación ni resultado científico.
    """
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return None

    app = vars.get("_app_instance")
    if frame is None and app is not None and hasattr(app, "_get_scene_view_frames"):
        _view2d, frame, notebook = app._get_scene_view_frames("diseno")
        notebook.select(frame)
    if frame is None:
        messagebox.showerror(
            "Vista 3D",
            "No se encontró el contenedor 3D embebido. Regenere el gráfico desde el Panel de Edición.",
        )
        return None

    try:
        return render_scene_3d(vars, frame, title="Vista 3D — Edición · sombra y temperatura")
    except Exception as exc:
        messagebox.showerror("Vista 3D", f"No se pudo generar la vista 3D:\n{exc}")
        return None

def guardar_como(vars, app):
    """Exporta una copia de la escena a una ubicación elegida por el usuario."""
    global archivo_actual
    filepath = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")]
    )
    if filepath:
        return guardar(vars, app, filepath=filepath, notify=True)
    return None


def guardar(vars, app, filepath=None, notify=True):
    """Guarda escena + parámetros del cálculo en un único Excel reproducible.

    Edición calcula hoy la temperatura con Tmin/Tmax (ciclo diario), incluso
    cuando la interfaz lateral está en modo simple. Por eso se registra
    ``modo_calculo=advanced``: al abrir este archivo en Modelo se reproduce
    exactamente la física usada para generar el gráfico de Edición.
    """
    global archivo_actual
    if filepath is not None:
        archivo_actual = str(filepath)
    if not archivo_actual:
        project = getattr(getattr(app, "project_manager", None), "current_project", None)
        if project is not None:
            archivo_actual = project.layout.edit_excel
        else:
            return guardar_como(vars, app)

    try:
        modo_ui = app.modo_edicion.get() if hasattr(app, "modo_edicion") else "advanced"
        save_scene_excel(
            archivo_actual,
            vars.get("arboles", []),
            vars.get("estructuras", []),
            vars,
            calculation_mode="advanced",
            origin="edicion",
            app=app,
            extra_parameters={
                "modo_ui_origen": modo_ui,
                "surface_model_mode": (app.surface_model_mode.get() if hasattr(app, "surface_model_mode") else "standard"),
                "ground_vegetation_fraction": getattr(app, "settings", {}).get("ground_vegetation_fraction", 0.50),
                "vegetation_water_availability": getattr(app, "settings", {}).get("vegetation_water_availability", 0.75),
                "canopy_water_availability": getattr(app, "settings", {}).get("canopy_water_availability", 0.75),
                "radiation_source_mode": getattr(getattr(app, "radiation_source_mode", None), "get", lambda: "clear_sky")(),
                "radiation_source_label": (getattr(app, "last_meteorology_data", None) or {}).get("source_label", ""),
                "radiation_quality": (getattr(app, "last_meteorology_data", None) or {}).get("quality", ""),
                "meteorology_csv": os.path.basename(getattr(app, "meteorology_series_path", "") or ""),
                "ghi_wm2": (getattr(app, "last_meteorology_data", None) or {}).get("ghi", ""),
                "dni_wm2": (getattr(app, "last_meteorology_data", None) or {}).get("dni", ""),
                "dhi_wm2": (getattr(app, "last_meteorology_data", None) or {}).get("dhi", ""),
            },
        )
        if hasattr(app, "last_edit_excel_path"):
            app.last_edit_excel_path = archivo_actual
        if notify:
            messagebox.showinfo(
                "Éxito",
                "Archivo guardado correctamente.\n\n"
                "Incluye Árboles, Estructuras y Parametros para reproducir el cálculo en Modelo."
            )
        return archivo_actual
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")
        return None


def abrir_archivo(vars, app, filepath=None):
    global archivo_actual
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

        # Archivos antiguos no tienen Parametros: en ese caso se conservan
        # los valores actuales de la interfaz, exactamente como antes.
        apply_parameters_to_vars(vars, libro.parametros)

        if hasattr(app, "modo_edicion") and libro.parametros.get("modo_ui_origen"):
            app.modo_edicion.set(str(libro.parametros["modo_ui_origen"]))
            try:
                app._toggle_edicion_mode()
            except Exception:
                pass

        if hasattr(app, "surface_model_mode") and libro.parametros.get("surface_model_mode"):
            mode = str(libro.parametros["surface_model_mode"]).lower()
            if mode in {"standard", "advanced", "advanced_vegetation"}:
                app.surface_model_mode.set(mode)

        if hasattr(app, "settings"):
            for key in ("ground_vegetation_fraction", "vegetation_water_availability", "canopy_water_availability"):
                if key in libro.parametros:
                    try:
                        app.settings[key] = float(libro.parametros[key])
                    except (TypeError, ValueError):
                        pass

        if libro.parametros.get("radiation_source_mode") and hasattr(app, "radiation_source_mode"):
            mode_rad = str(libro.parametros["radiation_source_mode"]).strip().lower()
            if mode_rad in {"clear_sky", "manual_measured", "manual_scenario", "observed_series"}:
                app.radiation_source_mode.set(mode_rad)
        met_name = str(libro.parametros.get("meteorology_csv", "") or "").strip()
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

        archivo_actual = filepath
        target_frame = getattr(app, "frame7", app.frame2)
        actualizar_grafico(vars, target_frame)
        messagebox.showinfo("Éxito", "Archivo cargado correctamente")
        return filepath
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
        return None
