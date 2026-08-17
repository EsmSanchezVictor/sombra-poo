import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import math
from core.scene_objects import adaptar_objetos_escena
from plot_style import CMAP_TEMPERATURA

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
    asignar_materiales_grilla,
    angulo_solar as _angulo_solar,
    azimut_solar as _azimut_solar,
    temperatura_ambiente as _temperatura_ambiente,
    calcular_coeficiente_conveccion as _calcular_coeficiente_conveccion,
    calcular_sombra_arboles as _calcular_sombra_arboles,
    sombra_estructuras as _sombra_estructuras,
)


def _huso_horas(vars):
    huso = vars.get("huso_horas")
    return huso.get() if hasattr(huso, "get") else huso


def crear_area_grafico(vars,frame,app):
    frame.grid(row=1, column=1, sticky="nsew")
    actualizar_grafico(vars,frame)
    # Crear figura y canvas
    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    actualizar_grafico(vars, frame)
    #canvas.mpl_connect('button_press_event', lambda e: manejar_click(e, app))
    return fig, ax, canvas  # Devuelve estos valores correctamente    
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
def actualizar_fecha(var,frame, fecha_str): #ojo con el frame
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        var.set(fecha.timetuple().tm_yday)
        actualizar_grafico(vars, frame)
    except ValueError:
        messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
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
def mostrar_dialogo_arbol(x, y,app):
    dialogo = tk.Toplevel()
    dialogo.title("Nuevo Árbol")
    
    campos = [
        ('Altura (m):', '5'),
        ('Densidad Copa (0-1):', '0.8'),
        ('Radio Copa (m):', '3')
    ]
    
    entries = {}
    for i, (label, valor) in enumerate(campos):
        ttk.Label(dialogo, text=label).grid(row=i, column=0)
        entry = ttk.Entry(dialogo)
        entry.insert(0, valor)
        entry.grid(row=i, column=1)
        entries[label] = entry
    
    def guardar():
        try:
            nuevo_arbol = Arbol(
                x=x,
                y=y,
                h=float(entries['Altura (m):'].get()),
                rho_copa=float(entries['Densidad Copa (0-1):'].get()),
                radio_copa=float(entries['Radio Copa (m):'].get())
            )
            app.vars['arboles'].append(nuevo_arbol)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
            #actualizar_grafico(app.vars, app.frame2)
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(app.vars, target_frame)
            dialogo.destroy()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
            
    ttk.Button(dialogo, text="Guardar", command=guardar).grid(row=len(campos), columnspan=2)
