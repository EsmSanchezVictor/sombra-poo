from datetime import datetime
from io import BytesIO
import csv
import os
import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib import cm
import math
from tkinter import filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from shape_selection import ShapeSelector
from image_processor import ImageProcessor
from save_pdf import PDFReportGenerator
from shadow_temp import Temperatura
from temp_graph import TemperatureGraph
#from mouse_pixel_value  import MouseHoverPixelValueWithTooltip
from utils import export_to_excel
import diseño as design
import modelo_con_excel as modelo
from DatasetSaver import DatasetSaver
from tkinter import messagebox
from PIL import Image, ImageTk

class App:
    def __init__(self, root):

        self.root = root
        self.root.title("Distribución Grid")
        self.modo = None  # 'arbol', 'estructura'
        self.elemento_temporal = None

        """ # Crear frames
        self.frame0 = tk.Frame(root, bg="magenta", width=100, height=3)
        self.frame1 = tk.Frame(self.root, bg="aqua", width=100, height=100)
        self.frame2 = tk.Frame(root, bg="green", width=100, height=100)
        self.frame3 = tk.Frame(root, bg="blue", width=100, height=100)
        self.frame4 = tk.Frame(root, bg="yellow", width=100, height=100)
        self.frame5 = tk.Frame(root, bg="purple", width=100, height=100)
        self.frame6 = tk.Frame(root, bg="orange", width=100, height=1) """
        # Paleta de colores suave para toda la interfaz
        self.palette = {
            "background": "#f5f7fb",
            "panel": "#ffffff",
            "accent": "#e6ebf5",
            "border": "#d6dce8",
        }

        self.root.configure(bg=self.palette["background"])

        # Crear frames principales con una estética consistente
        self.frame0 = tk.Frame(
            root,
            bg=self.palette["accent"],
            width=100,
            height=3,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame1 = tk.Frame(
            self.root,
            bg=self.palette["background"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame2 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame3 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame4 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame5 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame6 = tk.Frame(
            root,
            bg=self.palette["accent"],
            width=100,
            height=1,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame7 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame8 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame9 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame10 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame11 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame12 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame13 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )
        self.frame14 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )

        # Ubicar frames
        self.frame0.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.frame1.grid(row=1, column=0, rowspan=3, sticky="nsew")
        self.frame2.grid(row=1, column=1, sticky="nsew")
        self.frame3.grid(row=1, column=2, sticky="nsew")
        self.frame4.grid(row=2, column=1, sticky="nsew")
        self.frame5.grid(row=2, column=2, sticky="nsew")
        self.frame6.grid(row=3, column=1, columnspan=2, sticky="nsew")
        self.frame7.grid(row=1, column=1, sticky="nsew")
        self.frame8.grid(row=1, column=2, sticky="nsew")
        self.frame9.grid(row=2, column=1, sticky="nsew")
        self.frame10.grid(row=2, column=2, sticky="nsew")
        self.frame11.grid(row=1, column=1, sticky="nsew")
        self.frame12.grid(row=1, column=2, sticky="nsew")
        self.frame13.grid(row=2, column=1, sticky="nsew")
        self.frame14.grid(row=2, column=2, sticky="nsew")
        self.frame7.grid_remove()
        self.frame8.grid_remove()
        self.frame9.grid_remove()
        self.frame10.grid_remove()
        self.frame11.grid_remove()
        self.frame12.grid_remove()
        self.frame13.grid_remove()
        self.frame14.grid_remove()
        
        # Configurar pesos de las filas y columnas
        root.grid_rowconfigure(0, weight=0)
        root.grid_rowconfigure(1, weight=1)
        root.grid_rowconfigure(3, weight=0)
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_columnconfigure(2, weight=1)

        
        # Inicializamos el procesador de imágenes y el selector de forma
        self.image_processor = ImageProcessor()
        self.shape_selector = ShapeSelector(self) 
        self.dataset_saver = DatasetSaver(self)
        self.porcentaje_sombra = None
        self.tmrt_result = None
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.original_rgb = None
        self._tmrt_hover_cid = None
        self._tmrt_hover_canvas = None
        self._tmrt_hover_annotation = None
        self._shadow_hover_cid = None
        self._shadow_hover_canvas = None
        self._shadow_hover_annotation = None
        self.porcentaje_sombra = None
        self.tmrt_result = None
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.original_rgb = None
        self.mouse_hover_pixel_value = None
        self.curva_frame = None
        self.curva_label = None
        self.curva_photo = None
        self.curva_img_pil_original = None
        #self.frame1 = frame1
        self.panel_width =  min(int(self.frame1.winfo_screenwidth() / 6), self.frame1.winfo_width())

        # Crear un frame para los iconos (botones), inicialmente vertical a la izquierda
        """self.icon_frame = tk.Frame(self.frame1)"""
        self.icon_frame = tk.Frame(self.frame1, bg=self.palette["background"])
        self.icon_frame.grid(row=0, column=0, sticky="ns")

        # Cargar las imágenes para los botones (deben ser archivos PNG)
        self.images = [
            tk.PhotoImage(file="test/imagen/fiebre (3).png"),
            tk.PhotoImage(file="test/imagen/sombra (3).png"),
            tk.PhotoImage(file="test/imagen/config (3).png"),
            tk.PhotoImage(file="test/imagen/vista-3d (3).png")
        ]

        # Lista de botones que representan los iconos
        self.buttons = []
        self.panel_frames = []

        # Crear 4 botones que actuarán como iconos y 4 paneles
        for i in range(4):
            btn = tk.Button(self.icon_frame, image=self.images[i], command=lambda i=i: self.toggle_panel(i), relief=tk.FLAT,
                            bg=self.frame1.cget('bg'))
            btn.grid(row=i, column=0, pady=0, padx=0, sticky="ew")
            self.buttons.append(btn)

        # Crear los paneles desplegables (inicialmente ocultos)
        for i in range(4):
            """panel = tk.Frame(self.frame1, bg="white", width=0, height=400)"""
            panel = tk.Frame(
                self.frame1,
                bg=self.palette["panel"],
                width=0,
                height=400,
                highlightbackground=self.palette["border"],
                highlightthickness=1,
                bd=0,
            )
            panel.place(x=0, y=0, relheight=1)
            panel.place_forget()
            self.panel_frames.append(panel)

        # Inicializar variable
        self.setup_variables()
        self.locations_data = self._load_locations_csv()
        # Calculadora Tmrt (se instancia cuando se calcula)
        self.temp_calculator = None
        # Otros atributos que tengas...
        self.curvas_nivel_creadas = False  # Bandera para saber si las curvas de nivel han sido creadas
        # Calculadora Tmrt (se instancia cuando se calcula)

    
        # Configurar los contenidos para cada panel
        self.setup_panel_1()
        self.setup_panel_2()
        self.setup_panel_3()
        self.setup_panel_4()

        # Para recordar cuál panel está abierto
        self.active_panel = None
        self.is_animating = False

        # Inicializar componentes
        self.setup_menu()
        self.setup_status_bar()
        self.resultados(self.frame4)
        self.temp_sombra(self.frame5)
        self.imagen(self.frame2)
        self.curva_de_nivel(self.frame3)
        self.activar_mouse()
        
    def activar_mouse(self):
        # Vincular eventos de mouse
        self.canvas1.mpl_connect('button_press_event', self.shape_selector.on_mouse_press)
        self.canvas1.mpl_connect('motion_notify_event', self.shape_selector.on_mouse_move)
        self.canvas1.mpl_connect('button_release_event', self.shape_selector.on_mouse_release)
    def setup_variables(self):
        """Inicializa las variables de control para la aplicación"""
        self.selection_type = tk.StringVar(value="Polígono")
        self.matriz_size = tk.IntVar(value=1024)
        self.drawing_mode = None
        self.img = None
        self.img_rgb = None
        self.area_calculo_done = False
        self.area_referencia_done = False
        self.entries =[]
        self.modo = None
        self.vars = self._build_vars()
        self.vars_modelo = self._build_vars()
        # Controles de parámetros
        self.controles = self._build_controles(self.vars)
        self.controles_modelo = self._build_controles(self.vars_modelo)
        self.simple_mode_var = tk.BooleanVar(value=True)
        self.simple_country_var = tk.StringVar()
        self.simple_city_var = tk.StringVar()
        self.simple_cloudiness_var = tk.StringVar(value="Despejado")
        self.simple_temp_c_var = tk.StringVar(value="25")
        
    def _build_vars(self):
        return {
            "T_amb_base": tk.DoubleVar(value=295),
            "I_sol_base": tk.DoubleVar(value=1000),
            "T_min": tk.DoubleVar(value=290),
            "T_max": tk.DoubleVar(value=310),
            "dia": tk.IntVar(value=180),
            "lat": tk.DoubleVar(value=40),
            "lon": tk.DoubleVar(value=-3),
            "hora": tk.DoubleVar(value=12),
            "humedad": tk.DoubleVar(value=0.5),
            "viento": tk.StringVar(value="moderado"),
            "arboles": [],
            "estructuras": [],
            "_update_required": True,
            "_app_instance":self,
        }
        # Controles de parámetros
        
    def _build_controles(self, vars_dict):
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
    def _load_locations_csv(self):
        data_path = os.path.join("data", "locations_ar.csv")
        if not os.path.exists(data_path):
            return {"error": "No se encontró data/locations_ar.csv"}
        countries = []
        cities_by_country = {}
        city_lookup = {}
        with open(data_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                country = row.get("country", "").strip()
                city = row.get("city", "").strip()
                if not country or not city:
                    continue
                countries.append(country)
                cities_by_country.setdefault(country, []).append(city)
                key = (country, city)
                city_lookup[key] = {
                    "lat": float(row.get("lat", 0)),
                    "lon": float(row.get("lon", 0)),
                    "tz": row.get("tz", "").strip(),
                    "province": row.get("province", "").strip(),
                    "kind": row.get("kind", "").strip(),
                }
        unique_countries = sorted(set(countries))
        for country in unique_countries:
            cities_by_country[country] = sorted(set(cities_by_country.get(country, [])))
        return {
            "countries": unique_countries,
            "cities_by_country": cities_by_country,
            "city_lookup": city_lookup,
        }
    def setup_panel_1(self):
        """Configura el contenido del Panel 1"""
        panel = self.panel_frames[0]
        
        labels = ["Temperatura ambiente (°C):", "Hora del día (0-23):", "Fecha (YYYY-MM-DD):", "Latitud:", "Longitud:"]
        self.entries = []
        self.entry_temp = None
        self.entry_time = None
        self.entry_date = None
        self.entry_lat = None
        self.entry_lon = None

        for label_text in labels:
            label = tk.Label(panel, text=label_text, bg=panel.cget("bg"), fg="black")
            label.pack(anchor="w", padx=20, pady=5)
            entry = tk.Entry(panel)
            entry.pack(anchor="w", padx=20, pady=5)
            self.entries.append(entry)
        
        self.entry_temp = self.entries[0]
        self.entry_time = self.entries[1]
        self.entry_date = self.entries[2]
        self.entry_lat = self.entries[3]
        self.entry_lon = self.entries[4]
        
        calculate_button = tk.Button(panel, text="Calcular temperatura en sombra", command=self.calculate_temperature_in_shade)
        calculate_button.pack(padx=20, pady=20)
    def setup_panel_2(self):
        """Configura el contenido del Panel 2"""
        panel = self.panel_frames[1]

        # Botone para cargar la imagen a analizar 
        cargar_imagen_button = tk.Button(panel, text="Cargar imagen",command=self.cargar_imagen, bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        cargar_imagen_button.pack(anchor="w",padx=20, pady=10)
        
        # Selección de tipo de área
        area_label = tk.Label(panel, text="Seleccione el tipo de área:", bg=panel.cget("bg"), fg="black")
        area_label.pack(anchor="w", padx=20, pady=10)

        selection_type = tk.StringVar(value="Rectángulo")  # Variable para seleccionar entre rectángulo y círculo
        self.rect_button = tk.Radiobutton(panel, text="Rectángulo", variable=selection_type, value="Rectángulo", bg=panel.cget("bg"), fg="black")
        self.rect_button.pack(anchor="w", padx=20)

        self.circ_button = tk.Radiobutton(panel, text="Círculo", variable=selection_type, value="Círculo", bg=panel.cget("bg"), fg="black")
        self.circ_button.pack(anchor="w", padx=20)

        self.circ_button = tk.Radiobutton(panel, text="Polígono", variable=selection_type, value="Polígono", bg=panel.cget("bg"), fg="black")
        self.circ_button.pack(anchor="w", padx=20)
        
        # Selección del tamaño de la matriz
        matrix_label = tk.Label(panel, text="Seleccione el tamaño de la matriz:", bg=panel.cget("bg"), fg="black")
        matrix_label.pack(anchor="w", padx=20, pady=10)

        matrix_size = ttk.Combobox(panel, values=[480, 640, 800, 1024])
        matrix_size.pack(anchor="w", padx=20, pady=5)

        # Botones de selección de área
        self.area_calc_button = tk.Button(panel, text="Seleccione área de cálculo",bg='blue',fg='white', command=self.shape_selector.select_area_calculo, state=tk.DISABLED)
        self.area_calc_button.pack(anchor="w",padx=20, pady=10)

        self.area_ref_button = tk.Button(panel, text="Seleccione área de referencia",bg='red',fg='white', command=self.shape_selector.select_area_referencia, state=tk.DISABLED)
        self.area_ref_button.pack(anchor="w",padx=20, pady=10)

        # Botones de confirmación y cálculo
        process_label = tk.Label(panel, text="Calcular y procesar:", bg=panel.cget("bg"), fg="black")
        process_label.pack(anchor="w", padx=20, pady=10)

        self.confirm_button = tk.Button(panel, text="Confirmar selección y calcular", command=self.confirmar_seleccion, state=tk.DISABLED)
        self.confirm_button.pack(anchor="w",padx=20, pady=10)

        self.curve_button = tk.Button(panel, text="Generar curva de nivel", command=self.mostrar_curvas_nivel, state=tk.DISABLED)
        self.curve_button.pack(anchor="w",padx=20, pady=10)
        
        # Botones de confirmación y cálculo
        process_label = tk.Label(panel, text="Exportar resultados:", bg=panel.cget("bg"), fg="black")
        process_label.pack(anchor="w", padx=20, pady=10)

        self.excel_button = tk.Button(panel, text="Exportar matriz a excel", command=self.exportar_a_excel, state=tk.DISABLED)
        self.excel_button.pack(pady=10)

        self.pdf_button = tk.Button(panel, text="Exportar a informe PDF", command=self.exportar_a_pdf, state=tk.DISABLED)
        self.pdf_button.pack(pady=10)
        
        self.save_dataset_button = tk.Button(panel, text="Guardar Dataset", command=self.save_dataset, state=tk.DISABLED)
        self.save_dataset_button.pack(pady=10)
        
        
        
    def setup_panel_3(self):
        """Configura el contenido del Panel 3"""
        panel = self.panel_frames[2]

        for widget in panel.winfo_children():
            widget.destroy()        
        
        diseno_label = tk.Label(panel, text="Modo de Edición:", bg=panel.cget("bg"), fg="black")
        diseno_label.grid(row=0, column=0,sticky="w", padx=10, pady=10)
        
                
        # Botone para añadir arbol 
        add_arbol = tk.Button(panel, text="Añadir Árbol",command=lambda: design.establecer_modo('arbol',self), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_arbol.grid(row=2, column=0,sticky="w",padx=10, pady=3)

        # Botone para añadir arbol 
        add_estructura = tk.Button(panel, text="Añadir Estructura",command=lambda: design.establecer_modo('estructura',self), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_estructura.grid(row=2, column=0,sticky="w",padx=100, pady=3) 

        # Botone para añadir arbol 
        seleccionar = tk.Button(panel, text="Seleccionar",command=lambda: design.establecer_modo(None,self), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        seleccionar.grid(row=3, column=0,sticky="w",padx=60, pady=3)        
        
        
        # Botone guardar como
        guardar = tk.Button(panel, text="Guardar como",command=lambda:design.guardar_como(self.vars,self), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        guardar.grid(row=4, column=0,sticky="w",padx=10, pady=10)

        # Botone abrir
        abrir = tk.Button(panel, text="Abrir",command=lambda:design.abrir_archivo(self.vars,self), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        abrir.grid(row=4, column=0,sticky="w",padx=120, pady=10)

        # Botone para Generar Gráfico 
        grafico = tk.Button(panel, text="Generar gráfico",command=lambda: self.actualizar_grafico_diseno(self.frame7), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))        
        grafico.grid(row=5, column=0,sticky="w",padx=10, pady=8)   
        # Botone para Vista 3D 
        vista_3d = tk.Button(panel, text="Vista 3D", command=lambda:design.generar_3d(self.vars), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        vista_3d.grid(row=5, column=0,sticky="w",padx=120, pady=8)     
        
        # Selector de viento
        Label_viento=tk.Label(panel, text="Viento")
        Label_viento.grid(sticky="w",padx=10, pady=3) 
        lista_viento=ttk.Combobox(panel, textvariable=self.vars["viento"],values=["nulo", "moderado", "fuerte"])
        lista_viento.grid(sticky="w",padx=10, pady=3) 
        
        panelin = tk.Frame(self.panel_frames[2])
        panelin.grid(row=1, column=0, sticky="nsew", padx=0, pady=2) 
        for texto, var, fila, rango, es_fecha in self.controles:
            self.crear_control(panelin, texto, var, fila, rango, es_fecha)
    def setup_panel_4(self):
        """Configura el contenido del Panel 4"""
        panel = self.panel_frames[3]
        
        
        for widget in panel.winfo_children():
            widget.destroy()        
        
        diseno_label = tk.Label(panel, text="Modelo", bg=panel.cget("bg"), fg="black")
        diseno_label.grid(row=0, column=0,sticky="w", padx=10, pady=1)
        
                
        # Botone para cargar excel
        add_arbol = tk.Button(panel, text="Cargar Excel",command=lambda:modelo.cargar_excel(self.vars_modelo), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_arbol.grid(row=1, column=0,sticky="w",padx=10, pady=5)

        # Botone para generar grafico
        add_estructura = tk.Button(panel, text="Generar Gráfico",command=lambda:modelo.generar_grafico(self.vars_modelo, self.frame11), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_estructura.grid(row=4, column=0,sticky="w",padx=20, pady=3)

        # Botone para añadir arbol 
        seleccionar = tk.Button(panel, text="Vista 3D",command=lambda:modelo.generar_3d(self.vars_modelo), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        seleccionar.grid(row=4, column=0,sticky="w",padx=130, pady=3)        
        
        Label_preconf=tk.Label(panel, text="Configuraciones rápidas")
        Label_preconf.grid(row=5, column=0,sticky="w",padx=10, pady=6) 
        # Botone guardar como
        seleccionar = tk.Button(panel, text="Soleado", command=lambda: modelo.cargar_preset("soleado", self.vars_modelo), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_arbol.grid(row=6, column=0,sticky="w",padx=30, pady=3)

        # Botone abrir
        add_estructura = tk.Button(panel, text="Verano", command=lambda: modelo.cargar_preset("verano", self.vars), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        add_estructura.grid(row=6, column=0,sticky="w",padx=120, pady=3)

        # Botone para Generar Gráfico 
        seleccionar = tk.Button(panel, text="Soleado", command=lambda: modelo.cargar_preset("soleado", self.vars), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        seleccionar.grid(row=7, column=0,sticky="w",padx=30, pady=3)        
        
        # Botone para Vista 3D 
        seleccionar = tk.Button(panel, text="Nublado", command=lambda: modelo.cargar_preset("nublado", self.vars), bg='#4CAF50', fg='white', font=("Arial", 8, "bold"))
        seleccionar.grid(row=7, column=0,sticky="w",padx=120, pady=3)     
        
        # Selector de viento
        Label_viento=tk.Label(panel, text="Viento")
        Label_viento.grid(row=3, column=0,sticky="w",padx=10, pady=3) 
        lista_viento=ttk.Combobox(panel, textvariable=self.vars_modelo["viento"],values=["nulo", "moderado", "fuerte"])
        lista_viento.grid(row=3, column=0,sticky="w",padx=60, pady=3) 
        
        panelin = tk.Frame(self.panel_frames[3])
        panelin.grid(row=2, column=0, sticky="nsew", padx=0, pady=10) 
        for texto, var, fila, rango, es_fecha in self.controles_modelo:
            self.crear_control(panelin, texto, var, fila, rango, es_fecha)
        self.vars_modelo["graph_frame"] = self.frame11
    def crear_control(self, panel, texto, var, fila, rango=None, es_fecha=False):
        tk.Label(panel, text=texto, anchor="w",font=("Arial", 8),width=20).grid(row=fila, column=0, sticky="ew", padx=0, pady=10)
        if es_fecha:
            entry = tk.Entry(panel,width=15)
            entry.grid(row=fila, column=1, sticky="ew", padx=0)
            entry.bind("<Return>", lambda e: actualizar_dia(entry.get(), var))
        elif rango:
            scale = tk.Scale(panel, from_=rango[0], to=rango[1], variable=var, 
                            orient=tk.HORIZONTAL,length=1,width=5)
            scale.grid(row=fila, column=1, sticky="ew", padx=0)
    def toggle_panel(self, index):
            if self.is_animating:
                return

            if self.active_panel is not None and self.active_panel != index:
                self.close_panel(self.active_panel)
                self.frame1.after(250, lambda: self.open_panel(index))  # Espera antes de abrir el nuevo panel
            elif self.active_panel == index:
                self.close_panel(self.active_panel)
                self.active_panel = None
            else:
                self.open_panel(index)
    def open_panel(self, index):
        self.active_panel = index
        self.is_animating = True
        self.animate_panel_open(index, 0)
        if index == 1:
            self.show_panel2_frames()
        elif index == 2:
            self.show_diseno_frames()
        elif index == 3:
            self.show_modelo_frames()
        self.switch_buttons_to_horizontal()
        self.highlight_button(index)
    def animate_panel_open(self, index, current_width):
        button_height = self.icon_frame.winfo_height()

        if current_width <= self.panel_width:
            self.panel_frames[index].config(width=current_width)
            self.panel_frames[index].place(x=0, y=button_height-90, relheight=1)#, rely=0.1
            self.frame1.after(10, self.animate_panel_open, index, current_width + 10)
        else:
            self.is_animating = False
    def close_panel(self, index):
        self.is_animating = True
        self.animate_panel_close(index, self.panel_width)
        self.reset_button(index)
        self.switch_buttons_to_vertical()
    def animate_panel_close(self, index, current_width):
        button_height = self.icon_frame.winfo_height()
        if current_width > 0:
            self.panel_frames[index].config(width=current_width)
            self.panel_frames[index].place(x=0, y=button_height, relheight=1, rely=0.1)
            self.frame1.after(10, self.animate_panel_close, index, current_width - 10)
        else:
            self.panel_frames[index].place_forget()
            self.is_animating = False
    def _toggle_frames(self, frames_to_show, frames_to_hide):
        for frame in frames_to_hide:
            frame.grid_remove()
        for frame in frames_to_show:
            frame.grid()
    def show_panel2_frames(self):
        self._toggle_frames(
            [self.frame2, self.frame3, self.frame4, self.frame5],
            [self.frame7, self.frame8, self.frame9, self.frame10, self.frame11, self.frame12, self.frame13, self.frame14],
        )
    def show_diseno_frames(self):
        self._toggle_frames(
            [self.frame7, self.frame8, self.frame9, self.frame10],
            [self.frame2, self.frame3, self.frame4, self.frame5, self.frame11, self.frame12, self.frame13, self.frame14],
        )
    def show_modelo_frames(self):
        self._toggle_frames(
            [self.frame11, self.frame12, self.frame13, self.frame14],
            [self.frame2, self.frame3, self.frame4, self.frame5, self.frame7, self.frame8, self.frame9, self.frame10],
        )
    def highlight_button(self, index):
        for i, button in enumerate(self.buttons):
            button.config(bg="gray80" if i == index else self.frame1.cget("bg"))
    def reset_button(self, index):
        self.buttons[index].config(bg=self.frame1.cget("bg"))
    def switch_buttons_to_horizontal(self):
        for i, button in enumerate(self.buttons):
            button.grid_forget()
            button.grid(row=0, column=i,padx=12, sticky="ew")
    def switch_buttons_to_vertical(self):
        for i, button in enumerate(self.buttons):
            button.grid_forget()
            button.grid(row=i, column=0, sticky="ew")
    # Configuración del menú en frame0
    def setup_menu(self):
        """Configura el menú principal."""
        menu_bar = tk.Menu(self.root)
        for i in range(1, 7):  # 6 elementos en el menú
            submenu = tk.Menu(menu_bar, tearoff=0)
            for j in range(1, 4):  # Cada uno con 3 opciones
                submenu.add_command(label=f"Opción {i}.{j}")
            menu_bar.add_cascade(label=f"Menú {i}", menu=submenu)
        self.root.config(menu=menu_bar)  # Establece el menú en la ventana principal
    def setup_status_bar(self):
        """Configura la barra de estado."""
        now = datetime.now()
        # date_time_label = tk.Label(self.frame6, text=f"Fecha y Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        self.frame6.configure(bg=self.palette["accent"])

        date_time_label = tk.Label(
            self.frame6,
            text=f"Fecha y Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            bg=self.palette["accent"],
            fg="#2c3e50",
            font=("Arial", 9, "bold"),
        )
        date_time_label.pack(side="right", padx=10)
        for i in range(1, 4):
            #label = tk.Label(self.frame6, text=f"Etiqueta {i}")
            label = tk.Label(
                self.frame6,
                text=f"Etiqueta {i}",
                bg=self.palette["accent"],
                fg="#4a4f63",
                font=("Arial", 9),
            )
            label.pack(side="right", padx=10)
    def create_card(self, parent):
        return tk.Frame(
            parent,
            bg=self.palette["panel"],
            bd=0,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
            padx=12,
            pady=12,
        )
    def resultados(self, frame):
        """Configura el área de resultados."""
        #result_frame = tk.Frame(frame, bd=2, relief=tk.RAISED, padx=1, pady=1, width=1000, height=200)
        result_frame = self.create_card(frame)
        result_frame.pack(expand=True, fill='both', pady=5)

        #sombra_frame = tk.Frame(result_frame)
        sombra_frame = tk.Frame(result_frame, bg=self.palette["panel"])
        sombra_frame.pack(side=tk.LEFT, padx=50, pady=10)

        self.lbl_dimensiones_calculo = tk.Label(
            #sombra_frame, text="Dimensiones del Área de Cálculo: N/A", font=("Arial", 12, "bold")
            sombra_frame,
            text="Dimensiones del Área de Cálculo: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_dimensiones_calculo.pack(pady=5)

        self.lbl_dimensiones_referencia = tk.Label(
            #sombra_frame, text="Dimensiones del Área de Referencia: N/A", font=("Arial", 12, "bold")
            sombra_frame,
            text="Dimensiones del Área de Referencia: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",        
        )
        self.lbl_dimensiones_referencia.pack(pady=5)

        self.lbl_promedio_referencia = tk.Label(
            #sombra_frame, text="Promedio Gris Referencia: N/A", font=("Arial", 12, "bold")
            sombra_frame,
            text="Promedio Gris Referencia: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_promedio_referencia.pack(pady=5)

        self.lbl_porcentaje_sombra = tk.Label(
            #sombra_frame, text="Porcentaje de sombra: N/A", font=("Arial", 12, "bold")
            sombra_frame,
            text="Porcentaje de sombra: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_porcentaje_sombra.pack(pady=5)
    def temp_sombra(self, frame):
        """Configura el área de temperatura en sombra."""
        #temp_frame = tk.Frame(frame, bd=2, relief=tk.RAISED, padx=1, pady=1, width=1000, height=200)
        temp_frame = self.create_card(frame)
        temp_frame.pack(expand=True, fill='both', pady=5)

        #self.lbl_temp_shade = tk.Label(temp_frame, text="Temperatura en Sombra: N/A", font=("Arial", 12, "bold"))
        self.lbl_tmrt_sol = tk.Label(
            temp_frame,
            text="Tmrt al sol: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_tmrt_sol.pack(pady=5)

        self.lbl_tmrt_sombra = tk.Label(
            temp_frame,
            text="Tmrt en sombra: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_tmrt_sombra.pack(pady=5)

        self.lbl_delta_tmrt = tk.Label(
            temp_frame,
            text="ΔTmrt (impacto sombra): N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_delta_tmrt.pack(pady=5)    

        #self.graph_frame = tk.Frame(temp_frame)
        self.graph_frame = tk.Frame(temp_frame, bg=self.palette["panel"])
        self.graph_frame.pack(side=tk.RIGHT, padx=10)
    def imagen(self, frame):
        """Configura el área de visualización de imágenes."""
        #img_frame = tk.Frame(frame, bd=2, relief=tk.RAISED, padx=1, pady=1, width=1000, height=200)
        img_frame = self.create_card(frame)
        img_frame.pack(expand=True, fill='both', pady=5)
        self.fig1, self.ax1 = plt.subplots() 
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=img_frame)
        self.canvas1.get_tk_widget().pack(side=tk.LEFT)
    def curva_de_nivel(self, frame):
        """Configura el área de curvas de nivel."""
        #nivel_frame = tk.Frame(frame, bd=2, relief=tk.RAISED, padx=1, pady=1, width=1000, height=200)
        nivel_frame = self.create_card(frame)
        nivel_frame.pack(expand=True, fill='both', pady=5)
        self.curva_frame = nivel_frame
        self.curva_frame.bind("<Configure>", self._on_curva_frame_resize)

        self.fig2, self.ax2 = plt.subplots()
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=nivel_frame)
        self.canvas2.get_tk_widget().pack(side=tk.RIGHT)
    def cargar_imagen(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.img, self.img_rgb = self.image_processor.load_image(file_path)
            self.original_rgb = self.img_rgb
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self._setup_hover_shadow_percent_photo(self.ax1, self.canvas1, self.img_rgb)
            self.canvas1.draw()
            self.shape_selector.enable_calculo_button()
            if self.mouse_hover_pixel_value is None:
                self.mouse_hover_pixel_value = MouseHoverPixelValueWithTooltip(
                    self,
                    self.canvas1,
                    self.canvas2,
                    self.img_rgb,
                    self.shape_selector.area_seleccionada,
                )
            else:
                self.mouse_hover_pixel_value.img_rgb = self.img_rgb
    def calculate_temperature_in_shade(self):
        try:
            if self.porcentaje_sombra is None:
                messagebox.showerror("Error", "Primero debe seleccionar el área para calcular el porcentaje de sombra.")
                return
            # Obtener valores ingresados por el usuario
            temp_ambient = float(self.entry_temp.get().replace('\ufeff', '').strip())
            latitude = float(self.entry_lat.get().replace('\ufeff', '').strip())
            longitude = float(self.entry_lon.get().replace('\ufeff', '').strip())

            self.temp_calculator = Temperatura(latitude, longitude)
            result = self.temp_calculator.calculate_tmrt(temp_ambient, self.porcentaje_sombra, shadow_type="tree")
            self.tmrt_result = result
            
            
            self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {result['Tmrt_sol']:.2f} °C")
            self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {result['Tmrt_sombra']:.2f} °C")
            self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {result['Delta_Tmrt']:.2f} °C")
            # Limpiar el frame anterior si existe (evita sobreposición de gráficos)
            for widget in self.graph_frame.winfo_children():
                widget.destroy()

            # Crear un objeto de la clase TemperatureGraph y mostrar la gráfica dentro del frame
            graph = TemperatureGraph(temp_ambient, result["Tmrt_sombra"], self.graph_frame)
            graph.plot_temperature_scale()  # Dibujar la gráfica en el frame

        except ValueError as e:
            messagebox.showerror("Error", f"Error al ingresar los datos: {e}")
    def confirmar_seleccion(self):
        # Verificamos que ambas áreas hayan sido seleccionadas
        if self.shape_selector.area_seleccionada is not None and self.shape_selector.area_referencia is not None:
            # Cálculo del porcentaje de sombra
            porcentaje_sombra = self.image_processor.calcular_porcentaje_sombra(
                self.shape_selector.area_seleccionada,
                self.shape_selector.area_referencia
            )
            self.porcentaje_sombra = porcentaje_sombra
            self.lbl_porcentaje_sombra.config(text=f"Porcentaje de sombra: {porcentaje_sombra:.2f}%")

            # Habilitar los botones para curvas de nivel y exportar
            self.curve_button.config(state=tk.NORMAL)  # Habilitar el botón de curvas de nivel
            self.excel_button.config(state=tk.NORMAL)  # Habilitar el botón para exportar a Excel
            self.pdf_button.config(state=tk.NORMAL) # Habilita el botón para guardan el pdf
        else:
            print("Error: No se ha seleccionado un área válida.")
    def exportar_a_excel(self):
        if self.shape_selector.area_seleccionada is not None:
            export_to_excel(self.shape_selector.area_seleccionada)
    def mostrar_curvas_nivel(self):
        if self.shape_selector.area_seleccionada is not None:
            
            # Rotar la matriz 90 grados en sentido horario
            area_volteada = np.flipud(self.shape_selector.area_seleccionada)
            #area_rotada = np.rot90(self.shape_selector.area_seleccionada, k=0)  # k=-1 para rotar 90 grados a la derecha
        

            # Crear las curvas de nivel en una figura local
            fig, ax = plt.subplots()
            ax.contour(area_volteada, levels=100, cmap='jet', linewidths=1.5, alpha=0.8)
            fig.tight_layout(pad=0)

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0)
            buf.seek(0)
            plt.close(fig)

            img = Image.open(buf).copy()
            buf.close()
            self.curva_img_pil_original = img
            resized_img = self._fit_image_to_frame(self.curva_img_pil_original, self.curva_frame)
            photo = ImageTk.PhotoImage(resized_img)
            if self.curva_label is None:
                self.curva_label = tk.Label(self.curva_frame, image=photo, bg=self.curva_frame.cget("bg"))
                self.curva_label.pack(expand=True, fill='both')
            else:
                self.curva_label.configure(image=photo)
            self.curva_photo = photo
            self.curva_label.image = photo
            if self.canvas2 is not None:
                self.canvas2.get_tk_widget().pack_forget()

            self.tmrt_map = area_volteada
            self.curvas_nivel_creadas = True
    def _fit_image_to_frame(self, pil_img, frame, padding=8):
        if frame is None:
            return pil_img
        frame.update_idletasks()
        frame_width = frame.winfo_width()-15        
        frame_height = frame.winfo_height()-15
        if frame_width <= 1 or frame_height <= 1:
            frame_width, frame_height = 600, 350
        frame_width = max(1, frame_width - padding * 2)
        frame_height = max(1, frame_height - padding * 2)
        img_width, img_height = pil_img.size
        scale = min(frame_width / img_width, frame_height / img_height)
        new_width = max(1, int(img_width * scale))
        new_height = max(1, int(img_height * scale))
        return pil_img.resize((new_width, new_height), Image.LANCZOS)

    def _on_curva_frame_resize(self, event):
        if self.curva_img_pil_original is None or self.curva_label is None:
            return
        resized_img = self._fit_image_to_frame(self.curva_img_pil_original, event.widget)
        self.curva_photo = ImageTk.PhotoImage(resized_img)
        self.curva_label.config(image=self.curva_photo)
        self.curva_label.image = self.curva_photo

    def exportar_a_pdf(self):
        pdf_generator = PDFReportGenerator(self)
        pdf_generator.generate_report()    
    def actualizar_dia(fecha_str, dia_var):
        # Función para actualizar día del año desde fecha
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            dia_del_año = fecha.timetuple().tm_yday
            dia_var.set(dia_del_año)
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
    def render_grafico_en_frame(self, target_frame, grafico_fn, *args):
        for widget in target_frame.winfo_children():
            widget.destroy()
        
        
        # Crear nuevo gráfico en frame2 y capturar el canvas
        return grafico_fn(*args, target_frame)
    def actualizar_grafico_diseno(self, target_frame=None):
        if target_frame is None:
            target_frame = self.frame2

        # Crear nuevo gráfico en el frame destino y capturar el canvas
        fig, ax, self.canvas_diseno = self.render_grafico_en_frame(
            target_frame,
            lambda vars, frame: design.crear_area_grafico(vars, frame, self),
            self.vars,
        )
    
        # Vincular eventos usando la instancia actual (self)
        self.canvas_diseno.mpl_connect('button_press_event', lambda event: design.manejar_click(event, self))
    def save_dataset(self):
        """Método para manejar el guardado del dataset"""
        if not hasattr(self, 'img_rgb') or self.img_rgb is None:
            messagebox.showerror("Error", "No hay imagen cargada")
            return
            
        if not hasattr(self.shape_selector, 'area_seleccionada') or self.shape_selector.area_seleccionada is None:
            messagebox.showerror("Error", "No hay área de cálculo seleccionada")
            return
            
        try:
            self.dataset_saver.save_dataset()
            messagebox.showinfo("Éxito", "Dataset guardado correctamente")
        except Exception as e:
                        messagebox.showerror("Error", f"No se pudo guardar el dataset: {str(e)}")

    def _setup_hover_tmrt_map(self, ax, canvas, data_2d):
        if self._tmrt_hover_canvas is not None and self._tmrt_hover_cid is not None:
            self._tmrt_hover_canvas.mpl_disconnect(self._tmrt_hover_cid)
        self._tmrt_hover_canvas = canvas
        if self._tmrt_hover_annotation is None or self._tmrt_hover_annotation.axes != ax:
            self._tmrt_hover_annotation = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=8,
                bbox=dict(boxstyle="round", fc="white", alpha=0.7),
            )
            self._tmrt_hover_annotation.set_visible(False)

        def on_move(event):
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if self._tmrt_hover_annotation.get_visible():
                    self._tmrt_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            x, y = int(event.xdata), int(event.ydata)
            if y < 0 or x < 0 or y >= data_2d.shape[0] or x >= data_2d.shape[1]:
                if self._tmrt_hover_annotation.get_visible():
                    self._tmrt_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            tmrt_value = float(data_2d[y, x])
            try:
                temp_air = float(self.entry_temp.get().replace('\ufeff', '').strip())
                temp_air_text = f"{temp_air:.2f} °C"
            except (ValueError, AttributeError):
                temp_air_text = "N/A"

            self._tmrt_hover_annotation.xy = (event.xdata, event.ydata)
            self._tmrt_hover_annotation.set_text(
                f"Tmrt: {tmrt_value:.2f} °C\nTemp aire: {temp_air_text}"
            )
            self._tmrt_hover_annotation.set_visible(True)
            canvas.draw_idle()

        self._tmrt_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)

    def _setup_hover_shadow_percent_photo(self, ax, canvas, rgb_img):
        if self._shadow_hover_canvas is not None and self._shadow_hover_cid is not None:
            self._shadow_hover_canvas.mpl_disconnect(self._shadow_hover_cid)
        self._shadow_hover_canvas = canvas
        if self._shadow_hover_annotation is None or self._shadow_hover_annotation.axes != ax:
            self._shadow_hover_annotation = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=8,
                bbox=dict(boxstyle="round", fc="white", alpha=0.7),
            )
            self._shadow_hover_annotation.set_visible(False)

        def on_move(event):
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if self._shadow_hover_annotation.get_visible():
                    self._shadow_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            x, y = int(event.xdata), int(event.ydata)
            if y < 0 or x < 0 or y >= rgb_img.shape[0] or x >= rgb_img.shape[1]:
                if self._shadow_hover_annotation.get_visible():
                    self._shadow_hover_annotation.set_visible(False)
                    canvas.draw_idle()
                return

            pixel = rgb_img[y, x]
            r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            ref_gray = self.ref_gray_mean
            if ref_gray is None or ref_gray <= 0:
                text = "Ref no definida"
            else:
                sombra = (ref_gray - gray) / ref_gray
                sombra = max(0, min(sombra, 1)) * 100
                text = f"% Sombra: {sombra:.2f}%"

            self._shadow_hover_annotation.xy = (event.xdata, event.ydata)
            self._shadow_hover_annotation.set_text(text)
            self._shadow_hover_annotation.set_visible(True)
            canvas.draw_idle()

        self._shadow_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)