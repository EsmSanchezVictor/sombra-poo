import tkinter as tk
from tkinter import ttk
from datetime import datetime
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
from mouse_pixel_value  import MouseHoverPixelValueWithTooltip

from utils import export_to_excel


class App:
    def __init__(self, root):
      
        self.root = root
       # self.root.title("Selección de Área y Análisis de Sombra")
        
        # Crear los frames con colores para visualizar mejor
        self.frame1 = tk.Frame(self.root, bg="orange",width=400)
        self.frame2 = tk.Frame(root, bg="green")
        self.frame3 = tk.Frame(root, bg="blue")
        self.frame4 = tk.Frame(root, bg="yellow")
        self.frame5 = tk.Frame(root, bg="purple")
        self.frame6 = tk.Frame(root, bg="red")

        # Distribuir los frames en la cuadrícula con sticky="nsew" para que se expandan
        self.frame1.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.frame2.grid(row=0, column=1, sticky="nsew")
        self.frame3.grid(row=0, column=2, sticky="nsew")
        self.frame4.grid(row=1, column=1, sticky="nsew")
        self.frame5.grid(row=1, column=2, sticky="nsew")
        self.frame6.grid(row=2, column=0, columnspan=3, sticky="nsew")
        
        # Configurar el comportamiento responsivo de las filas y columnas
        self.root.grid_rowconfigure(0, weight=1)  # Permitir que la primera fila se expanda
        self.root.grid_rowconfigure(1, weight=1)  # Permitir que la segunda fila se expanda
        self.root.grid_rowconfigure(2, weight=1)  # Permitir que la tercera fila se expanda
        self.root.grid_columnconfigure(0, weight=1)  # Permitir que la primera columna se expanda
        self.root.grid_columnconfigure(1, weight=1)  # Permitir que la segunda columna se expanda
        self.root.grid_columnconfigure(2, weight=1)  # Permitir que la tercera columna se expanda
         
        # Otros atributos que tengas...
        self.curvas_nivel_creadas = False  # Bandera para saber si las curvas de nivel han sido creadas

        # Instanciar la clase Temperatura
        self.temp_calculator = Temperatura()
        
        # Inicializamos el procesador de imágenes y el selector de forma
        self.image_processor = ImageProcessor()
        self.shape_selector = ShapeSelector(self)

        # Variables de control
        self.setup_variables()

        # Crear y configurar los widgets de la GUI
        self.setup_gui()

    def setup_variables(self):
        """Inicializa las variables de control para la aplicación"""
        self.selection_type = tk.StringVar(value="Rectángulo")
        self.matriz_size = tk.IntVar(value=1024)
        self.drawing_mode = None
        self.img = None
        self.img_rgb = None
        self.area_calculo_done = False
        self.area_referencia_done = False

   
    def setup_gui(self):
        
        
        
        # Botones de acción
        self.btn_cargar = tk.Button(self.frame1, text="Cargar Imagen", command=self.cargar_imagen, bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        self.btn_cargar.pack(expand=True, fill='both',pady=5)
        
        # Crear un marco para organizar los widgets selesct
        self.frame_select = tk.Frame(self.frame1, bd=2, relief=tk.RAISED, padx=1, pady=1,width=500, height=200)
        self.frame_select.pack(expand=True, fill='both',pady=5)
        
        # Crear un menú de selección de tipo de área (Círculo o Rectángulo)
        lbl_seleccion = tk.Label(self.frame_select, text="Selecciona Tipo de Área:", font=("Arial", 8, "bold"))
        lbl_seleccion.pack(expand=True, fill='both',pady=5)

        radio_rectangulo = tk.Radiobutton(self.frame_select, text="Rectángulo",command=self.cargar_imagen, bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        radio_rectangulo.pack(expand=True, fill='both')

        radio_circulo = tk.Radiobutton(self.frame_select, text="Círculo", variable=self.selection_type, value="Círculo")
        radio_circulo.pack(expand=True, fill='both',pady=5)

        # Opción para seleccionar el tamaño de la matriz
        lbl_matriz_size = tk.Label(self.frame_select, text="Selecciona Tamaño de Matriz:", font=("Arial", 8, "bold"))
        lbl_matriz_size.pack(expand=True, fill='both',pady=5)
        option_menu_matriz = tk.OptionMenu(self.frame_select, self.matriz_size, 480, 640, 800, 1024)
        option_menu_matriz.pack(expand=True, fill='both',pady=5)



        self.btn_area_calculo = tk.Button(self.frame_select, text="     Seleccionar Área de Cálculo      ",bg='blue',fg='white', command=self.shape_selector.select_area_calculo, state=tk.DISABLED)
        self.btn_area_calculo.pack(expand=True, fill='both',pady=5)

        self.btn_area_referencia = tk.Button(self.frame_select, text="        Seleccionar Área de Referencia       ",bg='red',fg='white', command=self.shape_selector.select_area_referencia, state=tk.DISABLED)
        self.btn_area_referencia.pack(expand=True, fill='both',pady=5)
        
        
                # Crear un marco para organizar los widgets selesct
        self.frame_calc = tk.Frame(self.frame1, bd=2, relief=tk.RAISED, padx=1, pady=1,width=500, height=200)
        self.frame_calc.pack(expand=True, fill='both',pady=5)
        
        lbl_matriz_size = tk.Label(self.frame_calc, text="Calcular y procesar:", font=("Arial", 12, "bold"))
        lbl_matriz_size.pack(expand=True, fill='both',pady=5)
        
        self.btn_confirmar = tk.Button(self.frame_calc, text="Confirmar Selección y Calcular", command=self.confirmar_seleccion, state=tk.DISABLED)
        self.btn_confirmar.pack(expand=True, fill='both',pady=5)
        
        # Botón para generar las curvas de nivel en la segunda área de dibujo
        self.btn_curvas = tk.Button(self.frame_calc, text="Generar Curvas de Nivel", command=self.mostrar_curvas_nivel, state=tk.DISABLED)
        self.btn_curvas.pack(pady=2)
        
        self.frame_export = tk.Frame(self.frame1, bd=2, relief=tk.RAISED, padx=1, pady=1,width=500, height=200)
        self.frame_export.pack(expand=True, fill='both',pady=5)

        lbl_matriz_size = tk.Label(self.frame_export, text="Exportar resultados:", font=("Arial", 12, "bold"))
        lbl_matriz_size.pack(expand=True, fill='both',pady=5)
        
        self.btn_exportar = tk.Button(self.frame_export, text="Exportar Matriz a Excel", command=self.exportar_a_excel, state=tk.DISABLED)
        self.btn_exportar.pack(expand=True, fill='both')
        
        self.btn_exportar_pdf = tk.Button(self.frame_export, text="Exportar Informe PDF", command=self.exportar_a_pdf, state=tk.DISABLED)
        self.btn_exportar_pdf.pack(expand=True, fill='both',pady=5)
        
        self.frame_sis = tk.Frame(self.frame1, bd=2, relief=tk.RAISED, padx=1, pady=1,width=500, height=200)
        self.frame_sis.pack(expand=True, fill='both',pady=5)
        
        # Botón para resetear
        self.btn_reset = tk.Button(self.frame_sis, text="Resetear", command=self.resetear_campos)
        self.btn_reset.pack(expand=True, fill='both',pady=5)

        # Botón para salir
        self.btn_salir = tk.Button(self.frame_sis, text="Salir", command=self.root.quit)
        self.btn_salir.pack(expand=True, fill='both',pady=5)
        

        
           # Crear un marco para los controles de entrada de datos
        self.input_frame = tk.Frame(self.frame6, bd=2, relief=tk.RAISED, padx=1, pady=1,width=1000, height=200)
        self.input_frame.pack(expand=True, fill='both',pady=5)
        

        tk.Label(self.input_frame, text="Temperatura Ambiente (°C):").pack(side=tk.LEFT)
        self.temp_ambient = tk.Entry(self.input_frame,width=10)
        self.temp_ambient.pack(side=tk.LEFT)

        tk.Label(self.input_frame, text="Hora del Día (0-23):").pack(side=tk.LEFT)
        self.time_of_day = tk.Entry(self.input_frame,width=10)
        self.time_of_day.pack(side=tk.LEFT)

        tk.Label(self.input_frame, text="Fecha (YYYY-MM-DD):").pack(side=tk.LEFT)
        self.date_entry = tk.Entry(self.input_frame,width=10)
        self.date_entry.pack(side=tk.LEFT)

        tk.Label(self.input_frame, text="Latitud:").pack(side=tk.LEFT)
        self.latitude_entry = tk.Entry(self.input_frame,width=10)
        self.latitude_entry.pack(side=tk.LEFT)

        tk.Label(self.input_frame, text="Longitud:").pack(side=tk.LEFT)
        self.longitude_entry = tk.Entry(self.input_frame,width=10)
        self.longitude_entry.pack(side=tk.LEFT)

        # Botón para calcular la temperatura bajo sombra
        self.btn_calculate_temp = tk.Button(self.input_frame, text="Calcular Temperatura en Sombra", command=self.calculate_temperature_in_shade)
        self.btn_calculate_temp.pack(side=tk.LEFT, padx=10, pady=10)
        
        

        # Marco para las etiquetas de resultados
        
        self.result_frame = tk.Frame(self.frame4, bd=2, relief=tk.RAISED, padx=1, pady=1,width=1000, height=200)
        self.result_frame.pack(expand=True, fill='both',pady=5)
           
        
        self.sombra_frame = tk.Frame(self.result_frame)
        self.sombra_frame.pack(side=tk.LEFT, padx=50, pady=10)
        # Mostrar las dimensiones de las áreas seleccionadas en el marco de resultados
        self.lbl_dimensiones_calculo = tk.Label(self.sombra_frame, text="Dimensiones del Área de Cálculo: N/A", font=("Arial", 12, "bold"))
        self.lbl_dimensiones_calculo.pack(pady=5)

        self.lbl_dimensiones_referencia = tk.Label(self.sombra_frame, text="Dimensiones del Área de Referencia: N/A", font=("Arial", 12, "bold"))
        self.lbl_dimensiones_referencia.pack(pady=5)

        self.lbl_promedio_referencia = tk.Label(self.sombra_frame, text="Promedio Gris Referencia: N/A", font=("Arial", 12, "bold"))
        self.lbl_promedio_referencia.pack(pady=5)

        self.lbl_porcentaje_sombra = tk.Label(self.sombra_frame, text="Porcentaje de sombra: N/A", font=("Arial", 12, "bold"))
        self.lbl_porcentaje_sombra.pack(pady=5)
        
        self.temp_frame = tk.Frame(self.frame5, bd=2, relief=tk.RAISED, padx=1, pady=1,width=1000, height=200)
        self.temp_frame.pack(expand=True, fill='both',pady=5)
 
        # Crear la etiqueta para mostrar la temperatura en sombra
        self.lbl_temp_shade = tk.Label(self.temp_frame, text="Temperatura en Sombra: N/A", font=("Arial", 12, "bold"))
        self.lbl_temp_shade.pack(pady=5)
        
        # Añadir un Frame para el gráfico de temperatura en sombra
        self.graph_frame = tk.Frame(self.temp_frame)  # Crear el frame donde va la gráfica
        self.graph_frame.pack(side=tk.RIGHT, padx=10)  # Posicionar a la derecha


        self.img_frame = tk.Frame(self.frame2, bd=2, relief=tk.RAISED, padx=1, pady=1,width=1000, height=200)
        self.img_frame.pack(expand=True, fill='both',pady=5)
 
     
        # Crear la primera figura y canvas para mostrar la imagen original
        self.fig1, self.ax1 = plt.subplots()
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.img_frame)
        self.canvas1.get_tk_widget().pack(side=tk.LEFT)
        
        self.nivel_frame = tk.Frame(self.frame3, bd=2, relief=tk.RAISED, padx=1, pady=1,width=1000, height=200)
        self.nivel_frame.pack(expand=True, fill='both',pady=5)
        
        # Crear la segunda figura y canvas para mostrar las curvas de nivel
        self.fig2, self.ax2 = plt.subplots()
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.nivel_frame)
        self.canvas2.get_tk_widget().pack(side=tk.RIGHT)
        
        # Vincular eventos de mouse
        self.canvas1.mpl_connect('button_press_event', self.shape_selector.on_mouse_press)
        self.canvas1.mpl_connect('motion_notify_event', self.shape_selector.on_mouse_move)
        self.canvas1.mpl_connect('button_release_event', self.shape_selector.on_mouse_release)

    def cargar_imagen(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.img, self.img_rgb = self.image_processor.load_image(file_path)
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self.canvas1.draw()
            self.shape_selector.enable_calculo_button()
        
    def confirmar_seleccion(self):
        # Verificamos que ambas áreas hayan sido seleccionadas
        if self.shape_selector.area_seleccionada is not None and self.shape_selector.area_referencia is not None:
            # Cálculo del porcentaje de sombra
            porcentaje_sombra = self.image_processor.calcular_porcentaje_sombra(
                self.shape_selector.area_seleccionada,
                self.shape_selector.area_referencia
            )
            self.lbl_porcentaje_sombra.config(text=f"Porcentaje de sombra: {porcentaje_sombra:.2f}%")

            # Habilitar los botones para curvas de nivel y exportar
            self.btn_curvas.config(state=tk.NORMAL)  # Habilitar el botón de curvas de nivel
            self.btn_exportar.config(state=tk.NORMAL)  # Habilitar el botón para exportar a Excel
            self.btn_exportar_pdf.config(state=tk.NORMAL) # Habilita el botón para guardan el pdf
            # Instanciar la clase para manejar el hover del mouse y mostrar el valor del píxel
            self.mouse_hover_pixel_value = MouseHoverPixelValueWithTooltip(self, self.canvas1, self.canvas2, self.img_rgb, self.shape_selector.area_seleccionada)
            
           
  
            
          
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
        
            # Crear las curvas de nivel en el segundo área de dibujo
            self.ax2.clear()
            self.ax2.contour(area_volteada, levels=100, cmap='jet', linewidths=1.5, alpha=0.8)  # Usar mapa de colores 'jet'
            self.canvas2.draw()
            self.mouse_hover_pixel_value = MouseHoverPixelValueWithTooltip(self, self.canvas1, self.canvas2, self.img_rgb, self.shape_selector.area_seleccionada)
            self.curvas_nivel_creadas = True
            # Instanciar MouseHoverPixelValueWithTooltip después de generar las curvas de nivel
        self.mouse_hover_pixel_value = MouseHoverPixelValueWithTooltip(self, self.canvas1, self.canvas2, self.img_rgb, self.shape_selector.area_seleccionada)

    def exportar_a_pdf(self):
        pdf_generator = PDFReportGenerator(self)
        pdf_generator.generate_report()
        
    def calculate_temperature_in_shade(self):
        try:
            # Obtener valores ingresados por el usuario
            temp_ambient = float(self.temp_ambient.get().replace('\ufeff', '').strip())
            time_of_day = int(self.time_of_day.get().replace('\ufeff', '').strip())
            date = datetime.strptime(self.date_entry.get().replace('\ufeff', '').strip(), "%Y-%m-%d").date()
            latitude = float(self.latitude_entry.get().replace('\ufeff', '').strip())
            longitude = float(self.longitude_entry.get().replace('\ufeff', '').strip())

            # Parámetros de opacidad y densidad
            opacity = 0.8  # Puedes ajustarlo para que se base en los niveles de gris
            shadow_density = 0.9  # Basado en la densidad de los puntos de sombra

            # Usar la clase Temperatura para calcular la temperatura en sombra
            temp_shade = self.temp_calculator.temperature_in_shade(
                temp_ambient, latitude, longitude, date, time_of_day, opacity, shadow_density
            )

            # Mostrar el resultado de temperatura en sombra
            self.lbl_temp_shade.config(text=f"Temperatura en Sombra: {temp_shade:.2f} °C")

            # Limpiar el frame anterior si existe (evita sobreposición de gráficos)
            for widget in self.graph_frame.winfo_children():
                widget.destroy()

            # Crear un objeto de la clase TemperatureGraph y mostrar la gráfica dentro del frame
            graph = TemperatureGraph(temp_ambient, temp_shade, self.graph_frame)
            graph.plot_temperature_scale()  # Dibujar la gráfica en el frame

        except ValueError as e:
            print(f"Error al ingresar los datos: {e}")
        
    def resetear_campos(self):
        """Restablecer todos los campos de entrada y limpiar la interfaz"""
        self.selection_type.set("Rectángulo")
        self.matriz_size.set(1024)
        self.ax1.clear()
        self.canvas1.draw()