def mostrar_dialogo_estructura(x1, y1, x2, y2,app):
    dialogo = tk.Toplevel()
    dialogo.title("Nueva Estructura")
    
    campos = [
        ('Tipo:', ['Pared', 'Galeria', 'Sendero']),
        ('Altura (m):', '0'),
        ('Opacidad (0-1):', '1'),
        ('Material:', list(materiales.keys()))
    ]
    
    entries = {}
    for i, (label, opciones) in enumerate(campos):
        ttk.Label(dialogo, text=label).grid(row=i, column=0)
        if isinstance(opciones, list):
            entry = ttk.Combobox(dialogo, values=opciones)
            entry.current(0)
        else:
            entry = ttk.Entry(dialogo)
            entry.insert(0, opciones)
        entry.grid(row=i, column=1)
        entries[label] = entry
    
    def guardar():
        try:
            nueva_estructura = Estructura(
                tipo=entries['Tipo:'].get(),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                altura=float(entries['Altura (m):'].get()),
                opacidad=float(entries['Opacidad (0-1):'].get()),
                material=entries['Material:'].get()
            )
            app.vars['estructuras'].append(nueva_estructura)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
            #actualizar_grafico(app.vars,app.frame2)
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(app.vars, target_frame)
            dialogo.destroy()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
            
    ttk.Button(dialogo, text="Guardar", command=guardar).grid(row=len(campos), columnspan=2)
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
    dialogo = tk.Toplevel()
    dialogo.title("Editar Elemento")
    
    if arbol:
        campos = [
            ('X:', arbol.x),
            ('Y:', arbol.y),
            ('Altura (m):', arbol.h),
            ('Densidad Copa:', arbol.rho_copa),
            ('Radio Copa:', arbol.radio_copa)
        ]
        obj = arbol
    else:
        campos = [
            ('X1:', estructura.x1),
            ('Y1:', estructura.y1),
            ('X2:', estructura.x2),
            ('Y2:', estructura.y2),
            ('Altura (m):', estructura.altura),
            ('Opacidad:', estructura.opacidad),
            ('Material:', estructura.material)
        ]
        obj = estructura
    
    entries = {}
    for i, (label, valor) in enumerate(campos):
        ttk.Label(dialogo, text=label).grid(row=i, column=0)
        if label == 'Material:':
            entry = ttk.Combobox(dialogo, values=list(materiales.keys()))
            entry.set(valor)
        else:
            entry = ttk.Entry(dialogo)
            entry.insert(0, str(valor))
        entry.grid(row=i, column=1)
        entries[label] = entry
    
    def guardar():
        try:
            if arbol:
                arbol.x = float(entries['X:'].get())
                arbol.y = float(entries['Y:'].get())
                arbol.h = float(entries['Altura (m):'].get())
                arbol.rho_copa = float(entries['Densidad Copa:'].get())
                arbol.radio_copa = float(entries['Radio Copa:'].get())
            else:
                estructura.x1 = float(entries['X1:'].get())
                estructura.y1 = float(entries['Y1:'].get())
                estructura.x2 = float(entries['X2:'].get())
                estructura.y2 = float(entries['Y2:'].get())
                estructura.altura = float(entries['Altura (m):'].get())
                estructura.opacidad = float(entries['Opacidad:'].get())
                estructura.material = entries['Material:'].get()
            
            #actualizar_grafico(vars, app.frame2)
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(vars, target_frame)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()
            dialogo.destroy()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
    
    def eliminar():
        if messagebox.askyesno("Confirmar", "¿Eliminar este elemento?"):
            if arbol:
                vars['arboles'].remove(obj)
            else:
                vars['estructuras'].remove(obj)
            #actualizar_grafico(vars, app.frame2)
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(vars, target_frame)
            if hasattr(app, "mark_dirty"):
                app.mark_dirty()            
            dialogo.destroy()
    
    ttk.Button(dialogo, text="Guardar", command=guardar).grid(row=len(campos)+1, column=0)
    ttk.Button(dialogo, text="Eliminar", command=eliminar).grid(row=len(campos)+1, column=1)
