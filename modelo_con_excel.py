import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import math
from tkinter import messagebox

# Constantes
sigma = 5.67e-8  # Constante de Stefan-Boltzmann
class Material:
    def __init__(self, alpha, epsilon):
        self.alpha = alpha
        self.epsilon = epsilon
class Arbol:
    def __init__(self, x, y, h, rho_copa, radio_copa):
        self.x = x
        self.y = y
        self.h = h
        self.rho_copa = rho_copa
        self.radio_copa = radio_copa
class Estructura:
    def __init__(self, tipo, x1, y1, x2, y2, altura=0, opacidad=1, material=None):
        self.tipo = tipo
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
        self.altura = altura
        self.opacidad = opacidad
        self.material = material
# Materiales predefinidos (valores promedio dentro de los rangos)
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
    "Ladrillos de PET reciclado": Material(alpha=0.95, epsilon=0.925),
    "concreto translucido": Material(alpha=0.5, epsilon=0.9),
    "asfalto": Material(alpha=0.95, epsilon=0.95),
    "cemento": Material(alpha=0.6, epsilon=0.9),
    "suelo":Material(alpha=0.4, epsilon=0.9)
}
def declinacion_solar(dia_del_año):
    return 23.45 * np.sin(np.radians((360 / 365) * (dia_del_año - 81)))
def angulo_solar(latitud, longitud, dia_del_año, hora_local):
    delta = np.radians(declinacion_solar(dia_del_año))
    phi = np.radians(latitud)
    h = np.radians(15 * (hora_local - 12) + (longitud / 15))
    sin_theta = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(h)
    return np.arcsin(sin_theta)
def azimut_solar(latitud, longitud, dia_del_año, hora_local, theta_sol):
    delta = np.radians(declinacion_solar(dia_del_año))
    phi = np.radians(latitud)
    h = np.radians(15 * (hora_local - 12) + (longitud / 15))
    cos_theta = np.cos(theta_sol)
    if cos_theta == 0:
        return 0.0
    sin_az = -np.sin(h) * np.cos(delta) / cos_theta
    cos_az = (np.sin(delta) - np.sin(theta_sol) * np.sin(phi)) / (cos_theta * np.cos(phi))
    return np.arctan2(sin_az, cos_az)
def temperatura_ambiente(hora_local, T_min, T_max):
    return T_min + (T_max - T_min) * np.sin(np.pi * hora_local / 24)
def calcular_sombra_arboles(X, Y, arboles, theta_sol, azimut_sol):
    sombra = np.ones_like(X)
    if theta_sol <= 0:
        return sombra
    tan_theta = np.tan(max(theta_sol, np.radians(2)))
    for arbol in arboles:
        longitud_sombra = arbol.h / tan_theta
        dx = -longitud_sombra * np.sin(azimut_sol)
        dy = -longitud_sombra * np.cos(azimut_sol)
        cx = arbol.x + dx
        cy = arbol.y + dy
        distancia = np.sqrt((X - cx)**2 + (Y - cy)**2)
        sombra[distancia < arbol.radio_copa] *= (1 - arbol.rho_copa)
    return sombra
def sombra_estructuras(X, Y, estructuras, theta_sol, azimut_sol):
    
    sombra_total = np.zeros_like(X)
    if theta_sol <= 0:
        return sombra_total
    tan_theta = np.tan(max(theta_sol, np.radians(2)))
    for estructura in estructuras:
        if estructura.tipo == 'Pared' and theta_sol > 0:
            longitud_sombra = estructura.altura / tan_theta
            dx = -longitud_sombra * np.sin(azimut_sol)
            dy = -longitud_sombra * np.cos(azimut_sol)
            x_min = min(estructura.x1, estructura.x2, estructura.x1 + dx, estructura.x2 + dx)
            x_max = max(estructura.x1, estructura.x2, estructura.x1 + dx, estructura.x2 + dx)
            y_min = min(estructura.y1, estructura.y2, estructura.y1 + dy, estructura.y2 + dy)
            y_max = max(estructura.y1, estructura.y2, estructura.y1 + dy, estructura.y2 + dy)
            mask = (X >= x_min) & (X <= x_max) & (Y >= y_min) & (Y <= y_max)
            sombra_total[mask] += float(estructura.opacidad)
        elif estructura.tipo == 'Galeria':
            mask = (X >= estructura.x1) & (X <= estructura.x2) & \
                   (Y >= estructura.y1) & (Y <= estructura.y2)
            
            sombra_total[mask] += float(estructura.opacidad)
    return np.clip(sombra_total, 0, 1)
