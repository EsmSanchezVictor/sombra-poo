from datetime import datetime
from io import BytesIO
import os
import shutil
import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from typing import Optional
from DatasetSaver import DatasetSaver
from core.app_state import AppState
from core.settings_manager import SettingsManager
from core.project_manager import ProjectManager
from core.file_versioning import safe_path
from image_processor import ImageProcessor
#from mouse_pixel_value import MouseHoverPixelValueWithTooltip
from save_pdf import PDFReportGenerator
from services.location_service import LocationService
from services.snapshot_service import SnapshotService
from services.shadow_detector import ShadowDetector
from shape_selection import ShapeSelector
from shadow_temp import Temperatura
from temp_graph import TemperatureGraph
from services.solar_engine import SolarEngine
from services import analysis_service
from services import report_service
from ui import icon_factory
from ui import theme
from ui.menu_bar import MenuBar
from utils import export_to_excel
import diseño as design
import modelo_con_excel as modelo


class SombraApp:
    def __init__(self, root):

        self.root = root
        self.root.title("Distribución Grid")
        # NUEVO: la ventana arranca siempre maximizada. Antes se creaba
        # con el tamaño por defecto de Tk (chico, sin geometría propia)
        # — con layouts complejos como el de esta app, eso generaba
        # huecos en blanco y contenido apretado, como el de la captura.
        try:
            self.root.state("zoomed")  # Windows / algunos WMs de Linux
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)  # X11
            except tk.TclError:
                pass
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
        # Paleta de colores para toda la interfaz — centralizada en
        # ui/theme.py (antes vivía duplicada acá con solo 4 colores;
        # ahora además hay vocabulario con intención: primario, éxito,
        # texto — en vez de códigos hex sueltos repetidos en cada
        # pantalla).
        self.palette = dict(theme.PALETA)
        self.style = theme.aplicar_tema(self.root, self.palette)

        self.root.configure(bg=self.palette["background"])
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.base_dir = base_dir
        self.settings_path = os.path.join(base_dir, "data", "settings.json")
        self.settings_manager = SettingsManager(self.settings_path)
        self.settings = self.settings_manager.load()
        self.current_project_path = self.settings.get("last_project_path")
        self.current_location = None        
        self.is_dirty = False
        self.last_T = None
        self.last_shadow = None
        self.last_meta = None
        self.last_model_excel_path = None
        self.last_edit_excel_path = None
        self.last_image_path = None
        self.last_curve_path = None
        self.last_matrix_path = None
        self.last_mask_path = None
        self.last_histogram_path = None
        self.last_temp_graph_path = None
        self.shadow_quality = None

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

        self.startup_frame = tk.Frame(
            root,
            bg=self.palette["panel"],
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )        
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
        # Servicios de estado y proyecto
        self.app_state = AppState(self)
        self.project_manager = ProjectManager(self, self.app_state, self.settings_manager)
        self.snapshot_service = SnapshotService(self, self.project_manager)
        self.shadow_detector = ShadowDetector()
        self.shadow_detector_enabled = tk.BooleanVar(value=False)
        self.use_pvlib_engine = tk.BooleanVar(value=False)
        self.solar_engine = SolarEngine(use_pvlib=False)
        self.menu_bar = MenuBar(self)
        self.porcentaje_sombra = None
        self.tmrt_result = None
        self.snapshots = []  # NUEVO: historial de elementos analizados (imagen+sombra+curva+Tmrt) del proyecto actual
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.original_rgb = None
        self._tmrt_hover_cid = None
        self._tmrt_hover_canvas = None
        self._tmrt_hover_annotation = None
        self._shadow_hover_cid = None
        self._shadow_hover_canvas = None
        self._shadow_hover_annotation = None
        self.mouse_hover_pixel_value = None
        self.curva_frame = None
        self.curva_label = None
        self.curva_photo = None
        self.curva_img_pil_original = None
        #self.frame1 = frame1

        # --- Ancho del panel desplegable -----------------------------
        # panel_width se calcula UNA sola vez acá: el menor entre 1/6
        # del ancho de pantalla y el ancho actual de frame1. En este
        # punto de __init__ frame1 todavía no se dibujó en pantalla, así
        # que frame1.winfo_width() puede devolver un valor chico/no
        # definitivo — si el panel se ve angosto o ancho de más al
        # ajustarlo, este es el número a tocar (o reemplazarlo por una
        # constante fija en píxeles, ej. 260).
        self.panel_width = min(int(self.frame1.winfo_screenwidth() / 6), self.frame1.winfo_width())

        # --- Barra de íconos lateral (columna 0 de frame1) -----------
        # Se queda siempre en column=0 de frame1; los paneles se abren
        # A LA DERECHA de esta barra (ver open_panel/animate_panel_open
        # más abajo, sección "GEOMETRÍA").
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
        # self.panel_frames: frame de CONTENIDO de cada panel (acá es
        # donde setup_panel_1/2/3/4 empacan sus widgets — sin cambios
        # en esas funciones). Vive DENTRO de un Canvas con scrollbar.
        self.panel_frames = []
        # self.panel_outer_frames: frame FÍSICO de cada panel — es el
        # que se anima (ancho creciente/decreciente) y se posiciona con
        # .place() debajo de la barra de íconos. Acá NUNCA se empacan
        # widgets directamente.
        self.panel_outer_frames = []

        # Crear 4 botones que actuarán como iconos y 4 paneles
        for i in range(4):
            btn = tk.Button(self.icon_frame, image=self.images[i], command=lambda i=i: self.toggle_panel(i), relief=tk.FLAT,
                            bg=self.frame1.cget('bg'))
            btn.grid(row=i, column=0, pady=0, padx=0, sticky="ew")
            self.buttons.append(btn)

        # --- Paneles desplegables (inicialmente ocultos) -------------
        # Cada panel = 1 frame outer (animado/posicionado) que contiene
        # un Canvas+Scrollbar vertical, y adentro el frame de contenido
        # real. Esto es lo que arregla dos bugs reportados:
        #   1) el panel quedaba parcialmente tapado por la barra de
        #      íconos (frame1 no se agrandaba para darle lugar — ver
        #      open_panel/close_panel), y
        #   2) contenido más alto que la pantalla se perdía sin forma
        #      de llegar a él (ahora hay scroll vertical con rueda del
        #      mouse o la scrollbar).
        for i in range(4):
            outer = tk.Frame(
                self.frame1,
                bg=self.palette["panel"],
                width=0,
                height=400,
                highlightbackground=self.palette["border"],
                highlightthickness=1,
                bd=0,
            )
            outer.place(x=0, y=0, relheight=1)
            outer.place_forget()
            self.panel_outer_frames.append(outer)
            self.panel_frames.append(self._crear_panel_desplazable(outer))

        # Ocultar paneles al inicio
        self.hide_all_frames()

        # Inicializar variable
        self.setup_variables()
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
        self.apply_settings(self.settings)
        
        # Para recordar cuál panel está abierto
        self.active_panel = None
        self.is_animating = False
        # NUEVO: se incrementa cada vez que toggle_panel arranca una
        # acción nueva (abrir/cerrar/cambiar de panel). Cada animación
        # en curso (animate_panel_open/close) guarda el valor que tenía
        # este contador al arrancar, y en cada paso se fija si sigue
        # siendo el mismo — si no, significa que otra acción la
        # interrumpió, y esa corrida vieja se aborta sola en vez de
        # seguir escribiendo sobre frame1/el panel al mismo tiempo que
        # la animación nueva. Ver toggle_panel/animate_panel_open/close.
        self._panel_anim_token = 0

        # Inicializar componentes
        self.menu_bar.setup()
        self.setup_ribbon()
        self.setup_status_bar()
        self.resultados(self.frame4)
        self.temp_sombra(self.frame5)
        self.imagen(self.frame2)
        self.curva_de_nivel(self.frame3)
        self.activar_mouse()
        self.setup_startup_screen()
        self.show_startup_screen()
    
    
    def activar_mouse(self):
        # Vincular eventos de mouse
        self.canvas1.mpl_connect('button_press_event', self.shape_selector.on_mouse_press)
        self.canvas1.mpl_connect('motion_notify_event', self.shape_selector.on_mouse_move)
        self.canvas1.mpl_connect('button_release_event', self.shape_selector.on_mouse_release)
    
    def setup_startup_screen(self):
        """Pantalla de inicio — REDISEÑADA.

        Antes: título + subtítulo + 2 botones + unidades, todo gridado
        pegado arriba-izquierda de startup_frame, sin nada que centre
        el contenido — con la ventana grande (ahora maximizada por
        defecto) eso dejaba mucho espacio en blanco alrededor, y con
        una ventana chica el contenido se veía apretado (la captura que
        compartiste). Ahora es una tarjeta centrada, con logo y
        jerarquía tipográfica clara (Heading/Muted de ui/theme.py) —
        se ve igual de bien maximizada o no.
        """
        for widget in self.startup_frame.winfo_children():
            widget.destroy()
        self.startup_frame.configure(bg=self.palette["background"])
        self.startup_frame.grid_rowconfigure(0, weight=1)
        self.startup_frame.grid_columnconfigure(0, weight=1)

        card = tk.Frame(
            self.startup_frame, bg=self.palette["panel"],
            highlightbackground=self.palette["border"], highlightthickness=1,
        )
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        logo = icon_factory.obtener_icono("logo", size=56, color=self.palette["primario"])
        logo_lbl = tk.Label(card, image=logo, bg=self.palette["panel"])
        logo_lbl.image = logo
        logo_lbl.grid(row=0, column=0, pady=(30, 10))

        ttk.Label(
            card, text="Análisis de sombra y confort térmico",
            style="Heading.TLabel",
        ).grid(row=1, column=0, padx=40, pady=(0, 2))
        ttk.Label(
            card, text="Creá o abrí un proyecto para empezar.",
            style="Muted.TLabel",
        ).grid(row=2, column=0, padx=40, pady=(0, 22))

        ttk.Button(
            card, text="Crear proyecto nuevo", style="Success.TButton",
            command=self.new_project, width=26,
        ).grid(row=3, column=0, padx=40, pady=(0, 8))
        ttk.Button(
            card, text="Abrir proyecto existente", style="Primary.TButton",
            command=self.open_project, width=26,
        ).grid(row=4, column=0, padx=40, pady=(0, 30))

    def _mostrar_dialogo_primeras_configuraciones(self, on_continuar):
        """NUEVO. Antes "Primeras configuraciones" (unidades de
        temperatura/distancia) vivía siempre visible en la pantalla de
        inicio, incluso antes de elegir crear o abrir algo. Ahora es un
        paso propio que solo aparece al elegir "Nuevo proyecto" — tiene
        sentido ahí porque son las unidades CON LAS QUE se va a trabajar
        ese proyecto, no una configuración global de la pantalla vacía.
        """
        dialogo = tk.Toplevel(self.root)
        dialogo.title("Primeras configuraciones")
        dialogo.configure(bg=self.palette["panel"])
        dialogo.transient(self.root)
        dialogo.grab_set()
        dialogo.resizable(False, False)

        ttk.Label(
            dialogo, text="Primeras configuraciones", style="Heading.TLabel",
        ).grid(row=0, column=0, padx=24, pady=(18, 4), sticky="w")
        ttk.Label(
            dialogo, text="Unidades de trabajo para el proyecto nuevo.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, padx=24, pady=(0, 14), sticky="w")

        ttk.Label(dialogo, text="Temperatura").grid(row=2, column=0, padx=24, sticky="w")
        temp_combo = ttk.Combobox(
            dialogo, textvariable=self.temp_unit, values=["C", "F", "K"],
            state="readonly", width=10,
        )
        temp_combo.grid(row=3, column=0, padx=24, pady=(2, 10), sticky="w")

        ttk.Label(dialogo, text="Distancia").grid(row=4, column=0, padx=24, sticky="w")
        distance_combo = ttk.Combobox(
            dialogo, textvariable=self.distance_unit,
            values=["cm", "m", "km", "in", "ft", "yd", "mi"],
            state="readonly", width=10,
        )
        distance_combo.grid(row=5, column=0, padx=24, pady=(2, 18), sticky="w")

        def _continuar():
            self._save_unit_settings()
            dialogo.destroy()
            on_continuar()

        botones = tk.Frame(dialogo, bg=self.palette["panel"])
        botones.grid(row=6, column=0, padx=24, pady=(0, 18), sticky="e")
        ttk.Button(botones, text="Cancelar", command=dialogo.destroy).pack(side="left", padx=6)
        ttk.Button(
            botones, text="Continuar", command=_continuar, style="Success.TButton",
        ).pack(side="left")

        dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)

    def show_startup_screen(self):
        self.hide_all_frames()
        self.set_project_ui_enabled(False)
        self.startup_frame.grid(row=1, column=1, columnspan=2, rowspan=3, sticky="nsew", padx=30, pady=30)
        if hasattr(self, "entry_lat") and self.entry_lat:
            self.entry_lat.config(state="disabled")
        if hasattr(self, "entry_lon") and self.entry_lon:
            self.entry_lon.config(state="disabled")

    def hide_startup_screen(self):
        self.startup_frame.grid_remove()

    def on_project_loaded(self):
        self.hide_startup_screen()
        self.set_project_ui_enabled(True)
        self.update_status_saved_time()
        if self.current_location:
            self._update_location_labels()

    def set_project_ui_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in getattr(self, "buttons", []):
            button.config(state=state)
        if hasattr(self, "calculate_temp_button"):
            self.calculate_temp_button.config(state=state)
        if hasattr(self, "cargar_imagen_button"):
            self.cargar_imagen_button.config(state=state)

    def require_project(self, action_label: str) -> bool:
        if self.project_manager.current_project is None:
            messagebox.showwarning("Proyecto requerido", f"Debe crear o abrir un proyecto para {action_label}.")
            return False
        return True

    def _run_with_project(self, action_label: str, callback):
        if not self.require_project(action_label):
            return
        callback()

    def apply_project_location(self, location: dict) -> None:
        self.current_location = location
        lat = float(location.get("lat", 0))
        lon = float(location.get("lon", 0))
        self.vars["lat"].set(lat)
        self.vars["lon"].set(lon)
        self.vars_modelo["lat"].set(lat)
        self.vars_modelo["lon"].set(lon)
        self.vars["_update_required"] = True
        self.vars_modelo["_update_required"] = True
        if hasattr(self, "entry_lat") and self.entry_lat:
            self.entry_lat.config(state="normal")
            self.entry_lat.delete(0, tk.END)
            self.entry_lat.insert(0, str(lat))
            self.entry_lat.config(state="disabled")
        if hasattr(self, "entry_lon") and self.entry_lon:
            self.entry_lon.config(state="normal")
            self.entry_lon.delete(0, tk.END)
            self.entry_lon.insert(0, str(lon))
            self.entry_lon.config(state="disabled")
        if self.locations_data:
            self.simple_country.set(location.get("country", ""))
            self._update_city_options()
            label = location.get("city", "")
            if location.get("province"):
                label = f"{label} ({location.get('province')})"
            self.simple_city.set(label)
            if hasattr(self, "country_combo"):
                self.country_combo.config(state="disabled")
            if hasattr(self, "city_combo"):
                self.city_combo.config(state="disabled")
            if hasattr(self, "apply_location_button"):
                self.apply_location_button.config(state="disabled")
        self._update_location_labels()

    def _update_location_labels(self):
        if not self.current_location:
            return
        city = self.current_location.get("city", "")
        province = self.current_location.get("province", "")
        country = self.current_location.get("country", "")
        location_label = f"{city} ({province}) - {country}" if province else f"{city} - {country}"
        if hasattr(self, "edit_location_label"):
            self.edit_location_label.config(text=location_label)
        if hasattr(self, "edit_latlon_label"):
            self.edit_latlon_label.config(
                text=f"Lat/Lon: {self.current_location.get('lat', 0)}, {self.current_location.get('lon', 0)}"
            )

    def restore_project_artifacts(self):
        self.poblar_lista_snapshots()
        if self.snapshots:
            # Selecciona y carga el último elemento analizado —
            # equivalente a lo que hacía antes (imagen+curva+máscara),
            # pero ahora también restaura % de sombra y la barra de Tmrt,
            # y el resto del historial queda disponible para elegir.
            ultimo = len(self.snapshots) - 1
            self.snapshot_listbox.selection_clear(0, tk.END)
            self.snapshot_listbox.selection_set(ultimo)
            self.snapshot_listbox.see(ultimo)
            self.cargar_snapshot(ultimo)
        else:
            # Proyecto sin snapshots todavía: mantener el comportamiento
            # anterior por si hay rutas sueltas guardadas.
            self.last_image_path = self._resolve_artifact_path(self.last_image_path, "imagenes")
            self.last_curve_path = self._resolve_artifact_path(self.last_curve_path, os.path.join("resultados", "curvas_nivel"))
            self.last_mask_path = self._resolve_artifact_path(self.last_mask_path, "mascaras")
            if self.last_image_path and os.path.exists(self.last_image_path):
                self._load_image_from_path(self.last_image_path)
            if self.last_curve_path and os.path.exists(self.last_curve_path):
                self._load_curve_from_path(self.last_curve_path)
            if self.last_mask_path and os.path.exists(self.last_mask_path):
                self._load_mask_from_path(self.last_mask_path)
        self._restore_excel_files()

    def _restore_excel_files(self):
        self.last_edit_excel_path = self._resolve_artifact_path(self.last_edit_excel_path, "Planos")
        self.last_model_excel_path = self._resolve_artifact_path(self.last_model_excel_path, "modelos")
        if self.last_edit_excel_path and os.path.exists(self.last_edit_excel_path):
            # abrir_archivo ya regenera el gráfico de edición internamente
            # (llama a actualizar_grafico al final) — no hace falta nada más acá.
            loaded = design.abrir_archivo(self.vars, self, filepath=self.last_edit_excel_path)
            if loaded:
                self.last_edit_excel_path = loaded
        if self.last_model_excel_path and os.path.exists(self.last_model_excel_path):
            loaded = modelo.cargar_excel(self.vars_modelo, filepath=self.last_model_excel_path)
            if loaded:
                self.last_model_excel_path = loaded
                # NUEVO: cargar_excel() solo llena vars_modelo, no vuelve a
                # dibujar nada — el modelo quedaba con datos cargados pero
                # invisible hasta que el usuario tocara algún control a
                # mano. Se regenera acá con el mismo método que usa el
                # botón "Ejecutar modelo", para que quede consistente con
                # la ubicación/modo ya restaurados del proyecto.
                try:
                    self.generar_grafico_modelo()
                except Exception as exc:
                    print(f"[restore] No se pudo regenerar el gráfico del modelo automáticamente: {exc}")

    def _resolve_artifact_path(self, path_value, folder, filename=None):
        if path_value and os.path.exists(path_value):
            return path_value
        project = self.project_manager.current_project
        if not project:
            return path_value
        if filename:
            candidate = os.path.join(project.root_path, folder, filename)
        else:
            candidate = os.path.join(project.root_path, folder, os.path.basename(path_value)) if path_value else None
        if candidate and os.path.exists(candidate):
            return candidate
        return path_value

    def poblar_lista_snapshots(self):
        """Refresca el Listbox de historial con self.snapshots.

        NUEVO. Se llama después de guardar un snapshot y después de abrir
        un proyecto, para que el historial de elementos analizados quede
        siempre sincronizado con lo que hay guardado.
        """
        if not hasattr(self, "snapshot_listbox"):
            return
        self.snapshot_listbox.delete(0, tk.END)
        for entry in self.snapshots:
            etiqueta = entry.get("label") or f"elemento{entry.get('n', '?')}"
            sombra = entry.get("porcentaje_sombra")
            sombra_txt = f" — {sombra:.0f}% sombra" if isinstance(sombra, (int, float)) else ""
            self.snapshot_listbox.insert(tk.END, f"{etiqueta}{sombra_txt}")
        if hasattr(self, "status_elements_var"):
            self.status_elements_var.set(f"Elementos: {len(self.snapshots)}")

    def _on_snapshot_select(self, _event=None):
        seleccion = self.snapshot_listbox.curselection()
        if not seleccion:
            return
        self.cargar_snapshot(seleccion[0])

    def cargar_snapshot(self, index: int):
        """Recarga TODO lo asociado a un elemento del historial: imagen,
        selección de sombra (matriz), área de referencia, curva de nivel,
        histograma, y la barra de temperatura calculada en "Calcular
        temperatura en sombra" (redibujada a partir de los valores
        guardados, no una imagen estática).

        NUEVO — antes solo se restauraba el ÚLTIMO elemento guardado del
        proyecto (una sola imagen), sin poder volver a ninguno anterior.
        """
        if index < 0 or index >= len(self.snapshots):
            return
        entry = self.snapshots[index]
        project = self.project_manager.current_project
        if not project:
            return
        root = project.root_path

        def _abs(rel_path):
            if not rel_path:
                return None
            return rel_path if os.path.isabs(rel_path) else os.path.join(root, rel_path)

        image_path = _abs(entry.get("image"))
        curve_path = _abs(entry.get("curve"))
        reference_path = _abs(entry.get("reference"))
        matrix_path = _abs(entry.get("matrix"))
        histogram_path = _abs(entry.get("histogram"))

        if image_path and os.path.exists(image_path):
            self._load_image_from_path(image_path)
        if curve_path and os.path.exists(curve_path):
            self._load_curve_from_path(curve_path)
        if reference_path and os.path.exists(reference_path):
            self._load_mask_from_path(reference_path)
        if matrix_path and os.path.exists(matrix_path):
            try:
                self.shape_selector.area_seleccionada = pd.read_excel(matrix_path).to_numpy()
                self.last_matrix_path = matrix_path
            except Exception:
                pass
        if histogram_path and os.path.exists(histogram_path):
            self.last_histogram_path = histogram_path

        sombra = entry.get("porcentaje_sombra")
        self.porcentaje_sombra = sombra
        if isinstance(sombra, (int, float)):
            self.lbl_porcentaje_sombra.config(text=f"Porcentaje de sombra: {sombra:.2f}%")

        # Redibujar la barra de temperatura a partir de los valores
        # guardados en el snapshot (más confiable que depender de una
        # imagen exportada, y consistente con calculate_temperature_in_shade).
        tmrt_sombra = entry.get("tmrt_sombra")
        temp_ambient = entry.get("temp_ambient")
        if tmrt_sombra is not None and temp_ambient is not None:
            self.tmrt_result = {
                "Tmrt_sol": entry.get("tmrt_sol"),
                "Tmrt_sombra": tmrt_sombra,
                "Delta_Tmrt": entry.get("delta_tmrt"),
            }
            if hasattr(self, "lbl_tmrt_sol") and entry.get("tmrt_sol") is not None:
                self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {entry['tmrt_sol']:.2f} °C")
            if hasattr(self, "lbl_tmrt_sombra"):
                self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {tmrt_sombra:.2f} °C")
            if hasattr(self, "lbl_delta_tmrt") and entry.get("delta_tmrt") is not None:
                self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {entry['delta_tmrt']:.2f} °C")
            if hasattr(self, "graph_frame"):
                for widget in self.graph_frame.winfo_children():
                    widget.destroy()
                graph = TemperatureGraph(temp_ambient, tmrt_sombra, self.graph_frame)
                graph.plot_temperature_scale()

        self.curve_button.config(state=tk.NORMAL)
        self.excel_button.config(state=tk.NORMAL)
        self.pdf_button.config(state=tk.NORMAL)

    def _load_image_from_path(self, file_path: str):
        #self.img, self.img_rgb = self.image_processor.load_image(file_path)
        try:
            self.img, self.img_rgb = self.image_processor.load_image(file_path)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return        
        self.original_rgb = self.img_rgb
        self.last_image_path = file_path
        self.current_image_path = file_path
        self.current_image_basename = os.path.basename(file_path)
        self.current_image_stem = os.path.splitext(self.current_image_basename)[0]
        self._ensure_panel2_image_canvas()
        if hasattr(self, "ax1"):
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self._setup_hover_shadow_percent_photo(self.ax1, self.canvas1, self.img_rgb)
            self.canvas1.draw()
        self.shape_selector.enable_calculo_button()
        self.cargar_imagen_button.config(text="Cargar nueva imagen")

    def save_loaded_image_to_project(self, source_path: str) -> str:
        project = self.project_manager.current_project
        if project is None:
            raise RuntimeError("No hay proyecto abierto")
        project.ensure_structure()
        basename = os.path.basename(source_path)
        image_dir = os.path.join(project.root_path, "imagenes")
        os.makedirs(image_dir, exist_ok=True)
        destination_path = safe_path(image_dir, basename)
        print(f"[panel2] Copiando imagen a proyecto: {source_path} -> {destination_path}")
        if os.path.abspath(source_path) != os.path.abspath(str(destination_path)):
            shutil.copy2(source_path, destination_path)
        if not os.path.exists(destination_path):
            raise FileNotFoundError(f"No se pudo copiar la imagen a {destination_path}")

        destination_str = str(destination_path)
        destination_basename = os.path.basename(destination_str)
        self.current_image_path = destination_str
        self.current_image_basename = destination_basename
        self.current_image_stem = os.path.splitext(destination_basename)[0]
        self.last_image_path = destination_str
        return destination_str

    def _copy_image_to_project(self, source_path: str) -> str:
        return self.save_loaded_image_to_project(source_path)

    def _copy_excel_to_project(self, source_path: str, folder: str) -> str:
        project = self.project_manager.current_project
        if project is None:
            raise RuntimeError("No hay proyecto abierto")
        target_dir = os.path.join(project.root_path, folder)
        destination = safe_path(target_dir, os.path.basename(source_path))
        shutil.copy2(source_path, destination)
        return str(destination)

    def _reset_panel2_for_new_image(self):
        self.shape_selector.clear_panel2_selection()
        self.drawing_mode = None
        self.selection_mode = None
        self.area_calculo_done = False
        self.area_referencia_done = False
        self.porcentaje_sombra = None
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.curvas_nivel_creadas = False
        self.lbl_porcentaje_sombra.config(text="Porcentaje de sombra: N/A")
        self.lbl_dimensiones_calculo.config(text="Dimensiones del Área de Cálculo: N/A")
        self.lbl_dimensiones_referencia.config(text="Dimensiones del Área de Referencia: N/A")
        self.lbl_promedio_referencia.config(text="Promedio Gris Referencia: N/A")
        self.confirm_button.config(state=tk.DISABLED)
        self.curve_button.config(state=tk.DISABLED)
        self.excel_button.config(state=tk.DISABLED)
        self.pdf_button.config(state=tk.DISABLED)
        self.area_ref_button.config(state=tk.DISABLED)
        self.shape_selector.enable_calculo_button()
        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None
            self.curva_img_pil_original = None
        if hasattr(self, "ax2") and self.ax2 is not None:
            self.ax2.clear()
        if self.canvas2 is not None:
            widget = self.canvas2.get_tk_widget()
            if widget.winfo_exists():
                widget.pack(side=tk.RIGHT)
                self.canvas2.draw_idle()
                
    def _load_curve_from_path(self, file_path: str):
        if not self.curva_frame:
            return
        # CORRECCIÓN: canvas2 es un lienzo vacío (ejes 0-1 en blanco) que
        # _reset_panel2_for_new_image() vuelve a mostrar como placeholder.
        # mostrar_curvas_nivel() ya lo ocultaba al generar una curva nueva,
        # pero esta función (usada al restaurar un proyecto o un elemento
        # del historial) no lo hacía — quedaba packed al lado de la curva
        # real, achicándola. Es exactamente lo que se ve en el frame en
        # blanco de la captura.
        if self.canvas2 is not None:
            self.canvas2.get_tk_widget().pack_forget()
        img = Image.open(file_path)
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

    def _load_mask_from_path(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in (".xlsx", ".xls"):
                data = pd.read_excel(file_path)
                self.shape_selector.area_referencia = data.to_numpy()
            elif ext in (".png", ".jpg", ".jpeg"):
                self.shape_selector.area_referencia = np.array(Image.open(file_path).convert("L"))
        except Exception:
            return
        
    def setup_variables(self):
        """Inicializa las variables de control para la aplicación"""
        self.selection_type = tk.StringVar(value="Polígono")
        self.matriz_size = tk.IntVar(value=480)
        self.panel2_advanced_mode = tk.BooleanVar(value=False)        
        self.drawing_mode = None
        self.selection_mode = None
        self.img = None
        self.img_rgb = None
        self.current_image_path = None
        self.current_image_basename = None
        self.current_image_stem = None
        self.area_calculo_done = False
        self.area_referencia_done = False
        self.entries =[]
        self.modo = None
        self.vars = self._build_vars()
        self.vars_modelo = self._build_vars()
        self.modo_modelo = tk.StringVar(value="simple")
        self.modo_edicion = tk.StringVar(value="simple")
        self.panel2_advanced_mode = tk.BooleanVar(value=False)
        self.simple_country = tk.StringVar()
        self.simple_city = tk.StringVar()
        self.simple_cloudiness = tk.StringVar(value="Despejado")
        self.simple_temp_air_c = tk.DoubleVar(value=25.0)
        self.temp_unit = tk.StringVar(value=self.settings.get("temp_unit", self.settings.get("units", "C")))
        self.distance_unit = tk.StringVar(value=self.settings.get("distance_unit", "m"))
        self.locations_path = os.path.join(self.base_dir, "data", "locations_latam.csv")
        self.locations_data, self.locations_error = LocationService(self.locations_path).load()
        if self.locations_data and self.locations_data["countries"]:
            self.simple_country.set(self.locations_data["countries"][0])
        # Controles de parámetros
        self.controles = self._build_controles(self.vars)
        self.controles_modelo = self._build_controles(self.vars_modelo)

    def apply_settings(self, settings):
        """Aplica preferencias usando el gestor de settings."""
        self.settings = settings
        self.settings_manager.apply_to_app(self, settings)

    def mark_dirty(self):
        self.is_dirty = True

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

        # NUEVO: porcentaje de sombra manual. Antes "Calcular temperatura
        # en sombra" exigía haber cargado una imagen y procesado la
        # selección en el Panel 2 (self.porcentaje_sombra solo se
        # llenaba ahí). Con este campo se puede calcular Tmrt para
        # cualquier % de sombra hipotético sin pasar por una imagen —
        # útil para explorar escenarios ("¿y si hubiera 60% de sombra
        # acá?") o cuando no se tiene una foto todavía. Si se deja vacío,
        # se sigue usando el % calculado desde la imagen, como antes.
        manual_label = tk.Label(
            panel, text="Porcentaje de sombra manual (%, opcional):",
            bg=panel.cget("bg"), fg="black",
        )
        manual_label.pack(anchor="w", padx=20, pady=(15, 5))
        self.entry_porcentaje_manual = tk.Entry(panel)
        self.entry_porcentaje_manual.pack(anchor="w", padx=20, pady=5)
        manual_hint = tk.Label(
            panel,
            text="Si se completa, se usa en vez del % calculado en el Panel 2.",
            bg=panel.cget("bg"), fg="#666666", font=("Arial", 8),
        )
        manual_hint.pack(anchor="w", padx=20, pady=(0, 5))

        self.calculate_temp_button = tk.Button(
            panel,
            text="Calcular temperatura en sombra",
            command=self.calculate_temperature_in_shade,
        )
        self.calculate_temp_button.pack(padx=20, pady=20)
    def setup_panel_2(self):
        """Configura el contenido del Panel 2"""
        panel = self.panel_frames[1]

        # Botone para cargar la imagen a analizar 
        self.cargar_imagen_button = tk.Button(
            panel,
            text="Cargar imagen",
            command=self.cargar_imagen,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.cargar_imagen_button.pack(anchor="w", padx=20, pady=10)
        self.panel2_advanced_check = tk.Checkbutton(
            panel,
            text="Modo avanzado\n(tamaño de matriz)",
            justify="left",
            variable=self.panel2_advanced_mode,
            bg=panel.cget("bg"),
            command=self._toggle_panel2_advanced,
        )
        self.panel2_advanced_check.pack(anchor="w", padx=20, pady=4)
        self.shadow_detector_check = tk.Checkbutton(
            panel,
            text="Detector sombras reales (experimental)",
            variable=self.shadow_detector_enabled,
            bg=panel.cget("bg"),
        )
        self.shadow_detector_check.pack(anchor="w", padx=20, pady=2)

        # Selección del tamaño de la matriz
        matrix_label = tk.Label(panel, text="Seleccione el tamaño de la matriz:", bg=panel.cget("bg"), fg="black")
        matrix_label.pack(anchor="w", padx=20, pady=10)

        self.matrix_size_combo = ttk.Combobox(
            panel,
            textvariable=self.matriz_size,
            values=[480, 640, 800, 1024],
            state="readonly",
        )
        self.matrix_size_combo.pack(anchor="w", padx=20, pady=5)

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
        self.excel_button.pack(anchor="w", padx=20, pady=10)

        self.pdf_button = tk.Button(panel, text="Exportar a informe PDF", command=self.exportar_a_pdf, state=tk.DISABLED)
        self.pdf_button.pack(anchor="w", padx=20, pady=10)
        
        self.save_dataset_button = tk.Button(panel, text="Guardar Dataset", command=self.save_dataset, state=tk.DISABLED)
        self.save_dataset_button.pack(anchor="w", padx=20, pady=10)

        # NUEVO: historial de elementos analizados en este proyecto.
        # Cada vez que se guarda un snapshot (imagen + sombra + curva +
        # Tmrt), queda listado acá. Un click carga todo ese análisis de
        # nuevo: imagen, selección de sombra, área de referencia, curva
        # de nivel y la barra de temperatura calculada — sin tener que
        # rehacer el cálculo.
        historial_label = tk.Label(panel, text="Historial de elementos:", bg=panel.cget("bg"), fg="black")
        historial_label.pack(anchor="w", padx=20, pady=(20, 4))

        historial_frame = tk.Frame(panel, bg=panel.cget("bg"))
        historial_frame.pack(anchor="w", padx=20, pady=(0, 10), fill="x")

        historial_scroll = tk.Scrollbar(historial_frame, orient=tk.VERTICAL)
        self.snapshot_listbox = tk.Listbox(
            historial_frame, height=6, width=32,
            yscrollcommand=historial_scroll.set, exportselection=False,
        )
        historial_scroll.config(command=self.snapshot_listbox.yview)
        self.snapshot_listbox.pack(side=tk.LEFT, fill="x", expand=True)
        historial_scroll.pack(side=tk.RIGHT, fill="y")
        self.snapshot_listbox.bind("<<ListboxSelect>>", self._on_snapshot_select)
        self.poblar_lista_snapshots()

        self._toggle_panel2_advanced()
        
    def setup_panel_3(self):
        """Configura el contenido del Panel 3"""
        panel = self.panel_frames[2]

        for widget in panel.winfo_children():
            widget.destroy()        

        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)
        contenido = self._build_scrollable_content(panel)
        contenido.grid_columnconfigure(0, weight=1)

        diseno_label = tk.Label(contenido, text="Modo de Edición:", bg=panel.cget("bg"), fg="black")
        diseno_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        acciones = tk.Frame(contenido, bg=panel.cget("bg"))
        acciones.grid(row=1, column=0, sticky="ew", pady=4)
        acciones.grid_columnconfigure(0, weight=1)
        

        # Botones principales
        add_arbol = tk.Button(
            acciones,
            text="Añadir Árbol",
            command=lambda: self._run_with_project("editar la escena", lambda: design.establecer_modo('arbol', self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        add_arbol.grid(row=0, column=0, sticky="w", padx=0, pady=3)

        add_estructura = tk.Button(
            acciones,
            text="Añadir Estructura",
            command=lambda: self._run_with_project("editar la escena", lambda: design.establecer_modo('estructura', self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        add_estructura.grid(row=1, column=0, sticky="w", padx=0, pady=3)

        seleccionar = tk.Button(
            acciones,
            text="Seleccionar",
            command=lambda: self._run_with_project("editar la escena", lambda: design.establecer_modo(None, self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        seleccionar.grid(row=2, column=0, sticky="w", pady=3)

        guardar = tk.Button(
            acciones,
            text="Guardar como",
            command=lambda: self._run_with_project("guardar el archivo de edición", lambda: design.guardar_como(self.vars, self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        guardar.grid(row=3, column=0, sticky="w", padx=0, pady=6)

        abrir = tk.Button(
            acciones,
            text="Abrir",
            command=lambda: self.abrir_excel_edicion(),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        abrir.grid(row=4, column=0, sticky="w", padx=0, pady=6)

        grafico = tk.Button(
            acciones,
            text="Generar gráfico",
            command=lambda: self._run_with_project("generar el gráfico de edición", lambda: self.actualizar_grafico_diseno(self.frame7)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        grafico.grid(row=5, column=0, sticky="w", padx=0, pady=4)

        vista_3d = tk.Button(
            acciones,
            text="Vista 3D",
            command=lambda: self._run_with_project("generar la vista 3D", lambda: design.generar_3d(self.vars)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        vista_3d.grid(row=6, column=0, sticky="w", padx=0, pady=4)

        modo_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        modo_frame.grid(row=2, column=0, sticky="w", pady=4)
        tk.Radiobutton(
            modo_frame,
            text="Modo Simple",
            variable=self.modo_edicion,
            value="simple",
            bg=panel.cget("bg"),
            command=self._toggle_edicion_mode,
        ).grid(row=0, column=0, sticky="w")
        tk.Radiobutton(
            modo_frame,
            text="Modo Avanzado",
            variable=self.modo_edicion,
            value="advanced",
            bg=panel.cget("bg"),
            command=self._toggle_edicion_mode,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.simple_edit_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        self.simple_edit_frame.grid(row=3, column=0, sticky="nsew", pady=6)
        self.simple_edit_frame.grid_columnconfigure(1, weight=1)
        tk.Label(self.simple_edit_frame, text="Ubicación fija del proyecto", bg=panel.cget("bg")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        self.edit_location_label = tk.Label(self.simple_edit_frame, text="Sin proyecto", bg=panel.cget("bg"))
        self.edit_location_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        self.edit_latlon_label = tk.Label(self.simple_edit_frame, text="", bg=panel.cget("bg"))
        self.edit_latlon_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        self.advanced_edit_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        self.advanced_edit_frame.grid(row=3, column=0, sticky="nsew", pady=6)
        self.advanced_edit_frame.grid_columnconfigure(0, weight=1)

        label_viento = tk.Label(self.advanced_edit_frame, text="Viento", bg=panel.cget("bg"))
        label_viento.grid(row=0, column=0, sticky="w", pady=(8, 2))
        ttk.Combobox(
            self.advanced_edit_frame,
            textvariable=self.vars["viento"],
            values=["nulo", "moderado", "fuerte"],
        ).grid(row=1, column=0, sticky="ew", pady=2)

        panelin = tk.Frame(self.advanced_edit_frame, bg=panel.cget("bg"))
        panelin.grid(row=2, column=0, sticky="nsew", pady=6)
        for texto, var, fila, rango, es_fecha in self.controles:
            self.crear_control(panelin, texto, var, fila, rango, es_fecha)
        self._toggle_edicion_mode()    
    def setup_panel_4(self):
        """Configura el contenido del Panel 4"""
        panel = self.panel_frames[3]
        
        
        for widget in panel.winfo_children():
            widget.destroy()        

        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)
        contenido = self._build_scrollable_content(panel)
        contenido.grid_columnconfigure(0, weight=1)

        diseno_label = tk.Label(contenido, text="Modelo", bg=panel.cget("bg"), fg="black")
        diseno_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        modo_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        modo_frame.grid(row=1, column=0, sticky="w", pady=4)
        self.simple_mode_radio = tk.Radiobutton(
            modo_frame,
            text="Modo Simple",
            variable=self.modo_modelo,
            value="simple",
            bg=panel.cget("bg"),
            command=self._toggle_modelo_mode,
        )
        self.simple_mode_radio.grid(row=0, column=0, sticky="w")
        self.advanced_mode_radio = tk.Radiobutton(
            modo_frame,
            text="Modo Avanzado",
            variable=self.modo_modelo,
            value="advanced",
            bg=panel.cget("bg"),
            command=self._toggle_modelo_mode,
        )
        self.advanced_mode_radio.grid(row=1, column=0, sticky="w", pady=(2, 0))

        acciones_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        acciones_frame.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.apply_location_button = tk.Button(
            acciones_frame,
            text="Aplicar ubicación",
            command=lambda: self._apply_location(True),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
            state="normal" if self.locations_data else "disabled",
        )
        self.apply_location_button.grid(row=0, column=0, sticky="w", padx=0, pady=3)
        tk.Button(
            acciones_frame,
            text="Cargar Excel",
            command=self.cargar_excel_modelo,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=0, pady=3)
        tk.Button(
            acciones_frame,
            text="Guardar Excel",
            command=self.guardar_excel_modelo,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=0, pady=3)        
        tk.Button(
            acciones_frame,
            text="Generar Gráfico",
            command=self.generar_grafico_modelo,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=3, column=0, sticky="w", padx=0, pady=3)
        tk.Button(
            acciones_frame,
            text="Vista 3D",
            command=lambda: modelo.generar_3d(self.vars_modelo),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=4, column=0, sticky="w", padx=0, pady=3)

        self.simple_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        self.simple_frame.grid(row=2, column=0, sticky="nsew", pady=6)
        self.simple_frame.grid_columnconfigure(0, weight=1)

        if self.locations_error:
            tk.Label(
                self.simple_frame,
                text=self.locations_error,
                fg="red",
                bg=panel.cget("bg"),
                wraplength=260,
                justify="left",
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=4)

        tk.Label(self.simple_frame, text="País", bg=panel.cget("bg")).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.country_combo = ttk.Combobox(
            self.simple_frame,
            textvariable=self.simple_country,
            values=self.locations_data["countries"] if self.locations_data else [],
            state="readonly" if self.locations_data else "disabled",
            width=22,
        )
        self.country_combo.grid(row=2, column=0, sticky="ew", pady=(2, 6), padx=0)
        self.country_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_city_options())

        tk.Label(self.simple_frame, text="Ciudad", bg=panel.cget("bg")).grid(row=3, column=0, sticky="w", pady=(2, 0))
        self.city_combo = ttk.Combobox(
            self.simple_frame,
            textvariable=self.simple_city,
            values=[],
            width=22,
            state="normal" if self.locations_data else "disabled",
        )
        self.city_combo.grid(row=4, column=0, sticky="ew", pady=(2, 6), padx=0)
        self.city_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_location(False))
        self.city_combo.bind("<KeyRelease>", self._filter_city_options)

        tk.Label(self.simple_frame, text="Nubosidad", bg=panel.cget("bg")).grid(row=5, column=0, sticky="w", pady=(2, 0))
        ttk.Combobox(
            self.simple_frame,
            textvariable=self.simple_cloudiness,
            values=["Despejado", "Parcial", "Nublado"],
            state="readonly",
            width=22,
        ).grid(row=6, column=0, sticky="ew", pady=(2,6), padx=0)

        tk.Label(self.simple_frame, text="Temperatura aire (°C)", bg=panel.cget("bg")).grid(row=7, column=0, sticky="w", pady=(2, 0))
        tk.Entry(self.simple_frame, textvariable=self.simple_temp_air_c, width=10).grid(
            row=8, column=0, sticky="w", pady=(2,6), padx=0
        )
        tk.Label(self.simple_frame, text="Viento", bg=panel.cget("bg")).grid(row=9, column=0, sticky="w", pady=(2, 0))
        ttk.Combobox(
            self.simple_frame,
            textvariable=self.vars_modelo["viento"],
            values=["nulo", "moderado", "fuerte"],
            width=22,
        ).grid(row=10, column=0, sticky="ew", pady=(2,6), padx=0)

        self.advanced_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        self.advanced_frame.grid(row=2, column=0, sticky="nsew", pady=6)
        self.advanced_frame.grid_columnconfigure(1, weight=1)

        tk.Label(self.advanced_frame, text="Viento", bg=panel.cget("bg")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(
            self.advanced_frame,
            textvariable=self.vars_modelo["viento"],
            values=["nulo", "moderado", "fuerte"],
            width=22,
        ).grid(row=0, column=1, sticky="ew", pady=2, padx=(8, 0))

        tk.Label(self.advanced_frame, text="Configuraciones rápidas", bg=panel.cget("bg")).grid(
            row=1, column=0, sticky="w", pady=6
        )
        tk.Button(
            self.advanced_frame,
            text="Soleado",
            command=lambda: modelo.cargar_preset("soleado", self.vars_modelo),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=0, pady=3)
        tk.Button(
            self.advanced_frame,
            text="Verano",
            command=lambda: modelo.cargar_preset("verano", self.vars),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=2, column=1, sticky="w", padx=10, pady=3)
        tk.Button(
            self.advanced_frame,
            text="Soleado",
            command=lambda: modelo.cargar_preset("soleado", self.vars),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=3, column=0, sticky="w", padx=0, pady=3)
        tk.Button(
            self.advanced_frame,
            text="Nublado",
            command=lambda: modelo.cargar_preset("nublado", self.vars),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 8, "bold"),
        ).grid(row=3, column=1, sticky="w", padx=10, pady=3)

        panelin = tk.Frame(self.advanced_frame, bg=panel.cget("bg"))
        panelin.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)
        for texto, var, fila, rango, es_fecha in self.controles_modelo:
            self.crear_control(panelin, texto, var, fila, rango, es_fecha)
        self.vars_modelo["graph_frame"] = self.frame11
        self._update_city_options()
        if self.locations_error:
            self.modo_modelo.set("advanced")
            self.simple_mode_radio.config(state="disabled")
        self._toggle_modelo_mode()  
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
    def _toggle_modelo_mode(self):
        if self.modo_modelo.get() == "simple" and not self.locations_error:
            self.advanced_frame.grid_remove()
            self.simple_frame.grid()
        else:
            self.simple_frame.grid_remove()
            self.advanced_frame.grid()
    
    def _toggle_edicion_mode(self):
        if self.modo_edicion.get() == "simple":
            self.advanced_edit_frame.grid_remove()
            self.simple_edit_frame.grid()
        else:
            self.simple_edit_frame.grid_remove()
            self.advanced_edit_frame.grid()

    def _toggle_panel2_advanced(self):
        if self.panel2_advanced_mode.get():
            self.matrix_size_combo.config(state="readonly")
        else:
            self.matriz_size.set(480)
            self.matrix_size_combo.config(state="disabled")
            
    def _build_scrollable_content(self, parent):
        canvas = tk.Canvas(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        content = tk.Frame(canvas, bg=parent.cget("bg"))
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        return content

    def _save_unit_settings(self):
        self.settings["units"] = self.temp_unit.get()
        self.settings["temp_unit"] = self.temp_unit.get()
        self.settings["distance_unit"] = self.distance_unit.get()
        self.settings_manager.write(self.settings)

    def convert_temperature_for_display(self, value):
        unit = self.settings.get("temp_unit", self.settings.get("units", "C"))
        if unit == "C":
            return value - 273.15
        if unit == "F":
            return (value - 273.15) * (9 / 5) + 32
        return value

    def get_temperature_unit_symbol(self):
        return {"C": "°C", "F": "°F", "K": "K"}.get(
            self.settings.get("temp_unit", self.settings.get("units", "C")),
            "°C",
        )

    def get_distance_unit(self):
        return self.settings.get("distance_unit", "m")

    def _update_city_options(self):
        if not self.locations_data:
            return
        country = self.simple_country.get()
        cities = self.locations_data["cities"].get(country, [])
        self.city_combo["values"] = cities
        if cities and self.simple_city.get() not in cities:
            self.simple_city.set(cities[0])

    def _filter_city_options(self, event):
        if not self.locations_data:
            return
        country = self.simple_country.get()
        query = self.simple_city.get().lower().strip()
        cities = self.locations_data["cities"].get(country, [])
        if query:
            filtered = [city for city in cities if query in city.lower()]
        else:
            filtered = cities
        self.city_combo["values"] = filtered

    def _apply_location(self, show_message):
        if not self.locations_data:
            return
        city_label = self.simple_city.get().strip()
        location = self.locations_data["lookup"].get(city_label)
        if not location:
            if show_message:
                messagebox.showwarning("Ubicación", "Seleccione una ciudad válida.")
            return
        self.vars_modelo["lat"].set(location["lat"])
        self.vars_modelo["lon"].set(location["lon"])
        self.vars_modelo["_update_required"] = True
        if show_message:
            messagebox.showinfo("Ubicación aplicada", f"Lat/Lon: {location['lat']}, {location['lon']}")

    def _validate_kelvin_input(self):
        temp_k = self.vars_modelo["T_amb_base"].get()
        if temp_k < 260 or temp_k > 330:
            temp_c = temp_k - 273.15
            return messagebox.askyesno(
                "Temperatura en Kelvin",
                f"Temp Base está en Kelvin. Equivale a {temp_c:.1f} °C. ¿Es correcto?",
            )
        return True

    def generar_grafico_modelo(self):
        if not self.require_project("generar el gráfico del modelo"):
            return
        if self.modo_modelo.get() == "simple":
            if self.locations_data:
                city_label = self.simple_city.get().strip()
                if city_label not in self.locations_data["lookup"]:
                    messagebox.showwarning("Ubicación", "Seleccione una ciudad válida antes de generar el gráfico.")
                    return
            self._apply_location(False)
            try:
                temp_air_c = float(self.simple_temp_air_c.get())
            except (TypeError, ValueError):
                messagebox.showerror("Temperatura inválida", "Ingrese la temperatura del aire en °C.")
                return
            temp_air_k = temp_air_c + 273.15
            cloudiness = self.simple_cloudiness.get()
            rad_map = {"Despejado": 950, "Parcial": 650, "Nublado": 250}
            i_max = rad_map.get(cloudiness, 650)
            self.vars_modelo["T_amb_base"].set(temp_air_k)
            self.vars_modelo["I_sol_base"].set(i_max)
            self.vars_modelo["nubosidad"] = cloudiness
        else:
            if not self._validate_kelvin_input():
                return
        result = modelo.generar_grafico(self.vars_modelo, self.frame11)
        if result:
            self.last_T = result.get("T")
            self.last_shadow = result.get("shadow")
            self.last_meta = result.get("meta")
    def _crear_panel_desplazable(self, contenedor):
        """Envuelve el contenido de un panel lateral en un Canvas +
        Scrollbar vertical.

        POR QUÉ: los paneles 1, 2 y 4 tienen más controles de los que
        entran en el alto de la pantalla — antes lo que no entraba
        quedaba directamente invisible, sin ninguna forma de llegar a
        eso (no había scroll). Ahora sí.

        Devuelve el FRAME INTERNO donde hay que empacar los widgets del
        panel — setup_panel_1/2/3/4 ya hacen exactamente eso
        (`panel = self.panel_frames[i]` + `.pack(...)`), sin ningún
        cambio en esas funciones.

        AJUSTE DE ANCHO: el bind de "<Configure>" del canvas fuerza al
        frame interno a medir lo mismo que el canvas visible — así los
        widgets empacados con `fill="x"` (comboboxes, entries anchos)
        se ajustan al ancho real del panel en vez de quedarse cortados
        o sobrar espacio vacío a la derecha.
        """
        canvas = tk.Canvas(contenedor, bg=self.palette["panel"], highlightthickness=0)
        scrollbar = tk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        contenido = tk.Frame(canvas, bg=self.palette["panel"])

        # Cada vez que el contenido cambia de tamaño (se agregan/sacan
        # widgets), actualizar la región scrolleable.
        contenido.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        ventana_id = canvas.create_window((0, 0), window=contenido, anchor="nw")
        # Ajuste de ancho (ver docstring): el frame interno copia el
        # ancho del canvas cada vez que este cambia.
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(ventana_id, width=e.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scroll con la rueda del mouse — se activa/desactiva solo
        # mientras el puntero está sobre ESTE panel en particular, para
        # no interceptar el scroll de otras partes de la ventana.
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        return contenido

    def toggle_panel(self, index):
        """Abre, cierra, o cambia de panel lateral.

        BUG CORREGIDO ("conflicto al tocar los íconos"): antes, para
        cambiar de un panel a otro, se cerraba el viejo y se programaba
        abrir el nuevo con `frame1.after(250, ...)` — un tiempo fijo
        inventado que NO espera a que la animación de cierre realmente
        termine. animate_panel_close reduce el ancho de a 10px cada
        10ms, así que con un panel de, por ejemplo, 260px de ancho, el
        cierre tarda 260ms — MÁS que los 250ms de espera. Resultado: el
        open_panel del panel nuevo arrancaba mientras el close_panel
        del viejo todavía estaba corriendo, y las dos animaciones
        terminaban escribiendo `frame1.config(width=...)` una encima de
        la otra — de ahí el conflicto visual.

        Ahora close_panel() recibe un callback `on_complete` y recién
        llama a open_panel() cuando el cierre TERMINÓ de verdad — sin
        adivinar tiempos. Además, cualquier clic nuevo invalida
        cualquier animación vieja todavía en curso (ver
        self._panel_anim_token), así que ya no hace falta bloquear el
        clic con `if self.is_animating: return` — un clic de más ya no
        puede corromper nada, como mucho reinicia la animación.
        """
        if not self.require_project("acceder a los paneles"):
            return
        self._panel_anim_token += 1  # invalida cualquier animación en curso

        if self.active_panel is not None and self.active_panel != index:
            self.close_panel(self.active_panel, on_complete=lambda: self.open_panel(index))
        elif self.active_panel == index:
            self.close_panel(self.active_panel)
            self.active_panel = None
        else:
            self.open_panel(index)

    def open_panel(self, index):
        """Abre (despliega) el panel lateral 'index' (0-3).

        GEOMETRÍA (bug corregido en la vuelta anterior): frame1 se crea
        con un ancho fijo de apenas 100px — suficiente para la columna
        de íconos sola, pero NO para columna de íconos + panel
        desplegado. Como los paneles se ubican con .place() (que no
        fuerza a su contenedor a agrandarse), el panel terminaba
        dibujándose más ancho que frame1 y la parte que sobraba quedaba
        recortada/tapada por lo que hay al lado. Acá se agranda frame1
        al ancho real necesario ANTES de animar la apertura; close_panel
        lo vuelve a achicar (solo si no hay otro open_panel encadenado
        justo después — ver animate_panel_close).
        """
        if not self.require_project("acceder a los paneles"):
            return
        token = self._panel_anim_token
        self.active_panel = index
        self.is_animating = True
        icon_width = max(self.icon_frame.winfo_width(), 40)
        self.frame1.config(width=icon_width + self.panel_width)
        self.animate_panel_open(index, 0, token)
        if index == 1:
            self.show_panel2_frames()
        elif index == 2:
            self.show_diseno_frames()
        elif index == 3:
            self.show_modelo_frames()
        self.switch_buttons_to_horizontal()
        self.highlight_button(index)

    def animate_panel_open(self, index, current_width, token=None):
        """Animación de apertura: el ANCHO del panel crece de a 10px
        por frame hasta llegar a self.panel_width. Para tocar la
        velocidad, ajustar el paso (+10) o el delay (after(10, ...)).

        SINCRONIZACIÓN: si `token` ya no coincide con
        self._panel_anim_token, quiere decir que otra acción (otro
        clic) interrumpió esta animación mientras estaba en curso —
        esta corrida "vieja" se corta acá mismo en vez de seguir
        peleando por frame1/el panel con la animación nueva.

        ALTURA (bug corregido en la vuelta anterior): antes era
        relheight=1 (= 100% del alto de frame1) posicionado en
        y=button_height — eso hace que el panel mida MÁS que el espacio
        libre debajo de la barra de íconos, y el sobrante quedaba por
        debajo del borde inferior real de la ventana, invisible. Con
        height=-button_height, place() resta esa franja del alto total.
        """
        if token is not None and token != self._panel_anim_token:
            return
        button_height = self.icon_frame.winfo_height()
        if current_width <= self.panel_width:
            self.panel_outer_frames[index].config(width=current_width)
            self.panel_outer_frames[index].place(
                x=0, y=button_height, relheight=1, height=-button_height,
            )
            self.frame1.after(10, self.animate_panel_open, index, current_width + 10, token)
        else:
            self.is_animating = False

    def close_panel(self, index, on_complete=None):
        """Cierra el panel 'index'. Si se pasa on_complete, se llama
        recién cuando la animación de cierre TERMINÓ de verdad — así
        se encadena una apertura sin adivinar tiempos (ver toggle_panel)."""
        token = self._panel_anim_token
        self.is_animating = True
        self.animate_panel_close(index, self.panel_width, token, on_complete)
        self.reset_button(index)
        self.switch_buttons_to_vertical()

    def animate_panel_close(self, index, current_width, token=None, on_complete=None):
        """Igual que animate_panel_open pero decreciendo el ancho.
        Mismo chequeo de token (ver animate_panel_open) y mismo fix de
        altura (height=-button_height) — antes tenía, además, un
        rely=0.1 mezclado con y=button_height que no tenía relación con
        cómo se abría el panel; se sacó para que abrir/cerrar usen
        exactamente la misma geometría.

        Si viene on_complete (se está encadenando una apertura), NO se
        achica frame1 acá — el open_panel que sigue va a fijar el ancho
        que corresponda; achicarlo acá de paso sería trabajo perdido y,
        peor, un parpadeo visual (achica y al toque vuelve a agrandar).
        """
        if token is not None and token != self._panel_anim_token:
            return
        button_height = self.icon_frame.winfo_height()
        if current_width > 0:
            self.panel_outer_frames[index].config(width=current_width)
            self.panel_outer_frames[index].place(
                x=0, y=button_height, relheight=1, height=-button_height,
            )
            self.frame1.after(10, self.animate_panel_close, index, current_width - 10, token, on_complete)
        else:
            self.panel_outer_frames[index].place_forget()
            if on_complete is None:
                icon_width = max(self.icon_frame.winfo_width(), 40)
                self.frame1.config(width=icon_width)
                self.is_animating = False
            else:
                on_complete()

    def hide_all_frames(self):
        """Oculta todos los paneles desplegables. Actúa sobre los
        frames FÍSICOS (panel_outer_frames) — son los que están
        realmente posicionados con .place(); los de contenido
        (panel_frames) viven dentro de un Canvas y no necesitan
        esconderse por separado."""
        for frame in self.panel_outer_frames:
            frame.place_forget()
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

    def new_project(self):
        """Crea un proyecto nuevo. Pide primero las unidades de trabajo
        (ver _mostrar_dialogo_primeras_configuraciones) — ese paso ya no
        vive suelto en la pantalla de inicio, solo aparece acá."""
        self._mostrar_dialogo_primeras_configuraciones(
            on_continuar=self.project_manager.new_project
        )

    def open_project(self):
        """Abre un proyecto utilizando ProjectManager."""
        if not self._confirm_discard_changes("Abrir proyecto"):
            return
        self.project_manager.open_project()

    def open_project_from_path(self, file_path: str):
        """Abre un proyecto a partir de una ruta absoluta."""
        return self.project_manager.open_project_from_path(file_path)

    def save_project(self):
        """Guarda el proyecto actual."""
        return self.project_manager.save_project()

    def save_project_as(self):
        """Guarda el proyecto en un nuevo destino."""
        self.project_manager.save_project_as()
        
    def duplicate_project(self):
        """Duplica el proyecto actual."""
        return self.project_manager.duplicate_project()

    def export_project_3es(self):
        """Exporta el proyecto actual a .3es."""
        return self.project_manager.export_project()

    def import_project_3es(self):
        """Importa un proyecto .3es."""
        if not self._confirm_discard_changes("Importar .3es"):
            return False
        return self.project_manager.import_project()

    # Compatibilidad con llamadas antiguas        

    def export_project(self):
        return self.export_project_3es()

    def import_project(self):
        return self.import_project_3es()

    def save_snapshot(self):
        """Guarda un snapshot del proyecto actual."""
        if not self.require_project("guardar un snapshot"):
            return
        self.snapshot_service.save_snapshot()

    def exit_app(self):
        if not self._confirm_discard_changes("Salir"):
            return
        if messagebox.askokcancel("Salir", "¿Desea salir de la aplicación?"):
            self.root.destroy()

    def undo(self):
        messagebox.showinfo(
            "Pendiente",
            "Deshacer pendiente: aún no hay historial de acciones.",
        )

    def redo(self):
        messagebox.showinfo(
            "Pendiente",
            "Rehacer pendiente: aún no hay historial de acciones.",
        )

    def open_preferences(self):
        preferences = tk.Toplevel(self.root)
        preferences.title("Preferencias")
        preferences.resizable(False, False)
        preferences.configure(bg=self.palette["background"])

        ui_mode_var = tk.StringVar(value=self.settings.get("ui_mode", "simple"))
        temp_unit_var = tk.StringVar(value=self.settings.get("temp_unit", self.settings.get("units", "C")))
        distance_unit_var = tk.StringVar(value=self.settings.get("distance_unit", "m"))
        country_var = tk.StringVar(value=self.settings.get("default_country", "Argentina"))
        city_var = tk.StringVar(value=self.settings.get("default_city", "Paraná"))
        cloudiness_var = tk.StringVar(value=self.settings.get("default_cloudiness", "Despejado"))
        wind_var = tk.StringVar(value=self.settings.get("default_wind", "moderado"))

        card = tk.Frame(preferences, bg="white", padx=16, pady=14, bd=1, relief="solid")
        card.grid(row=0, column=0, padx=14, pady=14)

        tk.Label(card, text="Unidades", bg="white", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(card, textvariable=temp_unit_var, values=["C", "F", "K"], state="readonly", width=10).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Combobox(
            card,
            textvariable=distance_unit_var,
            values=["cm", "m", "km", "in", "ft", "yd", "mi"],
            state="readonly",
            width=10,
        ).grid(row=1, column=1, sticky="w")

        tk.Label(card, text="Modo UI", bg="white", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Radiobutton(card, text="Simple", variable=ui_mode_var, value="simple", bg="white").grid(row=3, column=0, sticky="w")
        tk.Radiobutton(card, text="Avanzado", variable=ui_mode_var, value="advanced", bg="white").grid(row=3, column=1, sticky="w")

        tk.Label(card, text="País por defecto", bg="white", font=("Arial", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(10, 0))
        if self.locations_data:
            country_combo = ttk.Combobox(card, textvariable=country_var, values=self.locations_data["countries"], width=22)
            country_combo.grid(row=5, column=0, columnspan=2, sticky="w")
        else:
            tk.Entry(card, textvariable=country_var, width=24).grid(row=5, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Ciudad por defecto", bg="white", font=("Arial", 9, "bold")).grid(row=6, column=0, sticky="w", pady=(10, 0))
        if self.locations_data:
            city_combo = ttk.Combobox(card, textvariable=city_var, width=22)
            city_combo.grid(row=7, column=0, columnspan=2, sticky="w")
            if country_var.get() in self.locations_data["cities"]:
                city_combo["values"] = self.locations_data["cities"][country_var.get()]

            def update_city_options(*_args):
                cities = self.locations_data["cities"].get(country_var.get(), [])
                city_combo["values"] = cities
                if cities and city_var.get() not in cities:
                    city_var.set(cities[0])

            country_combo.bind("<<ComboboxSelected>>", update_city_options)
        else:
            tk.Entry(card, textvariable=city_var, width=24).grid(row=7, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Nubosidad", bg="white", font=("Arial", 9, "bold")).grid(row=8, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(card, textvariable=cloudiness_var, values=["Despejado", "Parcial", "Nublado"], width=22).grid(
            row=9, column=0, columnspan=2, sticky="w"
        )

        tk.Label(card, text="Viento", bg="white", font=("Arial", 9, "bold")).grid(row=10, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(card, textvariable=wind_var, values=["nulo", "moderado", "fuerte"], width=22).grid(
            row=11, column=0, columnspan=2, sticky="w"
        )

        def save_preferences():
            self.settings.update(
                {
                    "ui_mode": ui_mode_var.get(),
                    "units": temp_unit_var.get(),
                    "temp_unit": temp_unit_var.get(),
                    "distance_unit": distance_unit_var.get(),
                    "default_country": country_var.get(),
                    "default_city": city_var.get(),
                    "default_cloudiness": cloudiness_var.get(),
                    "default_wind": wind_var.get(),
                }
            )
            self.settings_manager.write(self.settings)
            self.apply_settings(self.settings)
            preferences.destroy()

        actions = tk.Frame(card, bg="white")
        actions.grid(row=12, column=0, columnspan=2, pady=(12, 0), sticky="e")
        tk.Button(actions, text="Guardar", command=save_preferences).grid(row=0, column=0, padx=(0, 8))
        tk.Button(actions, text="Cancelar", command=preferences.destroy).grid(row=0, column=1)

    def _confirm_discard_changes(self, action_label):
        if not self.is_dirty:
            return True
        response = messagebox.askyesnocancel(
            "Cambios sin guardar",
            f"{action_label}: hay cambios sin guardar. ¿Desea guardarlos?",
        )
        if response is None:
            return False
        if response:
            self.save_project()
            return not self.is_dirty
        return True

    def _reset_scene(self):
        self.vars["arboles"] = []
        self.vars["estructuras"] = []

    def _reset_vars_to_defaults(self):
        defaults = self._build_vars()
        self._apply_vars_data(self.vars, defaults)
        self._apply_vars_data(self.vars_modelo, defaults)
        self.simple_cloudiness.set(self.settings.get("default_cloudiness", "Despejado"))
        self.simple_country.set(self.settings.get("default_country", self.simple_country.get()))
        self.simple_city.set(self.settings.get("default_city", self.simple_city.get()))
        self.modo_modelo.set(self.settings.get("ui_mode", "simple"))
        self.modo_edicion.set(self.settings.get("ui_mode_edit", "simple"))
        self.panel2_advanced_mode.set(False)
        self.matriz_size.set(480)        
        self.simple_temp_air_c.set(25.0)
        if hasattr(self, "city_combo") and self.locations_data:
            self._update_city_options()
        self._toggle_modelo_mode()
        self._toggle_edicion_mode()
        self._toggle_panel2_advanced()
        self._clear_frame(self.frame2)
        self._clear_frame(self.frame7)
        self._clear_frame(self.frame11)
        self.last_T = None
        self.last_shadow = None
        self.last_meta = None
        self.current_location = None
        
    def _clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def _apply_vars_data(self, vars_dict, data):
        for key, value in data.items():
            if key in ("arboles", "estructuras"):
                continue
            if key in vars_dict and hasattr(vars_dict[key], "set"):
                if hasattr(value, "get"):
                    vars_dict[key].set(value.get())
                else:
                    vars_dict[key].set(value)

    def abrir_excel_edicion(self):
        if not self.require_project("abrir un Excel de edición"):
            return
        filepath = design.abrir_archivo(self.vars, self)
        if filepath:
            self.last_edit_excel_path = self._copy_excel_to_project(filepath, "Planos")
            self.mark_dirty()

    def cargar_excel_modelo(self):
        if not self.require_project("abrir un Excel de modelo"):
            return
        filepath = modelo.cargar_excel(self.vars_modelo)
        if filepath:
            self.last_model_excel_path = filepath
            self.mark_dirty()

    def guardar_excel_modelo(self):
        if not self.require_project("guardar Excel de modelo"):
            return
        if not self.last_model_excel_path or not os.path.exists(self.last_model_excel_path):
            messagebox.showwarning("Modelo", "Primero cargue un Excel de modelo.")
            return
        self.last_model_excel_path = self._copy_excel_to_project(self.last_model_excel_path, "modelos")
        messagebox.showinfo("Modelo", "Excel de modelo guardado en la carpeta del proyecto.")
        self.mark_dirty()

    def run_model_for_active_panel(self, force=False):
        if not self.require_project("ejecutar el modelo"):
            return
        if self.active_panel is None:
            messagebox.showinfo(
                "Pendiente",
                "Seleccione un panel antes de ejecutar el modelo.",
            )
            return

        if self.active_panel in (3, 4):
            self.generar_grafico_modelo()
            return

        if self.active_panel == 2:
            self.actualizar_grafico_diseno(self.frame7)
            return

        if self.active_panel == 1:
            self.render_grafico_en_frame(self.frame2, self.imagen)
            return

        messagebox.showinfo(
            "Pendiente",
            "No hay gráfico disponible para el panel activo.",
        )

    def mostrar_analisis_comparativo(self):
        """NUEVO. Compara todos los elementos analizados del proyecto:
        % de sombra y ΔTmrt lado a lado, más estadística descriptiva.
        No depende de tener una imagen cargada — usa self.snapshots."""
        if not self.require_project("comparar elementos del proyecto"):
            return
        if not self.snapshots:
            messagebox.showinfo(
                "Análisis comparativo",
                "Todavía no hay elementos guardados en este proyecto.\n"
                "Usá 'Confirmar selección y calcular' + 'Guardar Dataset' "
                "sobre al menos un elemento primero.",
            )
            return

        resumen = analysis_service.resumen_estadistico(self.snapshots)
        project = self.project_manager.current_project
        analisis_dir = os.path.join(project.root_path, "resultados", "analisis")
        os.makedirs(analisis_dir, exist_ok=True)
        chart_path = safe_path(analisis_dir, "comparativo_elementos.png")
        resultado = analysis_service.grafico_comparativo(self.snapshots, str(chart_path))
        if resultado is None:
            messagebox.showinfo(
                "Análisis comparativo",
                "Ningún elemento guardado tiene % de sombra calculado todavía.",
            )
            return
        self.last_comparative_chart_path = str(chart_path)

        ventana = tk.Toplevel(self.root)
        ventana.title("Análisis comparativo del proyecto")
        ventana.geometry("720x950")

        s = resumen["porcentaje_sombra"]
        d = resumen["delta_tmrt"]
        lineas = [f"Elementos analizados: {resumen['n_elementos']}"]
        if s["n"]:
            lineas.append(
                f"% de sombra — media {s['media']:.1f}% · mín {s['min']:.1f}% · "
                f"máx {s['max']:.1f}% · σ {s['desvio']:.1f}%"
            )
        if d["n"]:
            lineas.append(
                f"ΔTmrt — media {d['media']:.2f}°C · mín {d['min']:.2f}°C · "
                f"máx {d['max']:.2f}°C · σ {d['desvio']:.2f}°C"
            )
        tk.Label(ventana, text="\n".join(lineas), justify="left", anchor="w",
                 font=("Arial", 10)).pack(fill="x", padx=12, pady=10)

        img = Image.open(resultado)
        img.thumbnail((680, 400))
        photo = ImageTk.PhotoImage(img)
        lbl = tk.Label(ventana, image=photo)
        lbl.image = photo
        lbl.pack(padx=10, pady=5)

        # NUEVO: dispersión real % sombra vs. ΔTmrt con línea de
        # tendencia — a diferencia de la curva de sensibilidad (teórica,
        # según el modelo), esto usa los datos reales ya calculados de
        # cada elemento del proyecto.
        scatter_path = safe_path(analisis_dir, "dispersion_sombra_tmrt.png")
        scatter_result, pendiente, r2 = analysis_service.dispersión_sombra_tmrt(
            self.snapshots, str(scatter_path),
        )
        if scatter_result:
            self.last_scatter_chart_path = str(scatter_result)
            img2 = Image.open(scatter_result)
            img2.thumbnail((680, 400))
            photo2 = ImageTk.PhotoImage(img2)
            lbl2 = tk.Label(ventana, image=photo2)
            lbl2.image = photo2
            lbl2.pack(padx=10, pady=5)
        else:
            tk.Label(
                ventana,
                text="(Se necesitan al menos 2 elementos con % de sombra y ΔTmrt "
                     "para la dispersión real)",
                fg="#888888",
            ).pack(pady=5)

        tk.Button(
            ventana, text="Exportar tabla a Excel…",
            command=lambda: self._exportar_tabla_elementos_excel(analisis_dir),
        ).pack(pady=(4, 12))

    def _exportar_tabla_elementos_excel(self, analisis_dir: str):
        """NUEVO. Exporta self.snapshots a Excel en resultados/analisis/."""
        if not self.snapshots:
            messagebox.showinfo("Exportar tabla", "No hay elementos para exportar.")
            return
        chart_path = safe_path(analisis_dir, "elementos_proyecto.xlsx")
        try:
            resultado = analysis_service.exportar_tabla_excel(self.snapshots, str(chart_path))
        except Exception as exc:
            messagebox.showerror("Exportar tabla", f"No se pudo exportar: {exc}")
            return
        messagebox.showinfo("Exportar tabla", f"Tabla exportada a:\n{resultado}")

    def mostrar_curva_sensibilidad(self):
        """NUEVO. Grafica cómo responde el Tmrt en sombra al % de sombra
        (0-100%) según el propio modelo, con la ubicación/fecha/hora/
        temperatura actuales del Panel 1. Herramienta pura de
        exploración del modelo — no requiere ninguna imagen."""
        if not self.require_project("generar curva de sensibilidad"):
            return
        temp_ambient, hora, fecha, lat, lon = self._leer_parametros_tmrt()
        calculador = Temperatura(lat, lon)

        project = self.project_manager.current_project
        analisis_dir = os.path.join(project.root_path, "resultados", "analisis")
        os.makedirs(analisis_dir, exist_ok=True)
        chart_path = safe_path(analisis_dir, "sensibilidad_sombra.png")
        resultado_path, _, _ = analysis_service.curva_sensibilidad(
            calculador, temp_ambient, fecha, hora, str(chart_path),
        )
        self.last_sensitivity_chart_path = str(resultado_path)

        ventana = tk.Toplevel(self.root)
        ventana.title("Sensibilidad sombra–temperatura")
        ventana.geometry("650x620")
        img = Image.open(resultado_path)
        img.thumbnail((620, 560))
        photo = ImageTk.PhotoImage(img)
        lbl = tk.Label(ventana, image=photo)
        lbl.image = photo
        lbl.pack(padx=10, pady=10)

    def generar_informe_completo(self):
        """NUEVO. Informe PDF consolidado de TODO el proyecto: resumen
        estadístico, tabla de elementos, comparación entre ellos, curva
        de sensibilidad del modelo y últimos artefactos visuales.
        Se guarda directamente en resultados/analisis/ del proyecto
        (sin diálogo de guardado) para que quede siempre junto con el
        resto de los resultados del proyecto."""
        if not self.require_project("generar el informe completo"):
            return
        project = self.project_manager.current_project
        analisis_dir = os.path.join(project.root_path, "resultados", "analisis")
        os.makedirs(analisis_dir, exist_ok=True)
        nombre = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        destino = os.path.join(analisis_dir, nombre)
        try:
            ruta_final = report_service.generar_informe_proyecto(self, project, destino)
        except Exception as exc:
            messagebox.showerror("Informe completo", f"No se pudo generar el informe: {exc}")
            return
        messagebox.showinfo("Informe completo", f"Informe guardado en:\n{ruta_final}")

    def quick_stats(self):
        if self.last_T is None:
            messagebox.showinfo(
                "Pendiente",
                "Ejecutá el modelo primero (F5) para ver estadísticas.",
            )
            return
        unit = self.get_temperature_unit_symbol()
        data = np.array(self.last_T, dtype=float)
        data = self.convert_temperature_for_display(data)
        min_val = float(np.nanmin(data))
        max_val = float(np.nanmax(data))
        mean_val = float(np.nanmean(data))
        lines = [
            f"T mínimo: {min_val:.2f} {unit}",
            f"T máximo: {max_val:.2f} {unit}",
            f"T promedio: {mean_val:.2f} {unit}",
        ]
        if self.last_shadow is not None:
            shadow = np.array(self.last_shadow, dtype=float)
            sombra_pct = (1 - shadow).mean() * 100
            lines.append(f"% sombra promedio: {sombra_pct:.2f}%")
        messagebox.showinfo("Estadísticas rápidas", "\n".join(lines))

    def show_about(self):
        app_name = self.root.title()
        version = getattr(self, "version", "N/D")
        messagebox.showinfo(
            "Acerca de",
            f"{app_name}\nVersión: {version}\nAplicación para análisis de sombra urbana.",
        )
    def _open_link(self, label, url):
        """Muestra un mensaje informativo para enlaces externos."""
        messagebox.showinfo("Enlace", f"Abrir {label}: {url}")
    def setup_ribbon(self):
        """NUEVO: barra de herramientas con íconos agrupados por
        categoría (Archivo / Escena / Modelo / Análisis), con etiqueta
        debajo de cada ícono — mismo lenguaje visual que las barras de
        herramientas de software técnico (CAD, edición de imagen, etc.)
        en vez de depender solo del menú de texto.

        Es ADITIVA: no reemplaza el menú ni el selector de paneles
        lateral (self.icon_frame/self.buttons) — llama exactamente a
        los mismos métodos, así que cualquiera de los dos caminos
        funciona igual y no hay lógica duplicada que pueda desincronizarse.
        """
        ribbon = tk.Frame(self.frame0, bg=self.palette["panel"])
        ribbon.pack(fill="x", padx=4, pady=(2, 0))

        def _grupo(nombre):
            contenedor = tk.Frame(ribbon, bg=self.palette["panel"])
            contenedor.pack(side="left", padx=(6, 2), pady=2)
            botones = tk.Frame(contenedor, bg=self.palette["panel"])
            botones.pack(side="top")
            tk.Label(
                contenedor, text=nombre, bg=self.palette["panel"],
                fg="#8a8f9c", font=("Arial", 7),
            ).pack(side="top", pady=(1, 0))
            return botones

        def _boton(padre, icono, texto, comando):
            marco = tk.Frame(padre, bg=self.palette["panel"])
            marco.pack(side="left", padx=3)
            btn = tk.Button(
                marco, image=icono, command=comando, relief=tk.FLAT,
                bg=self.palette["panel"], activebackground=self.palette["accent"],
                cursor="hand2",
            )
            btn.image = icono  # evita que el ícono se libere (bug clásico de Tkinter)
            theme.dar_hover(btn, self.palette["panel"], self.palette["accent"])
            btn.pack()
            tk.Label(
                marco, text=texto, bg=self.palette["panel"], fg="#4a4f63",
                font=("Arial", 7),
            ).pack()
            return btn

        def _separador():
            tk.Frame(ribbon, bg=self.palette["border"], width=1).pack(
                side="left", fill="y", padx=4, pady=4)

        grupo_archivo = _grupo("Archivo")
        _boton(grupo_archivo, icon_factory.obtener_icono("nuevo"), "Nuevo", self.new_project)
        _boton(grupo_archivo, icon_factory.obtener_icono("abrir"), "Abrir", self.open_project)
        _boton(grupo_archivo, icon_factory.obtener_icono("guardar"), "Guardar", self.save_project)
        _separador()

        grupo_escena = _grupo("Escena")
        _boton(grupo_escena, self.images[0], "Temp.", lambda: self.open_panel(0))
        _boton(grupo_escena, self.images[1], "Sombra", lambda: self.open_panel(1))
        _boton(grupo_escena, self.images[2], "Edición", lambda: self.open_panel(2))
        _boton(grupo_escena, self.images[3], "Modelo", lambda: self.open_panel(3))
        _separador()

        grupo_modelo = _grupo("Modelo")
        _boton(grupo_modelo, icon_factory.obtener_icono("play"), "Ejecutar", self.run_model_for_active_panel)
        _separador()

        grupo_analisis = _grupo("Análisis")
        _boton(grupo_analisis, icon_factory.obtener_icono("barras"), "Comparar", self.mostrar_analisis_comparativo)
        _boton(grupo_analisis, icon_factory.obtener_icono("curva"), "Sensib.", self.mostrar_curva_sensibilidad)
        _boton(grupo_analisis, icon_factory.obtener_icono("pdf"), "Informe", self.generar_informe_completo)

    def setup_status_bar(self):
        self.frame6.configure(bg=self.palette["accent"])
        username = getattr(self, "username", "Usuario")
        self.status_project_var = tk.StringVar(value="Proyecto: Sin proyecto")
        self.status_saved_var = tk.StringVar(value="Último guardado: N/A")

        self.project_status_label = tk.Label(
            self.frame6,
            textvariable=self.status_project_var, #text=f"Conexión: {connection_start.strftime('%Y-%m-%d %H:%M:%S')}",
            bg=self.palette["accent"],
            fg="#2c3e50",
            font=("Arial", 9, "bold"),
        )
        self.project_status_label.pack(side="left", padx=10)

        self.saved_status_label = tk.Label(
            self.frame6,
            textvariable=self.status_saved_var,            #text=f"Usuario: {username}",
            bg=self.palette["accent"],
            fg="#2c3e50",
            font=("Arial", 9),
        )
        self.saved_status_label.pack(side="left", padx=10)

        # NUEVO: cantidad de elementos analizados, siempre visible.
        # Software de análisis científico debería mostrar el tamaño de
        # muestra sin que haya que abrir el historial para contarlo.
        self.status_elements_var = tk.StringVar(value="Elementos: 0")
        self.elements_status_label = tk.Label(
            self.frame6,
            textvariable=self.status_elements_var,
            bg=self.palette["accent"],
            fg="#2c3e50",
            font=("Arial", 9),
        )
        self.elements_status_label.pack(side="left", padx=10)

        tk.Label(
            self.frame6,
            text=f"Usuario: {username}", #text="3Esfera",
            bg=self.palette["accent"],
            fg="#4a4f63",
            font=("Arial", 9),
 ).pack(side="right", padx=10)
        tk.Label(
            self.frame6,
            text="3esfera",
            bg=self.palette["accent"],
            fg="#4a4f63",
            font=("Arial", 9),
        ).pack(side="right", padx=10)

    def update_status_saved_time(self, iso_time: str | None = None):
        project = self.project_manager.current_project
        pname = project.name if project else "Sin proyecto"
        self.status_project_var.set(f"Proyecto: {pname}")
        if not iso_time:
            self.status_saved_var.set("Último guardado: N/A")
            return
        try:
            dt = datetime.fromisoformat(iso_time)
            self.status_saved_var.set(f"Último guardado: {dt.isoformat(sep=' ', timespec='seconds')}")
        except ValueError:
            self.status_saved_var.set(f"Último guardado: {iso_time}")

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
            #sombra_frame, text="Área de Cálculo: N/A", font=("Arial", 12, "bold")
            sombra_frame,
            text="Dimensiones del Área de Cálculo: N/A",
            font=("Arial", 9, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_dimensiones_calculo.pack(pady=5)

        self.lbl_dimensiones_referencia = tk.Label(
            #sombra_frame, text="Área de Referencia: N/A", font=("Arial", 12, "bold")
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
        img_frame = self.create_card(frame)
        img_frame.pack(expand=True, fill='both', pady=5)
        self.fig1, self.ax1 = plt.subplots() 
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=img_frame)
        self.canvas1.get_tk_widget().pack(side=tk.LEFT)
    def curva_de_nivel(self, frame):
        """Configura el área de curvas de nivel."""
        nivel_frame = self.create_card(frame)
        nivel_frame.pack(expand=True, fill='both', pady=5)
        self.curva_frame = nivel_frame
        self.curva_frame.bind("<Configure>", self._on_curva_frame_resize)

        self.fig2, self.ax2 = plt.subplots()
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=nivel_frame)
        self.canvas2.get_tk_widget().pack(side=tk.RIGHT)
    def cargar_imagen(self):
        if not self.require_project("cargar una imagen"):
            return  
        self.show_panel2_frames()      
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                ("Todos los archivos", "*.*"),
            ]
        )
        if file_path:
            try:
                saved_image_path = self.save_loaded_image_to_project(file_path)
                self._reset_panel2_for_new_image()
                self.img, self.img_rgb = self.image_processor.load_image(saved_image_path)
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))
                return
            self.original_rgb = self.img_rgb
            self._ensure_panel2_image_canvas()
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self._setup_hover_shadow_percent_photo(self.ax1, self.canvas1, self.img_rgb)
            self.canvas1.draw()
            self.shape_selector.enable_calculo_button()
            self.cargar_imagen_button.config(text="Cargar nueva imagen")
            self.mark_dirty()
            
                
    def _ensure_panel2_image_canvas(self):
        canvas = getattr(self, "canvas1", None)
        if canvas is None:
            self.imagen(self.frame2)
            self.activar_mouse()
            return
        widget = canvas.get_tk_widget()
        if not widget.winfo_exists():
            self.imagen(self.frame2)
            self.activar_mouse()
    def calculate_temperature_in_shade(self):
        if not self.require_project("calcular temperatura en sombra"):
            return
        try:
            # NUEVO: se puede calcular con un % de sombra manual (campo
            # nuevo en Panel 1) sin depender de haber procesado una
            # imagen en el Panel 2. Si el campo manual está vacío, se
            # usa self.porcentaje_sombra (el calculado desde la imagen),
            # igual que antes.
            manual_text = self.entry_porcentaje_manual.get().replace('\ufeff', '').strip() if hasattr(self, "entry_porcentaje_manual") else ""
            if manual_text:
                try:
                    porcentaje_sombra = float(manual_text)
                except ValueError:
                    messagebox.showerror("Error", "El porcentaje de sombra manual debe ser un número.")
                    return
                if not (0 <= porcentaje_sombra <= 100):
                    messagebox.showerror("Error", "El porcentaje de sombra manual debe estar entre 0 y 100.")
                    return
            elif self.porcentaje_sombra is not None:
                porcentaje_sombra = self.porcentaje_sombra
            else:
                messagebox.showerror(
                    "Error",
                    "Ingrese un porcentaje de sombra manual, o seleccione el área de "
                    "sombra en una imagen (Panel 2) para calcularlo automáticamente.",
                )
                return
            # Se guarda en self.porcentaje_sombra para que el resto de la
            # app (curvas de nivel, historial) use el mismo valor sin
            # importar si vino de la imagen o se ingresó a mano.
            self.porcentaje_sombra = porcentaje_sombra

            # Obtener valores ingresados por el usuario
            temp_ambient = float(self.entry_temp.get().replace('\ufeff', '').strip())
            latitude = float(self.entry_lat.get().replace('\ufeff', '').strip())
            longitude = float(self.entry_lon.get().replace('\ufeff', '').strip())
            hora = float(self.entry_time.get().replace('\ufeff', '').strip())
            fecha_str = self.entry_date.get().replace('\ufeff', '').strip()
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            self.temp_calculator = Temperatura(latitude, longitude)
            self.solar_engine.use_pvlib = bool(self.use_pvlib_engine.get())
            _ = self.solar_engine.get_solar_position(latitude, longitude, datetime.combine(fecha, datetime.min.time()))
            result = self.temp_calculator.calculate_tmrt(
                temp_ambient,
                porcentaje_sombra,
                shadow_type="tree",
                date_value=fecha,
                time_value=hora,
            )            
            self.tmrt_result = result
            if hasattr(self, "lbl_porcentaje_sombra"):
                self.lbl_porcentaje_sombra.config(text=f"Porcentaje de sombra: {porcentaje_sombra:.2f}%")
            
            
            self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {result['Tmrt_sol']:.2f} °C")
            self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {result['Tmrt_sombra']:.2f} °C")
            self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {result['Delta_Tmrt']:.2f} °C")
            # Limpiar el frame anterior si existe (evita sobreposición de gráficos)
            for widget in self.graph_frame.winfo_children():
                widget.destroy()

            # Crear un objeto de la clase TemperatureGraph y mostrar la gráfica dentro del frame
            graph = TemperatureGraph(temp_ambient, result["Tmrt_sombra"], self.graph_frame)
            graph.plot_temperature_scale()  # Dibujar la gráfica en el frame
            if self.project_manager.current_project:
                temp_img_dir = os.path.join(self.project_manager.current_project.root_path, "resultados")
                temp_img_path = safe_path(temp_img_dir, "temp_ambiente_last.png")
                plt.gcf().savefig(temp_img_path, dpi=120, bbox_inches="tight")
                self.last_temp_graph_path = str(temp_img_path)
                
        except ValueError as e:
            messagebox.showerror("Error", f"Error al ingresar los datos: {e}")
    def confirmar_seleccion(self):
        if not self.require_project("confirmar selección"):
            return
        # Verificamos que ambas áreas hayan sido seleccionadas
        if self.shape_selector.area_seleccionada is not None and self.shape_selector.area_referencia is not None:
            # Cálculo del porcentaje de sombra
            porcentaje_sombra = self.image_processor.calcular_porcentaje_sombra(
                self.shape_selector.area_seleccionada,
                self.shape_selector.area_referencia
            )
            self.porcentaje_sombra = porcentaje_sombra
            self.lbl_porcentaje_sombra.config(text=f"Porcentaje de sombra: {porcentaje_sombra:.2f}%")
            if self.shadow_detector_enabled.get() and self.img_rgb is not None:
                detected = self.shadow_detector.detect_shadow_mask(self.img_rgb, method="adaptive")
                roi = np.zeros_like(detected, dtype=bool)
                if self.shape_selector.area_seleccionada is not None:
                    h, w = self.shape_selector.area_seleccionada.shape[:2]
                    roi[:h, :w] = True
                quality_meta = self.shadow_detector.compute_shadow_quality(detected, roi_mask=roi)
                self.shadow_quality = quality_meta.get("shadow_quality")
                
            # Habilitar los botones para curvas de nivel y exportar
            self.curve_button.config(state=tk.NORMAL)  # Habilitar el botón de curvas de nivel
            self.excel_button.config(state=tk.NORMAL)  # Habilitar el botón para exportar a Excel
            self.pdf_button.config(state=tk.NORMAL) # Habilita el botón para guardan el pdf
            if not self.current_image_path or not os.path.exists(self.current_image_path):
                print(f"[confirmar] Ruta de imagen inexistente: {self.current_image_path}")
                messagebox.showerror("Error", "La imagen del proyecto no existe. Cargá la imagen nuevamente.")
                return            
            self.dataset_saver.save_dataset(
                img_filename=self.current_image_basename,
                mask_filename=f"{self.current_image_stem}_mask.png",
                save_image=False,
            )
            self.shape_selector.disable_selection()
            self.area_calc_button.config(state=tk.DISABLED)
            self.area_ref_button.config(state=tk.DISABLED)
        else:
            print("Error: No se ha seleccionado un área válida.")
    def exportar_a_excel(self):
        if not self.require_project("exportar a Excel"):
            return
        if self.shape_selector.area_seleccionada is not None:
            file_path = export_to_excel(self.shape_selector.area_seleccionada)
            if file_path:
                self.last_matrix_path = file_path
    def _leer_parametros_tmrt(self):
        """Lee temp. ambiente / hora / fecha / lat / lon desde el Panel 1,
        con valores por defecto razonables si están vacíos.

        NUEVO — antes calcular Tmrt exigía haber completado estos campos
        a mano Y haber pasado por el flujo de imagen. Con esto, tanto
        "Calcular temperatura en sombra" como "Generar curva de nivel"
        pueden calcular usando lo que haya disponible (ubicación del
        proyecto, hora actual, 25°C por defecto) sin bloquear al usuario.
        """
        def _f(entry, default):
            if entry is None:
                return default
            try:
                return float(entry.get().replace('\ufeff', '').strip())
            except (ValueError, AttributeError):
                return default

        ahora = datetime.now()
        loc = self.current_location or {}
        temp_ambient = _f(self.entry_temp, 25.0)
        hora = _f(self.entry_time, ahora.hour + ahora.minute / 60)
        lat = _f(self.entry_lat, float(loc.get("lat", 0.0)))
        lon = _f(self.entry_lon, float(loc.get("lon", 0.0)))
        fecha_str = self.entry_date.get().replace('\ufeff', '').strip() if self.entry_date else ""
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            fecha = ahora.date()
        return temp_ambient, hora, fecha, lat, lon

    def mostrar_curvas_nivel(self):
        if not self.require_project("generar curvas de nivel"):
            return
        if self.shape_selector.area_seleccionada is not None:

            # Rotar la matriz 90 grados en sentido horario
            area_volteada = np.flipud(self.shape_selector.area_seleccionada)

            # CAMBIO PRINCIPAL: antes se graficaba directamente el nivel
            # de gris de la foto (0-255), que no tiene unidad física ni
            # es comparable entre dos fotos con distinta exposición o
            # condiciones de luz. Ahora se calcula el % de sombra LOCAL
            # de cada píxel (misma normalización que calcular_porcentaje_
            # sombra, pero sin promediar) y se lo alimenta al modelo de
            # Tmrt ya usado en "Calcular temperatura en sombra" — el
            # contorno pasa a mostrar TEMPERATURA EN SOMBRA calculada en
            # °C, punto por punto, según ubicación/fecha/hora y el propio
            # % de sombra de cada zona de la imagen.
            temp_ambient, hora, fecha, lat, lon = self._leer_parametros_tmrt()
            mapa_sombra = self.image_processor.calcular_mapa_sombra(
                self.shape_selector.area_seleccionada,
                self.shape_selector.area_referencia,
            )
            mapa_sombra_volteado = np.flipud(mapa_sombra)
            calculador = Temperatura(lat, lon)
            resultado_mapa = calculador.calculate_tmrt_map(
                temp_ambient, mapa_sombra_volteado,
                shadow_type="tree", date_value=fecha, time_value=hora,
            )
            mapa_temperatura = resultado_mapa["Tmrt_map"]

            # Crear las curvas de nivel en una figura local
            #
            # CAMBIOS: antes esta figura no tenía colorbar, ni ejes con
            # unidades, ni título con metadatos — se veían "formas" pero
            # no había forma de leer un valor concreto ni de saber cuándo
            # ni de qué imagen salió. Y usaba "jet" (mala práctica para
            # datos científicos: no es perceptualmente uniforme). Ver
            # plot_style.py para el detalle de cada elección.
            from plot_style import (
                CMAP_CURVAS_NIVEL, CMAP_HISTOGRAMA,
                agregar_colorbar_temperatura, anotar_estadisticas,
                anotar_metadatos,
            )

            fig, ax = plt.subplots()
            contorno = ax.contour(
                mapa_temperatura, levels=20, cmap=CMAP_CURVAS_NIVEL,
                linewidths=1.2, alpha=0.9,
            )
            ax.set_xlabel("Posición X (px)")
            ax.set_ylabel("Posición Y (px)")
            ax.set_title(
                f"Temperatura en sombra calculada — {self.current_image_stem}\n"
                f"(rad. {resultado_mapa['Radiacion_Wm2']:.0f} W/m², "
                f"alt. solar {resultado_mapa['Solar_altitude']:.1f}°)",
                fontsize=10,
            )
            agregar_colorbar_temperatura(fig, ax, contorno, unidad="°C")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            fig.tight_layout(pad=0.6)
            anotar_metadatos(fig, f"Generado: {timestamp}  ·  Fuente: {self.current_image_stem}")

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.1)
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

            project_root = self.project_manager.current_project.root_path
            # CAMBIO: "histograma" (singular) -> "histogramas" (plural),
            # alineado con services/snapshot_service.py, que ya guardaba
            # ahí — antes esta carpeta creada acá nunca era la que se
            # usaba realmente.
            hist_dir = os.path.join(project_root, "resultados", "histogramas")
            curve_dir = os.path.join(project_root, "resultados", "curvas_nivel")
            excel_dir = os.path.join(project_root, "resultados", "excels")
            os.makedirs(hist_dir, exist_ok=True)
            os.makedirs(curve_dir, exist_ok=True)
            os.makedirs(excel_dir, exist_ok=True)

            curve_path = safe_path(curve_dir, f"{self.current_image_stem}_curva.png")
            self.curva_img_pil_original.save(curve_path)
            self.last_curve_path = str(curve_path)

            hist_path = safe_path(hist_dir, f"{self.current_image_stem}_histo.png")
            hist_fig, hist_ax = plt.subplots()
            values = self.shape_selector.area_seleccionada.flatten()
            counts, bins, patches = hist_ax.hist(values, bins=50, alpha=0.95)
            cmap = plt.get_cmap(CMAP_HISTOGRAMA)
            max_count = max(counts) if len(counts) else 1
            for c, patch in zip(counts, patches):
                patch.set_facecolor(cmap(c / max_count if max_count else 0))
            hist_ax.set_xlabel("Nivel de gris")
            hist_ax.set_ylabel("Frecuencia (cantidad de píxeles)")
            hist_ax.set_title(f"Histograma — {self.current_image_stem}")
            # CAMBIO: antes el histograma no tenía ningún resumen
            # numérico (media, mediana, desvío, N) — solo la forma de
            # la distribución, sin poder leer valores concretos.
            anotar_estadisticas(hist_ax, values)
            hist_fig.tight_layout()
            anotar_metadatos(hist_fig, f"Generado: {timestamp}")
            hist_fig.savefig(hist_path, dpi=150)
            plt.close(hist_fig)
            
            self.last_histogram_path = str(hist_path)

            excel_path = safe_path(excel_dir, f"{self.current_image_stem}.xlsx")
            pd.DataFrame(self.shape_selector.area_seleccionada).to_excel(excel_path, index=False)
            self.last_matrix_path = str(excel_path)
            self.mark_dirty()            
            
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
        if not self.require_project("exportar a PDF"):
            return        
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
        if not self.require_project("guardar el dataset"):
            return  
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            print(f"[dataset] Ruta de imagen inválida: {self.current_image_path}")
            messagebox.showerror("Error", "La imagen actual no existe en disco. Recargá la imagen antes de guardar.")
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
        if self._shadow_hover_annotation is not None and self._shadow_hover_annotation.axes != ax:
            self._shadow_hover_annotation.set_visible(False)
            try:
                self._shadow_hover_annotation.remove()
            except (NotImplementedError, ValueError):
                pass
            self._shadow_hover_annotation = None        
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