import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import math

# Constantes físicas
sigma = 5.67e-8  # Constante de Stefan-Boltzmann
# variables
elemento_temporal = None

modo=None
archivo_actual = None 

# Clases de datos
class Material:
    def __init__(self,  alpha, epsilon):
        self.alpha = alpha
        self.epsilon = epsilon
class Arbol:
    def __init__(self,  x, y, h, rho_copa, radio_copa):
        self.x = x
        self.y = y
        self.h = h
        self.rho_copa = rho_copa
        self.radio_copa = radio_copa
class Estructura:
    def __init__( self, tipo, x1, y1, x2, y2, altura=0, opacidad=1, material=None):
        self.tipo = tipo
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
        self.altura = altura
        self.opacidad = opacidad
        self.material = material
# Materiales predefinidos
materiales = {
    "acero inoxidable": Material(alpha=0.3, epsilon=0.2),
    "aluminio": Material(alpha=0.2, epsilon=0.125),
    "madera tratada": Material(alpha=0.7, epsilon=0.85),
    "policarbonato": Material(alpha=0.85, epsilon=0.9),
    "Policarbonato (paneles)": Material(alpha=0.85, epsilon=0.9),
    "Hormigón": Material(alpha=0.9, epsilon=0.9),
    "PVC (estructuras ligeras)": Material(alpha=0.8, epsilon=0.925),
    "Fibra de vidrio": Material(alpha=0.85, epsilon=0.89),
    "Lámina de polietileno (HDPE)": Material(alpha=0.35, epsilon=0.925),
    "Vidrio templado": Material(alpha=0.85, epsilon=0.9),
    "Ladrillo cerámico": Material(alpha=0.88, epsilon=0.875),
    "Corrugado de hierro": Material(alpha=0.8, epsilon=0.25),
    "ETFE": Material(alpha=0.3, epsilon=0.9),
    "CLT (Madera laminada natural)": Material(alpha=0.7, epsilon=0.85),
    "Aerogel": Material(alpha=0.25, epsilon=0.925),
    "Tierra apisonada": Material(alpha=0.4, epsilon=0.9),
    "Paca de paja": Material(alpha=0.5, epsilon=0.9),
    "Corcho": Material(alpha=0.3, epsilon=0.9),
    "Fibra de carbono": Material(alpha=0.8, epsilon=0.75),
    "Chapa de Zinc": Material(alpha=0.7, epsilon=0.25),
    "Terracota": Material(alpha=0.7, epsilon=0.875),
    "Micelio (hongos)": Material(alpha=0.5, epsilon=0.9),
    "Plástico reciclado": Material(alpha=0.7, epsilon=0.925),
    "Lana de vidrio": Material(alpha=0.3, epsilon=0.9),
    "Caucho": Material(alpha=0.8, epsilon=0.925),
    "Malla de acero": Material(alpha=0.7, epsilon=0.2),
    "Geotextil": Material(alpha=0.4, epsilon=0.9),
    "Tablero de óxido de magnesio": Material(alpha=0.5, epsilon=0.9),
    "Ferrocemento": Material(alpha=0.7, epsilon=0.9),
    "Hempcrete": Material(alpha=0.4, epsilon=0.9),
    "Fotocerámica (Vidrio Fotovoltaico)": Material(alpha=0.3, epsilon=0.9),
    "Concreto Translúcido": Material(alpha=0.5, epsilon=0.9),
    "Materiales de Cambio de Fase (PCMs)": Material(alpha=0.45, epsilon=0.925),
    "Acero Corten": Material(alpha=0.7 , epsilon=0.7),
    "Composite Madera-Plástico": Material(alpha=1.0e-7, epsilon=0.9),
    "Pinturas Intumescentes": Material(alpha=0.4, epsilon=0.925),
    "Cobre (superficies antibacterianas)": Material(alpha=0.8, epsilon=0.315),
    "Espuma de Poliuretano": Material(alpha=0.3, epsilon=0.9),
    "Concreto Autocurativo": Material(alpha=0.6, epsilon=0.9),
    "Ladrillos de PET reciclado": Material(alpha=8.0e-8, epsilon=0.925),
    "concreto translucido": Material(alpha=0.5, epsilon=0.9),
    "asfalto": Material(alpha=0.95, epsilon=0.95),
    "cemento": Material(alpha=0.6, epsilon=0.9),
    "suelo":Material(alpha=0.4, epsilon=0.9)
}


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
def actualizar_fecha(var, fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        var.set(fecha.timetuple().tm_yday)
        actualizar_grafico(vars,frame)
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
            actualizar_grafico(app.vars, app.frame2)
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
            actualizar_grafico(app.vars,app.frame2)
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
            
            actualizar_grafico(vars, app.frame2)
            dialogo.destroy()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
    
    def eliminar():
        if messagebox.askyesno("Confirmar", "¿Eliminar este elemento?"):
            if arbol:
                vars['arboles'].remove(obj)
            else:
                vars['estructuras'].remove(obj)
            actualizar_grafico(vars, app.frame2)
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
    theta_sol =  angulo_solar(vars)
    I_sol =  vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
    
    # Cálculo de sombras
    sombra_arboles =  calcular_sombra_arboles(vars,X, Y, theta_sol)
    sombra_estruct =  calcular_sombra_estructuras(vars,X, Y, theta_sol)
    sombra_total = np.clip(sombra_arboles * (1 - sombra_estruct), 0, 1)
    
    # Configuración de materiales
    alpha = np.full_like(X, materiales["suelo"].alpha)
    epsilon = np.full_like(X, materiales["suelo"].epsilon)
    
    for estructura in  vars['estructuras']:
        if estructura.material.lower() in materiales:
            mat = materiales[estructura.material.lower()]
            mask = (X >= estructura.x1) & (X <= estructura.x2) & \
                (Y >= estructura.y1) & (Y <= estructura.y2)
            alpha[mask] = mat.alpha
            epsilon[mask] = mat.epsilon
    
    # Balance energético
    T_amb =  temperatura_ambiente(vars)
    q_solar = alpha * I_sol * sombra_total
    q_emitido = epsilon * sigma * (T_amb**4 -  vars["T_amb_base"].get()**4)
    h_c =  coeficiente_conveccion(vars)
    q_conveccion = h_c * (T_amb -  vars["T_amb_base"].get())
    
    # Cálculo final de temperatura
    T =  vars["T_amb_base"].get() + (q_solar - q_emitido - q_conveccion) / (h_c + epsilon * sigma)
    
    # Configuración de niveles para el contorno
    nivel_min = np.nanmin(T)
    nivel_max = np.nanmax(T)
    
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
    try:
        contorno = ax.contourf(X, Y, T, niveles, cmap='viridis', alpha=0.8)
        ax.contour(X, Y, T, niveles, colors='k', linewidths=0.5)
    except ValueError as e:
        messagebox.showerror("Error", f"Problema al generar el gráfico: {str(e)}")
        return
    
    # Barra de color
    cbar = fig.colorbar(contorno, ax=ax)
    cbar.set_label('Temperatura (K)', rotation=270, labelpad=20)
    
    # Dibujar elementos del modelo
    if  vars['arboles']:
        ax.scatter([a.x for a in  vars['arboles']], 
                [a.y for a in  vars['arboles']], 
                c='green', s=50, label='Árboles')
    
    for estructura in  vars['estructuras']:
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
    
    # Configuración adicional del gráfico
    ax.set_title('Distribución de Temperatura')
    #ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Información técnica
    info_text = (
        f"Parámetros actuales:\n"
        f"Hora: { vars['hora'].get():.1f}\n"
        f"Radiación solar: {I_sol:.1f} W/m²\n"
        f"Viento: { vars['viento'].get()}\n"
        f"Temp ambiente: {T_amb:.1f} K"
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
    delta = np.radians(23.45 * np.sin(np.radians((360/365)*( vars["dia"].get()-81))))
    phi = np.radians( vars["lat"].get())
    h = np.radians(15*( vars["hora"].get()-12) + ( vars["lon"].get()/15))
    return np.arcsin(np.sin(phi)*np.sin(delta) + np.cos(phi)*np.cos(delta)*np.cos(h))
def temperatura_ambiente(vars):
    return  vars["T_min"].get() + ( vars["T_max"].get() -  vars["T_min"].get()) * np.sin(np.pi* vars["hora"].get()/24)
def coeficiente_conveccion(vars):
    return {"nulo":5, "moderado":15, "fuerte":25}.get( vars["viento"].get(), 10)
def calcular_sombra_arboles(  vars,X, Y, theta_sol):
    sombra = np.ones_like(X)
    for arbol in  vars['arboles']:
        if theta_sol <= 0:
            continue
        radio_sombra = arbol.radio_copa / np.tan(theta_sol)
        distancia = np.sqrt((X - arbol.x)**2 + (Y - arbol.y)**2)
        sombra[distancia < radio_sombra] *= (1 - arbol.rho_copa)
    return sombra
def calcular_sombra_estructuras(vars,X, Y, theta_sol):
    sombra_total = np.zeros_like(X)
    for estructura in  vars['estructuras']:
        if estructura.tipo == 'Pared' and theta_sol > 0:
            longitud_sombra = estructura.altura / np.tan(theta_sol)
            x_sombra = estructura.x1 - longitud_sombra if np.cos(theta_sol) > 0 else estructura.x1 + longitud_sombra
            y_sombra = estructura.y1 - longitud_sombra if np.sin(theta_sol) > 0 else estructura.y1 + longitud_sombra
            mask = (X >= min(estructura.x1, x_sombra)) & (X <= max(estructura.x1, x_sombra)) & (Y >= min(estructura.y1, y_sombra)) & (Y <= max(estructura.y1, y_sombra))
            sombra_total[mask] += float(estructura.opacidad)
        elif estructura.tipo == 'Galeria':
            mask = (X >= estructura.x1) & (X <= estructura.x2) & (Y >= estructura.y1) & (Y <= estructura.y2)
            sombra_total[mask] += float(estructura.opacidad)
    return np.clip(sombra_total, 0, 1)
def generar_3d(vars):
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return
    
    ventana_3d = tk.Toplevel()
    ventana_3d.title("Vista 3D de Temperatura")
    ventana_3d.geometry("1000x800")
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    X =  vars["X"]
    Y =  vars["Y"]
    T =  vars["T"]
    
    surf = ax.plot_surface(X, Y, T, cmap='viridis', rstride=2, cstride=2, alpha=0.8)
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
    
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Temperatura (K)')
    ax.set_title('Distribución Térmica 3D')
    
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
def abrir_archivo(vars, app):
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
            actualizar_grafico(vars,app.frame2)
            messagebox.showinfo("Éxito", "Archivo cargado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