def actualizar_grafico(vars, frame):
    #if not force and not self.vars['_update_required']:
    #    return
    
    # Limpiar frame del gráfico
    for widget in frame.winfo_children():
        widget.destroy()
    
    # Configuración del espacio de simulación
    x = y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)
    
    # Cálculos principales
    theta_sol = angulo_solar(vars)
    azimut_sol = azimut_solar(vars, theta_sol)
    I_sol = vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
    
    # Cálculo de sombras
    vars["_scene_objects"] = adaptar_objetos_escena(vars.get("arboles", []), vars.get("estructuras", []))    
    sombra_arboles = calcular_sombra_arboles(vars, X, Y, theta_sol, azimut_sol)
    sombra_estruct = calcular_sombra_estructuras(vars, X, Y, theta_sol, azimut_sol)
    sombra_total = np.clip(sombra_arboles * (1 - sombra_estruct), 0, 1)
    
    # Configuración de materiales
    # CORRECCIÓN: antes el material se comparaba en minúsculas contra un
    # dict con claves en mayúsculas ("Hormigón") y casi nunca matcheaba,
    # cayendo en 'suelo' en silencio. asignar_materiales_grilla usa el
    # índice normalizado MATERIALES_LOWER y avisa si no reconoce el nombre.
    alpha, epsilon = asignar_materiales_grilla(X, Y, vars.get('estructuras', []))
    
    # Balance energético
    T_amb = temperatura_ambiente(vars)
    q_solar = alpha * I_sol * sombra_total
    h_c = coeficiente_conveccion(vars)
    h_r = 4 * epsilon * sigma * (T_amb**3)
    
    # Cálculo final de temperatura (balance estacionario linealizado)
    T = T_amb + q_solar / (h_c + h_r)
    
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
    fig, ax = plt.subplots(figsize=(8, 6))
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
    cbar.set_label(f'Temperatura ({temp_unit})')
    
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
        tamanos = [max(20, (a.radio_copa ** 2) * 8) for a in vars['arboles']]
        ax.scatter([a.x for a in vars['arboles']],
                [a.y for a in vars['arboles']],
                c='green', s=tamanos, alpha=0.6, edgecolors='darkgreen',
                label='Árboles')

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
    ax.set_title('Distribución de Temperatura')
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
        f"Temp ambiente: {(app_instance.convert_temperature_for_display(T_amb) if app_instance else T_amb):.1f} {temp_unit}"
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
def generar_3d(vars):
    """Vista 3D simplificada de la escena: temperatura como mapa de color
    sobre el plano del suelo + árboles/estructuras como objetos con su
    altura real.

    CAMBIOS respecto a la versión original:
    - Antes se dibujaba T (temperatura, en Kelvin) como una SUPERFICIE
      ondulada en el eje Z, con el eje Z además invertido. Eso no se
      parece a cómo se lee un plano de sombra real y no tenía ninguna
      relación visual con los árboles/estructuras que el usuario coloca
      en el modo edición — de hecho, generar_3d() no los dibujaba en
      absoluto.
    - Ahora el eje Z representa ALTURA REAL (metros) de los objetos de
      la escena, y la temperatura se muestra como un mapa de color
      proyectado sobre el plano del suelo (contourf con zdir='z',
      offset=0) — el mismo lenguaje visual que la imagen de referencia
      del usuario (curvas de temperatura sobre el terreno + objetos
      3D simples encima), pero sin geometría fotorrealista.
    - Los árboles se dibujan como un tallo + una copa esférica simple,
      del tamaño real de su radio de copa. Las estructuras tipo Pared
      se dibujan como un panel vertical de su altura real; Galería y
      Sendero como una franja horizontal a nivel de piso/techo.
    - Usa la misma paleta (CMAP_TEMPERATURA) que el resto de la app en
      vez de 'viridis' suelto, para que el mapa de color se lea igual
      en todas las vistas del proyecto.
    """
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return

    ventana_3d = tk.Toplevel()
    ventana_3d.title("Vista 3D simplificada")
    ventana_3d.geometry("1000x800")

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    X = vars["X"]
    Y = vars["Y"]
    T = vars["T"]

    app_instance = vars.get('_app_instance')
    temp_unit = app_instance.get_temperature_unit_symbol() if app_instance else "K"
    T_display = app_instance.convert_temperature_for_display(T) if app_instance else T

    # --- Mapa de temperatura proyectado sobre el plano del suelo (z=0) ---
    nivel_min, nivel_max = float(np.nanmin(T_display)), float(np.nanmax(T_display))
    if not np.isfinite(nivel_min) or not np.isfinite(nivel_max) or nivel_min == nivel_max:
        niveles = 10
    else:
        niveles = np.linspace(nivel_min, nivel_max, 20)

    piso = ax.contourf(X, Y, T_display, niveles, zdir='z', offset=0,
                        cmap=CMAP_TEMPERATURA, alpha=0.95)
    cbar = fig.colorbar(piso, ax=ax, shrink=0.6, aspect=12, pad=0.08)
    cbar.set_label(f"Temperatura ({temp_unit})")
    # Etiquetas de extremos al estilo "Warmest/Coolest" de la referencia,
    # además de los números — más rápido de leer de un vistazo.
    cbar.ax.text(0.5, 1.02, "Más cálido", transform=cbar.ax.transAxes,
                 ha='center', va='bottom', fontsize=8)
    cbar.ax.text(0.5, -0.02, "Más fresco", transform=cbar.ax.transAxes,
                 ha='center', va='top', fontsize=8)

    # --- Árboles: tallo + copa esférica simple, tamaño real ---
    arboles = vars.get('arboles', [])
    if arboles:
        ax.scatter(
            [a.x for a in arboles], [a.y for a in arboles], [a.h for a in arboles],
            s=[max(30, (a.radio_copa ** 2) * 25) for a in arboles],
            c='forestgreen', alpha=0.85, depthshade=True,
            edgecolors='darkgreen', label='Árboles',
        )
        for a in arboles:
            ax.plot([a.x, a.x], [a.y, a.y], [0, a.h], color='saddlebrown', linewidth=2)

    # --- Estructuras: panel vertical (Pared) o franja horizontal (Galería/Sendero) ---
    estructuras = vars.get('estructuras', [])
    for e in estructuras:
        color = {'Pared': '0.3', 'Galeria': 'saddlebrown', 'Sendero': 'gray'}.get(e.tipo, '0.5')
        if e.tipo == 'Pared':
            altura = max(e.altura, 0.1)
            panel = [[
                (e.x1, e.y1, 0), (e.x2, e.y2, 0),
                (e.x2, e.y2, altura), (e.x1, e.y1, altura),
            ]]
            ax.add_collection3d(Poly3DCollection(panel, facecolor=color, alpha=0.7, edgecolor='black'))
        else:
            z_nivel = e.altura if e.tipo == 'Galeria' else 0.05
            franja = [[
                (e.x1, e.y1, z_nivel), (e.x2, e.y1, z_nivel),
                (e.x2, e.y2, z_nivel), (e.x1, e.y2, z_nivel),
            ]]
            ax.add_collection3d(Poly3DCollection(franja, facecolor=color, alpha=0.5))

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Altura (m)')
    ax.set_title('Vista 3D simplificada — sombra y temperatura')
    ax.view_init(elev=42, azim=-60)  # ángulo isométrico, similar a la referencia
    if arboles or estructuras:
        ax.legend(loc='upper left', fontsize=8)

    canvas = FigureCanvasTkAgg(fig, master=ventana_3d)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, ventana_3d)
    toolbar.update()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