def calcular_coeficiente_conveccion(viento):
    return {"nulo": 5, "moderado": 15, "fuerte": 25}.get(viento, 10)
def cargar_excel(vars):
    filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not filepath:
        return
    
    try:
        # Cargar árboles
        df_arboles = pd.read_excel(filepath, sheet_name='Árboles')
        # Convertir columnas numéricas
        numeric_cols_arboles = ['X', 'Y', 'Altura (m)', 'Densidad_copa (0-1)', 'Radio_copa (m)']
        df_arboles[numeric_cols_arboles] = df_arboles[numeric_cols_arboles].apply(pd.to_numeric, errors='coerce').fillna(0)
        vars['arboles'] = [
            Arbol(row['X'], row['Y'], row['Altura (m)'],
                  row['Densidad_copa (0-1)'], row['Radio_copa (m)']) 
            for _, row in df_arboles.iterrows()
        ]
        
        # Cargar estructuras
        df_estructuras = pd.read_excel(filepath, sheet_name='Estructuras')
        # Convertir columnas numéricas
        numeric_cols_estructuras = ['X_inicial', 'Y_inicial', 'X_final', 'Y_final', 'Altura (m)', 'Opacidad (0-1)']
        df_estructuras[numeric_cols_estructuras] = df_estructuras[numeric_cols_estructuras].apply(pd.to_numeric, errors='coerce')
        df_estructuras['Altura (m)'] = df_estructuras['Altura (m)'].fillna(0)
        df_estructuras['Opacidad (0-1)'] = df_estructuras['Opacidad (0-1)'].fillna(1)
        
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
        
        messagebox.showinfo("Éxito", "Datos cargados correctamente")
        vars['_update_required'] = True
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
def generar_grafico(vars, frame):
    if '_update_required' not in vars or not vars['_update_required']:
        return
    
    for widget in frame.winfo_children():
        widget.destroy()
    
    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Configuración del espacio
    x = y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)
    
    # Cálculos principales
    theta_sol = angulo_solar(vars["lat"].get(), vars["lon"].get(), vars["dia"].get(), vars["hora"].get())
    azimut_sol = azimut_solar(vars["lat"].get(), vars["lon"].get(), vars["dia"].get(), vars["hora"].get(), theta_sol)
    I_sol = vars["I_sol_base"].get() * max(0, np.sin(theta_sol))
    
    # Cálculo de sombras
    sombra_arboles = calcular_sombra_arboles(X, Y, vars.get('arboles', []), theta_sol, azimut_sol)
    sombra_estruct = sombra_estructuras(X, Y, vars.get('estructuras', []), theta_sol, azimut_sol)
    sombra_total = np.clip(sombra_arboles * (1 - sombra_estruct), 0, 1)
    debug_flag = vars.get("debug", False)
    debug = bool(debug_flag.get()) if hasattr(debug_flag, "get") else bool(debug_flag)
    if debug:
        print("Sombra estructuras min/max:", np.min(sombra_estruct), np.max(sombra_estruct))
    # Configuración de materiales
    alpha = np.full_like(X, materiales["suelo"].alpha)
    epsilon = np.full_like(X, materiales["suelo"].epsilon)
    
    for estructura in vars.get('estructuras', []):
        if estructura.material.lower() in materiales:
            mat = materiales[estructura.material.lower()]
            mask = (X >= estructura.x1) & (X <= estructura.x2) & \
                   (Y >= estructura.y1) & (Y <= estructura.y2)
            alpha[mask] = mat.alpha
            epsilon[mask] = mat.epsilon
    
    # Balance energético
    T_amb = temperatura_ambiente(vars["hora"].get(), vars["T_min"].get(), vars["T_max"].get())
    q_solar = alpha * I_sol * sombra_total
    h_c = calcular_coeficiente_conveccion(vars["viento"].get())
    h_r = 4 * epsilon * sigma * (T_amb**3)
    
    # Cálculo final de temperatura (balance estacionario linealizado)
    T = T_amb + q_solar / (h_c + h_r)
    finite_mask = np.isfinite(T)
    if not np.all(finite_mask):
        T = np.where(finite_mask, T, T_amb)
    # Guardar datos para 3D
    vars["X"] = X
    vars["Y"] = Y
    vars["T"] = T
    
    # Configuración del gráfico
    tmin = float(np.nanmin(T))
    tmax = float(np.nanmax(T))
    margin = 1.0  
    if debug:
        print("T min/max:", tmin, tmax)
        print("Sombra total min/max:", np.min(sombra_total), np.max(sombra_total))
        print("Radiación efectiva min/max:", np.min(q_solar), np.max(q_solar))
    if np.isclose(tmin, tmax):
        delta = max(margin, 0.01 * abs(tmin), 0.5)
        tmin_auto = tmin - delta
        tmax_auto = tmax + delta
    else:
        tmin_auto = tmin - margin
        tmax_auto = tmax + margin
    if tmin_auto >= tmax_auto:
        tmax_auto = tmin_auto + max(margin, 0.5)
    niveles = np.linspace(tmin_auto, tmax_auto, 20)
    niveles = np.unique(np.sort(niveles))
    if niveles.size < 2:
        delta = max(margin, 0.01 * abs(tmin))
        niveles = np.array([tmin_auto - delta, tmax_auto + delta])
        
    contorno = ax.contourf(X, Y, T, niveles, cmap='viridis', alpha=0.8)
    ax.contour(X, Y, T, niveles, colors='k', linewidths=0.5)  # Añadir líneas de contorno
    ax.set_title('Distribución de temperatura', fontsize=12, pad=10)
    fig.colorbar(contorno, ax=ax).set_label('Temperatura (K)', rotation=270, labelpad=20)
    ax.contour(X, Y, T, niveles, colors='black', linewidths=1.5)
    if debug:
        print(f"Min T: {np.nanmin(T)}, Max T: {np.nanmax(T)}")

    # Dibujar elementos
    if 'arboles' in vars:
        ax.scatter([a.x for a in vars['arboles']],[a.y for a in vars['arboles']],c='green', s=50, label='Árboles')
    
    if 'estructuras' in vars:
        for estructura in vars['estructuras']:
            if estructura.tipo == 'Sendero':
                ax.add_patch(plt.Rectangle((estructura.x1, estructura.y1), estructura.x2 - estructura.x1,estructura.y2 - estructura.y1,color='gray', alpha=0.3, label=estructura.material))
            elif estructura.tipo == 'Pared':
                ax.plot([estructura.x1, estructura.x1], [estructura.y1, estructura.y2], color='black', linewidth=2)
    
    ax.set_title('Distribución de Temperatura')
    ax.legend()
    
    # Función para manejar clics
    def on_click(event):
        if event.inaxes != ax:
            return
        
        # Buscar árboles
        if 'arboles' in vars:
            for arbol in vars['arboles']:
                if math.dist((event.xdata, event.ydata), (arbol.x, arbol.y)) < 5:
                    editar_elemento(vars, arbol=arbol)
                    temp_sombra = T[int(arbol.y), int(arbol.x)]
                    detalles = (
                        f"Árbol en ({arbol.x}, {arbol.y})\n"
                        f"Temperatura: {temp_sombra:.2f} K\n"
                        f"Altura: {arbol.h} m\n"
                        f"Densidad copa: {arbol.rho_copa}"
                    )
                    ax.set_title(detalles)
                    fig.canvas.draw_idle()
                    return
        
        # Buscar estructuras
        if 'estructuras' in vars:
            for estructura in vars['estructuras']:
                if (estructura.x1 <= event.xdata <= estructura.x2 and estructura.y1 <= event.ydata <= estructura.y2):
                    editar_elemento(vars, estructura=estructura)
                    return


    # Información de aportes energéticos
    info_text = (
        f"Aportes energéticos:\n"
        f"Radiación solar: {q_solar.mean():.1f} W/m²\n"
        f"Coef. convección: {h_c:.1f} W/m²K\n"
        f"Coef. radiativo: {h_r.mean():.1f} W/m²K"
    )
    ax.text(0.05, 0.95, info_text, transform=ax.transAxes, 
            bbox=dict(facecolor='white', alpha=0.8), verticalalignment='top')   
    canvas.mpl_connect('button_press_event', on_click)
    canvas.draw()
    for widget in frame.winfo_children():
        widget.destroy()
    FigureCanvasTkAgg(fig, master=frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)
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
        },
    }    
def editar_elemento(vars, arbol=None, estructura=None):
    dialog = tk.Toplevel()
    dialog.title("Editar Elemento")
    dialog.geometry("300x400")
    
    entries = {}
    if arbol:
        fields = [
            ('X', arbol.x),
            ('Y', arbol.y),
            ('Altura (m)', arbol.h),
            ('Densidad Copa', arbol.rho_copa),
            ('Radio Copa', arbol.radio_copa)
        ]
    elif estructura:
        fields = [
            ('X1', estructura.x1),
            ('Y1', estructura.y1),
            ('X2', estructura.x2),
            ('Y2', estructura.y2),
            ('Altura (m)', estructura.altura),
            ('Opacidad', estructura.opacidad),
            ('Material', estructura.material)
        ]
    
    for i, (label, value) in enumerate(fields):
        ttk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=2)
        entry = ttk.Entry(dialog)
        entry.insert(0, str(value))
        entry.grid(row=i, column=1, padx=5, pady=2)
        entries[label] = entry
    
    def guardar_cambios():
        try:
            if arbol:
                arbol.x = float(entries['X'].get())
                arbol.y = float(entries['Y'].get())
                arbol.h = float(entries['Altura (m)'].get())
                arbol.rho_copa = float(entries['Densidad Copa'].get())
                arbol.radio_copa = float(entries['Radio Copa'].get())
            elif estructura:
                estructura.x1 = float(entries['X1'].get())
                estructura.y1 = float(entries['Y1'].get())
                estructura.x2 = float(entries['X2'].get())
                estructura.y2 = float(entries['Y2'].get())
                estructura.altura = float(entries['Altura (m)'].get())
                estructura.opacidad = float(entries['Opacidad'].get())
                estructura.material = entries['Material'].get()
            
            dialog.destroy()
            vars['_update_required'] = True
            generar_grafico(vars, vars['graph_frame'])
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
    ttk.Button(dialog, text="Guardar", command=guardar_cambios).grid(
        row=len(fields)+1, columnspan=2, pady=10)
def generar_3d(vars):
    if "T" not in vars or "X" not in vars or "Y" not in vars:
        messagebox.showerror("Error", "Primero genere el gráfico 2D")
        return
    
    ventana_3d = tk.Toplevel()
    ventana_3d.title("Vista 3D de Temperatura")
    ventana_3d.geometry("1000x800")
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    X = vars["X"]
    Y = vars["Y"]
    T = vars["T"]
    
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
def cargar_preset(config, vars):
    presets = {
        "verano": {"T_min": 298, "T_max": 315, "I_sol_base": 1000, "dia": 180},
        "invierno": {"T_min": 275, "T_max": 290, "I_sol_base": 600, "dia": 355},
        "soleado": {"I_sol_base": 1200},
        "nublado": {"I_sol_base": 300}
    }
    for k, v in presets[config].items():
        vars[k].set(v)