def guardar_como(vars, app):
    global archivo_actual
    filepath = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")]
    )
    if filepath:
        archivo_actual = filepath
        guardar(vars, app)
def guardar(vars, app):
    global archivo_actual
    if not  archivo_actual:
        guardar_como(vars,app)
        return
    
    try:
        df_arboles = pd.DataFrame([{
            'X': a.x,
            'Y': a.y,
            'Altura (m)': a.h,
            'Densidad_copa (0-1)': a.rho_copa,
            'Radio_copa (m)': a.radio_copa
        } for a in  vars['arboles']])
        
        df_estructuras = pd.DataFrame([{
            'Tipo': e.tipo,
            'X_inicial': e.x1,
            'Y_inicial': e.y1,
            'X_final': e.x2,
            'Y_final': e.y2,
            'Altura (m)': e.altura,
            'Opacidad (0-1)': e.opacidad,
            'Material': e.material
        } for e in  vars['estructuras']])
        
        with pd.ExcelWriter( archivo_actual) as writer:
            df_arboles.to_excel(writer, sheet_name='Árboles', index=False)
            df_estructuras.to_excel(writer, sheet_name='Estructuras', index=False)
        
        messagebox.showinfo("Éxito", "Archivo guardado correctamente")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")
def abrir_archivo(vars, app, filepath=None):
    if filepath is None:
        filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if filepath:
        try:
            df_arboles = pd.read_excel(filepath, sheet_name='Árboles')
            vars['arboles'] = [
                Arbol(row['X'], row['Y'], row['Altura (m)'],row['Densidad_copa (0-1)'], row['Radio_copa (m)']) 
                for _, row in df_arboles.iterrows()
            ]
            
            df_estructuras = pd.read_excel(filepath, sheet_name='Estructuras')
            vars['estructuras'] = []
            for _, row in df_estructuras.iterrows():
                estructura = Estructura(
                    tipo=row['Tipo'],
                    x1=row['X_inicial'],
                    y1=row['Y_inicial'],
                    x2=row['X_final'],
                    y2=row['Y_final'],
                    altura=row['Altura (m)'],
                    opacidad=row['Opacidad (0-1)'],
                    material=row['Material']
                )
                vars['estructuras'].append(estructura)
            
            archivo_actual = filepath
            #actualizar_grafico(vars,app.frame2)
            target_frame = getattr(app, "frame7", app.frame2)
            actualizar_grafico(vars, target_frame)
            messagebox.showinfo("Éxito", "Archivo cargado correctamente")
            return filepath
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
            return None
    return None
