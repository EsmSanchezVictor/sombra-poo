from datetime import datetime, timedelta
import zoneinfo
import os
import shutil
import tkinter as tk
from tkinter import ttk, font as tkfont

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
from core import scenario as scenario_tools
from core import thermal_comfort
from core.climate_profile import viento_categoria_a_ms, factor_ghi_nubosidad, descomponer_radiacion
from core.species import ESPECIES as CATALOGO_ESPECIES, nombres_especies
from core.validation import k_factor_desde_mediciones, leer_csv_mediciones, metricas
from core.uncertainty import estimate_tmrt_uncertainty
from core.memory_utils import collect_and_log
from image_processor import (
    ImageProcessor, DEFAULT_MATRIX_SIZE, MATRIX_SIZE_OPTIONS, normalize_matrix_size,
)
#from mouse_pixel_value import MouseHoverPixelValueWithTooltip
from save_pdf import PDFReportGenerator
from services.location_service import LocationService
from services.snapshot_service import SnapshotService
from services.analysis_record_store import AnalysisRecordStore
from services.shadow_detector import ShadowDetector
from shape_selection import ShapeSelector
from shadow_temp import Temperatura
from temp_graph import TemperatureGraph
from services.solar_engine import SolarEngine
from services.meteorology_service import MeteorologyService, SOURCE_LABELS
from services import analysis_service
from services import report_service
from ui import icon_factory
from ui import panels as ui_panels
from ui import theme
from ui.layout import (
    PANEL_CONTENT_RATIO,
    PANEL_HORIZONTAL_SCALE,
    PANEL_ELEMENT_SCALE,
    PANEL_MIN_FONT_SIZE,
    calcular_geometria_contenido_panel,
    calcular_ancho_sidebar_abierto,
)
from ui.dialogs import HerramientasDialogs
from ui.menu_bar import MenuBar
from ui.diurnal_animation import DiurnalAnimationPlayer, Diurnal3DAnimationPlayer
from ui.solar_indicator import add_solar_indicator_2d
from ui.modal_style import prepare_dialog
from utils import export_to_excel
import diseno as design
import modelo_con_excel as modelo


class SombraApp:
    def __init__(self, root, db_manager=None, username="Usuario", session_id=None,
                 connection_start=None, on_session_exit=None):

        self.root = root
        self.db_manager = db_manager
        self.username = username or "Usuario"
        self.session_id = session_id
        self.connection_start = connection_start or datetime.now()
        self.on_session_exit = on_session_exit
        self._session_exit_notified = False
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
        self.k_factor = float(self.settings.get("k_factor", 0.04))
        self.k_factor_info = self.settings.get("k_factor_info")
        # Refactor (README §6): los diálogos viven en ui/dialogs.py;
        # SombraApp conserva los nombres públicos como bound methods.
        self._herramientas = HerramientasDialogs(self)
        for _n in ("_dialogo_calibrar_k_factor", "_dialogo_confort",
                   "_dialogo_escenario_ab", "_dialogo_validar_csv",
                   "_dialogo_auditoria_cientifica",
                   "_dialogo_especies", "_dialogo_editar_especies",
                   "_dialogo_ranking_arboles"):
            setattr(self, _n, getattr(self._herramientas, _n))
        self.current_project_path = self.settings.get("last_project_path")
        self.current_location = None        
        self.is_dirty = False
        self._suspend_autosave_tracking = False
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
        self.last_scientific_audit = None

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
            bd=0,
            relief="flat",
            highlightthickness=0,
        )
        self.frame3 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            bd=0,
            relief="flat",
            highlightthickness=0,
        )
        self.frame4 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            bd=0,
            relief="flat",
            highlightthickness=0,
        )
        self.frame5 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            bd=0,
            relief="flat",
            highlightthickness=0,
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
        # Área propia del carrusel del Panel 2 (fila fija debajo de las
        # 4 secciones, sin peso de grilla: no afecta sus tamaños).
        # Altura contenida a propósito: la fila 1 (foto/curva) tiene
        # weight=1 y es la dominante al redimensionar la ventana.
        self.frame15 = tk.Frame(
            root,
            bg=self.palette["panel"],
            width=100,
            height=100,
            highlightbackground=self.palette["border"],
            highlightthickness=1,
        )

        # Ubicar frames
        # v26: frame1 abarca también la fila 4. Esa fila contiene el
        # carrusel cuando se muestra el Panel 2; con rowspan=3 el lateral
        # terminaba antes del carrusel y dejaba una franja vacía debajo.
        self.frame0.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.frame1.grid(row=1, column=0, rowspan=4, sticky="nsew")
        self.frame2.grid(row=1, column=1, sticky="nsew")
        self.frame3.grid(row=1, column=2, sticky="nsew")
        self.frame4.grid(row=2, column=1, sticky="nsew")
        self.frame5.grid(row=2, column=2, sticky="nsew")
        self.frame6.grid(row=5, column=1, columnspan=2, sticky="nsew")
        # v30: Edición y Modelo son superficies de visualización completas.
        # frame7/frame11 abarcan exactamente el bloque histórico 2x2 ocupado
        # por frame2+frame3+frame4+frame5 (filas 1-2, columnas 1-2).
        # Los frames auxiliares 8-10 / 12-14 se conservan por compatibilidad
        # pero permanecen ocultos en esos modos.
        self.frame7.grid(row=1, column=1, rowspan=2, columnspan=2, sticky="nsew")
        self.frame8.grid(row=1, column=2, sticky="nsew")
        self.frame9.grid(row=2, column=1, sticky="nsew")
        self.frame10.grid(row=2, column=2, sticky="nsew")
        self.frame11.grid(row=1, column=1, rowspan=2, columnspan=2, sticky="nsew")
        self.frame12.grid(row=1, column=2, sticky="nsew")
        self.frame13.grid(row=2, column=1, sticky="nsew")
        self.frame14.grid(row=2, column=2, sticky="nsew")
        self.frame15.grid(row=4, column=1, columnspan=2, sticky="ew")
        self.frame7.grid_remove()
        self.frame8.grid_remove()
        self.frame9.grid_remove()
        self.frame10.grid_remove()
        self.frame11.grid_remove()
        self.frame12.grid_remove()
        self.frame13.grid_remove()
        self.frame14.grid_remove()
        self.frame15.grid_remove()

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
        root.grid_rowconfigure(4, weight=0)  # carrusel: alto fijo, no crece
        root.grid_rowconfigure(5, weight=0)  # separador inferior
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
        self.analysis_store = None
        self.current_analysis_id = None
        self.shadow_detector = ShadowDetector()
        self.shadow_detector_enabled = tk.BooleanVar(value=False)
        self.use_pvlib_engine = tk.BooleanVar(value=bool(self.settings.get("clear_sky_use_pvlib", False)))
        self.solar_engine = SolarEngine(use_pvlib=False)
        # v14: fuente radiativa/meteorológica explícita. El default conserva
        # el comportamiento histórico (cielo despejado modelado).
        self.meteorology_service = MeteorologyService()
        self.radiation_source_mode = tk.StringVar(value=self.settings.get("radiation_source_mode", "clear_sky"))
        self.manual_ghi = tk.StringVar(value="800")
        self.manual_dni = tk.StringVar(value="")
        self.manual_dhi = tk.StringVar(value="")
        self.meteorology_series_path = None
        self.last_meteorology_data = None
        self.last_validation_summary = None
        self.menu_bar = MenuBar(self)
        self.porcentaje_sombra = None  # compatibilidad: ahora representa cobertura si proviene de foto
        self.cobertura_sombra = None
        self.atenuacion_sombra = None
        self.shadow_photo_analysis = None
        self.last_shadow_classification_path = None
        self.tmrt_result = None
        self.snapshots = []  # NUEVO: historial de elementos analizados (imagen+sombra+curva+Tmrt) del proyecto actual
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.original_rgb = None
        self._shadow_hover_cid = None
        self._shadow_hover_canvas = None
        self._shadow_hover_annotation = None
        # Interacción del mapa Tmrt (curvas de nivel): hover y punto fijado.
        self._curve_hover_cid = None
        self._curve_click_cid = None
        self._curve_hover_annotation = None
        self._curve_hover_canvas = None
        self._curve_pinned_pixel = None
        self.tmrt_hover_data = None
        self.mouse_hover_pixel_value = None
        self.curva_frame = None
        self.curva_label = None
        self.curva_photo = None
        self.curva_img_pil_original = None
        self._temp_graph_figure = None
        self._temp_graph_canvas = None
        #self.frame1 = frame1

        # --- Ancho del panel desplegable -----------------------------
        # v22: el ancho se calcula como una fracción del viewport con
        # límites operativos. La columna 0 se reserva explícitamente al
        # abrir el panel (ver _reservar_ancho_sidebar); esto evita que
        # grid comprima frame1 mientras el panel colocado con place()
        # conserva un ancho mayor y termina recortado contra frame2/4.
        self.panel_width = calcular_ancho_sidebar_abierto(self.frame1.winfo_screenwidth())

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

        # v22: la columna 0 de la grilla principal tiene un ancho reservado
        # explícito. Sin esto Tk podía comprimir frame1 por debajo del ancho
        # del panel colocado con ``place`` (p.ej. frame1=218 px mientras el
        # panel medía 260 px), recortando su borde derecho junto a frame2/4.
        self.sidebar_closed_width = max(40, max(img.width() for img in self.images) + 8)
        self.frame1.grid_propagate(False)
        self._reservar_ancho_sidebar(self.sidebar_closed_width)

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
        self._install_autosave_variable_traces()
        
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
        # BUG CORREGIDO ("los íconos no manejan bien el cambio de
        # paneles"): las animaciones se encolaban con
        # widget.after(10, callable, ...). Tkinter registra ese
        # callable bajo un nombre generado con id() que puede reciclarse
        # (y el comando se auto-borra al dispararse) — con cadenas de
        # ~23 pasos, dos timers terminaban con el mismo nombre y la
        # animación se cortaba en un paso al azar (panel congelado a
        # medio abrir, o cambio de panel que nunca llegaba). Ahora se
        # registra UN único comando Tcl persistente (_anim_cmd) y cada
        # paso se encola con tk.call("after", ...) sobre ese nombre
        # estable — sin re-registros, sin colisiones.
        self._anim_cmd = self.root.register(self._panel_anim_step)
        # Si un cierre va encadenado a una apertura (open_panel(index)
        # apenas termina de cerrar), se guarda el token acá — ver
        # animate_panel_close/_panel_anim_step.
        self._open_after_close = {}
        # Callback de cierre encadenado (on_complete de close_panel).
        # _panel_anim_step recibe los args vía Tcl y no puede recibir
        # callables Python — por eso el callback se guarda acá y el
        # paso final del cierre lo invoca (BUG CORREGIDO: antes el paso
        # final reabría el MISMO panel en vez de llamar a on_complete).
        self._close_callbacks = {}

        # Inicializar componentes
        self.menu_bar.setup()
        self.setup_ribbon()
        self.setup_status_bar()
        self.resultados(self.frame4)
        self.carrusel(self.frame15)
        self.temp_sombra(self.frame5)
        self.imagen(self.frame2)
        self.curva_de_nivel(self.frame3)
        self.activar_mouse()
        self.setup_startup_screen()
        self.show_startup_screen()
        # El cierre por la X usa la misma ruta que Archivo > Salir, para
        # registrar correctamente el fin de sesión y del proyecto activo.
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
    
    
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
        prepare_dialog(dialogo, self.root, modal=True, resizable=False)
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

    def on_project_loaded(self, project_action="opened"):
        self.hide_startup_screen()
        self.set_project_ui_enabled(True)
        self._get_analysis_store()
        self.update_status_saved_time()
        self._register_project_session(project_action)
        if self.current_location:
            self._update_location_labels()

    def _register_project_session(self, action="opened"):
        """Asocia el proyecto actual a la sesión autenticada."""
        if self.db_manager is None or not self.session_id:
            return
        project = self.project_manager.current_project
        if project is None:
            return
        try:
            self.db_manager.start_project_work(
                self.session_id,
                project.name,
                project_root=os.path.abspath(project.root_path),
                project_state_path=os.path.abspath(project.state_path),
                action=action,
            )
        except Exception as exc:
            # La trazabilidad no debe impedir abrir un proyecto.
            print(f"[sesion] No se pudo registrar proyecto: {exc}")

    def _touch_session(self):
        if self.db_manager is None or not self.session_id:
            return
        try:
            self.db_manager.touch_session(self.session_id)
        except Exception as exc:
            print(f"[sesion] No se pudo actualizar actividad: {exc}")

    def _get_analysis_store(self):
        """Devuelve la base de análisis del proyecto actual.

        La instancia se recrea automáticamente al cambiar de proyecto. La
        SQLite vive dentro de la carpeta del proyecto, por lo que se incluye
        también al exportar/duplicar el proyecto.
        """
        project = self.project_manager.current_project
        if project is None:
            self.analysis_store = None
            return None
        root = os.path.abspath(project.root_path)
        store = getattr(self, "analysis_store", None)
        if store is None or os.path.abspath(store.project_root) != root:
            self.analysis_store = AnalysisRecordStore(root)
        return self.analysis_store

    def _recargar_analisis_desde_base(self, *, migrate_legacy=True):
        """Sincroniza el cache ``self.snapshots`` desde SQLite.

        ``snapshots`` se mantiene porque servicios de reportes/análisis ya lo
        consumen, pero desde v17 es un cache de los registros persistentes y
        no el mecanismo primario de almacenamiento del carrusel.
        """
        store = self._get_analysis_store()
        if store is None:
            return
        if migrate_legacy:
            store.migrate_legacy_snapshots(getattr(self, "snapshots", []))
        self.snapshots = store.list_entries(complete_only=True)

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
        tz = location.get("tz") or "America/Argentina/Buenos_Aires"
        if "timezone" in self.vars and hasattr(self.vars["timezone"], "set"):
            self.vars["timezone"].set(tz)
        if "timezone" in self.vars_modelo and hasattr(self.vars_modelo["timezone"], "set"):
            self.vars_modelo["timezone"].set(tz)
        try:
            self.solar_engine.set_timezone(tz)
        except Exception:
            pass
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
        # v17: SQLite es la fuente primaria del carrusel. Los snapshots JSON
        # viejos se migran una sola vez de forma idempotente.
        self._recargar_analisis_desde_base(migrate_legacy=True)
        self.poblar_lista_snapshots()
        if self.snapshots:
            # Selecciona y carga el último elemento analizado —
            # equivalente a lo que hacía antes (imagen+curva+máscara),
            # pero ahora también restaura % de sombra y la barra de Tmrt,
            # y el resto del historial queda disponible para elegir.
            ultimo = len(self.snapshots) - 1
            self.cargar_snapshot(ultimo)
        else:
            # Proyecto sin snapshots todavía: mantener el comportamiento
            # anterior por si hay rutas sueltas guardadas.
            self.last_image_path = self._resolve_artifact_path(self.last_image_path, os.path.join("entradas", "imagenes"))
            self.last_curve_path = self._resolve_artifact_path(self.last_curve_path, os.path.join("analisis", "elementos"))
            self.last_mask_path = self._resolve_artifact_path(self.last_mask_path, os.path.join("analisis", "elementos"))
            if self.last_image_path and os.path.exists(self.last_image_path):
                self._load_image_from_path(self.last_image_path)
            if self.last_curve_path and os.path.exists(self.last_curve_path):
                self._load_curve_from_path(self.last_curve_path)
            if self.last_mask_path and os.path.exists(self.last_mask_path):
                self._load_mask_from_path(self.last_mask_path)
        self._restore_excel_files()

    def _restore_excel_files(self):
        project = self.project_manager.current_project
        if project is not None:
            if os.path.exists(project.layout.edit_excel):
                self.last_edit_excel_path = project.layout.edit_excel
            if os.path.exists(project.layout.model_excel):
                self.last_model_excel_path = project.layout.model_excel
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

    def poblar_lista_snapshots(self, selected_analysis_id=None):
        """Sincroniza contador y carrusel con la base de análisis.

        ``self.snapshots`` sigue existiendo como cache compatible para los
        reportes, pero desde v17 cada entrada completa tiene ``analysis_id`` y
        proviene de SQLite.
        """
        if hasattr(self, "status_elements_var"):
            self.status_elements_var.set(f"Elementos: {len(self.snapshots)}")
        if hasattr(self, "carrusel_inner"):
            self._carrusel_actualizar(selected_analysis_id=selected_analysis_id)

    def _registrar_histograma_en_carrusel(self):
        """Persiste/actualiza el análisis actual y refresca el carrusel.

        Antes esta función agregaba una entrada provisional a la lista. Esa
        lógica era la causa del bug de duplicación: seleccionar una miniatura
        regeneraba la curva/histograma y volvía a hacer ``append``. Ahora el
        registro se guarda por ``analysis_id`` con UPSERT en SQLite.
        """
        hist = getattr(self, "last_histogram_path", None)
        if not hist or not os.path.exists(str(hist)):
            return
        self.snapshot_service.capture_analysis_record(auto=True)

    def cargar_snapshot(self, index: int):
        """Restaura un registro completo del carrusel sin recalcularlo.

        Desde v17 el click recupera de SQLite + artefactos persistidos:
        foto original, curva Tmrt, máscaras/ROIs de cálculo y referencia,
        matrices válidas, promedio gris, cobertura, atenuación y
        transmitancia. Para snapshots legacy se conservan fallbacks.
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

        # Limpiar completamente el estado visual del elemento anterior antes
        # de restaurar el seleccionado. Luego fijamos el ID para que un futuro
        # Guardar/Recalcular haga UPDATE del mismo registro.
        self._reset_panel2_for_new_image()
        self.current_analysis_id = entry.get("analysis_id")

        image_path = _abs(entry.get("image"))
        curve_path = _abs(entry.get("curve"))
        reference_path = _abs(entry.get("reference"))
        matrix_path = _abs(entry.get("matrix"))
        calc_data_path = _abs(entry.get("calc_data"))
        reference_data_path = _abs(entry.get("reference_data"))
        photo_analysis_path = _abs(entry.get("photo_analysis_data"))
        tmrt_data_path = _abs(entry.get("tmrt_data"))
        histogram_path = _abs(entry.get("histogram"))
        classification_path = _abs(entry.get("shadow_classification"))
        temperature_summary_path = _abs(entry.get("temperature_summary"))

        if image_path and os.path.exists(image_path):
            self._load_image_from_path(image_path)
            # En snapshots históricos la imagen puede llamarse elementoN.png;
            # el nombre conceptual del árbol es el label guardado.
            if entry.get("label"):
                self.current_image_stem = str(entry["label"])

        # Nuevos bundles NPZ preservan máscara válida y máscara full-size.
        calc_loaded = self._load_area_bundle(calc_data_path, "calculo")
        ref_loaded = self._load_area_bundle(reference_data_path, "referencia")

        # Fallback para snapshots <=v16.
        if not ref_loaded and reference_path and os.path.exists(reference_path):
            self._load_mask_from_path(reference_path)
        if not calc_loaded and matrix_path and os.path.exists(matrix_path):
            try:
                self.shape_selector.area_seleccionada = pd.read_excel(matrix_path).to_numpy()
                self.shape_selector.area_seleccionada_mask = np.ones_like(
                    self.shape_selector.area_seleccionada, dtype=bool
                )
                self.last_matrix_path = matrix_path
            except Exception:
                pass

        self.area_calculo_done = self.shape_selector.area_seleccionada is not None
        self.area_referencia_done = self.shape_selector.area_referencia is not None

        # Cada análisis puede haberse calculado con una resolución distinta.
        # Al seleccionarlo, el control refleja la resolución REAL del bundle
        # restaurado; esto no recalcula nada ni modifica sus resultados.
        matrix_n = entry.get("matrix_size")
        if self.area_calculo_done:
            arr_calc = np.asarray(self.shape_selector.area_seleccionada)
            if arr_calc.ndim == 2 and arr_calc.shape[0] == arr_calc.shape[1]:
                matrix_n = int(arr_calc.shape[0])
        matrix_n = normalize_matrix_size(matrix_n if matrix_n is not None else DEFAULT_MATRIX_SIZE)
        previous_suspend = getattr(self, "_suspend_autosave_tracking", False)
        self._suspend_autosave_tracking = True
        try:
            self.matriz_size.set(matrix_n)
            self.panel2_advanced_mode.set(matrix_n != DEFAULT_MATRIX_SIZE)
            self._toggle_panel2_advanced()
        finally:
            self._suspend_autosave_tracking = previous_suspend

        if self.area_calculo_done:
            self.area_ref_button.config(state=tk.NORMAL)
        if self.area_calculo_done and self.area_referencia_done:
            self.confirm_button.config(state=tk.NORMAL)

        # Restaurar ROIs visuales. Las máscaras full-size quedan además en
        # ShapeSelector para cálculos/inspección posteriores.
        self.shape_selector.shape_patch_calculo = self._restaurar_patch(
            entry.get("poly_calculo"), "blue")
        self.shape_selector.shape_patch_referencia = self._restaurar_patch(
            entry.get("poly_referencia"), "red")
        if self.ax1 is not None and self.img_rgb is not None:
            self.ax1.clear()
            self.ax1.imshow(self.img_rgb)
            self._setup_hover_shadow_percent_photo(self.ax1, self.canvas1, self.img_rgb)
            if self.shape_selector.shape_patch_calculo is not None:
                self.ax1.add_patch(self.shape_selector.shape_patch_calculo)
            if self.shape_selector.shape_patch_referencia is not None:
                self.ax1.add_patch(self.shape_selector.shape_patch_referencia)
            self.canvas1.draw()

        # Valores de las áreas: se recuperan, no se vuelven a inferir.
        calc_text = entry.get("area_calculo_text")
        ref_text = entry.get("area_referencia_text")
        if calc_text:
            self.lbl_dimensiones_calculo.config(text=calc_text)
        elif entry.get("area_calculo_px") is not None:
            self.lbl_dimensiones_calculo.config(
                text=f"Área de Cálculo: {int(entry['area_calculo_px'])} px válidos")
        if ref_text:
            self.lbl_dimensiones_referencia.config(text=ref_text)
        elif entry.get("area_referencia_px") is not None:
            self.lbl_dimensiones_referencia.config(
                text=f"Área de Referencia: {int(entry['area_referencia_px'])} px válidos")

        promedio = entry.get("promedio_gris")
        if isinstance(promedio, (int, float)):
            self.ref_gray_mean = float(promedio)
        elif self.shape_selector.area_referencia is not None:  # legacy
            try:
                self.ref_gray_mean = self.image_processor.media_valida(
                    self.shape_selector.area_referencia,
                    self.shape_selector.area_referencia_mask,
                )
            except Exception:
                self.ref_gray_mean = None
        if self.ref_gray_mean is not None:
            self.lbl_promedio_referencia.config(
                text=f"Promedio Gris Referencia: {self.ref_gray_mean:.2f}")

        cobertura = entry.get("cobertura_sombra", entry.get("porcentaje_sombra"))
        atenuacion = entry.get("atenuacion_sombra")
        tau_eff = entry.get("transmitancia_efectiva")
        self.cobertura_sombra = cobertura
        self.atenuacion_sombra = atenuacion
        self.porcentaje_sombra = cobertura
        if isinstance(cobertura, (int, float)):
            self.lbl_porcentaje_sombra.config(text=f"Cobertura de sombra: {cobertura:.2f}%")
        if isinstance(atenuacion, (int, float)) and hasattr(self, "lbl_atenuacion_sombra"):
            self.lbl_atenuacion_sombra.config(text=f"Atenuación en sombra: {atenuacion:.2f}%")
        if isinstance(tau_eff, (int, float)) and hasattr(self, "lbl_transmitancia_sombra"):
            self.lbl_transmitancia_sombra.config(text=f"Transmitancia efectiva: {tau_eff*100:.2f}%")

        # Recuperar exactamente el análisis fotográfico y mapas guardados.
        self.shadow_photo_analysis = self._load_photo_analysis_bundle(photo_analysis_path, entry)
        if self.shadow_photo_analysis is None and self.area_calculo_done and self.area_referencia_done:
            # Compatibilidad exclusiva con registros viejos que no guardaban
            # los mapas: solo en ese caso se recompone desde matrices.
            try:
                self.shadow_photo_analysis = self.image_processor.analizar_sombra_fotografica(
                    self.shape_selector.area_seleccionada,
                    self.shape_selector.area_referencia,
                    mascara_area=self.shape_selector.area_seleccionada_mask,
                    mascara_referencia=self.shape_selector.area_referencia_mask,
                )
            except Exception:
                self.shadow_photo_analysis = None
        if self.shadow_photo_analysis is not None and hasattr(self, "shadow_mask_button"):
            self.shadow_mask_button.config(state=tk.NORMAL)
        if classification_path and os.path.exists(classification_path):
            self.last_shadow_classification_path = classification_path
        if temperature_summary_path and os.path.exists(temperature_summary_path):
            self.last_temp_graph_path = temperature_summary_path
        if histogram_path and os.path.exists(histogram_path):
            self.last_histogram_path = histogram_path

        # Curva: cargar matrices guardadas y reconstruir canvas interactivo sin
        # llamar mostrar_curvas_nivel(). Eso evita duplicar y evita recalcular.
        tmrt_loaded = self._load_tmrt_bundle(tmrt_data_path)
        if tmrt_loaded:
            self._render_stored_tmrt_map(entry)
        elif curve_path and os.path.exists(curve_path):
            self._load_curve_from_path(curve_path)
        if curve_path and os.path.exists(curve_path):
            self.last_curve_path = curve_path

        # Barra Tmrt escalar, si el registro la tenía.
        tmrt_sombra = entry.get("tmrt_sombra")
        temp_ambient = entry.get("temp_ambient")
        tmrt_sol = entry.get("tmrt_sol")
        valor_sol_grafico = tmrt_sol if tmrt_sol is not None else temp_ambient
        if tmrt_sombra is not None and valor_sol_grafico is not None:
            self.tmrt_result = {
                "Tmrt_sol": tmrt_sol,
                "Tmrt_sombra": tmrt_sombra,
                "Delta_Tmrt": entry.get("delta_tmrt"),
                "Modelo_Tmrt": entry.get("modelo_tmrt"),
            }
            if hasattr(self, "lbl_tmrt_sol") and tmrt_sol is not None:
                self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {tmrt_sol:.2f} °C")
            if hasattr(self, "lbl_tmrt_sombra"):
                self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {tmrt_sombra:.2f} °C")
            if hasattr(self, "lbl_delta_tmrt") and entry.get("delta_tmrt") is not None:
                self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {entry['delta_tmrt']:.2f} °C")
            if hasattr(self, "graph_frame"):
                self._show_temperature_graph(valor_sol_grafico, tmrt_sombra)

        self.curve_button.config(state=tk.NORMAL if self.area_calculo_done else tk.DISABLED)
        self._carrusel_marcar(index)

    def _clear_temperature_graph(self):
        """Libera canvas/figura de la barra Tmrt anterior.

        Destruir solo el widget Tk no libera necesariamente el árbol de
        artistas de Matplotlib. v18 conserva una única figura y la limpia de
        forma explícita al reemplazarla.
        """
        canvas = getattr(self, "_temp_graph_canvas", None)
        if canvas is not None:
            try:
                widget = canvas.get_tk_widget()
                if widget.winfo_exists():
                    widget.destroy()
            except Exception:
                pass
        fig = getattr(self, "_temp_graph_figure", None)
        if fig is not None:
            try:
                fig.clear()
            except Exception:
                pass
        self._temp_graph_canvas = None
        self._temp_graph_figure = None

    def _show_temperature_graph(self, tmrt_sol, tmrt_sombra):
        self._clear_temperature_graph()
        fig, canvas = TemperatureGraph(tmrt_sol, tmrt_sombra, self.graph_frame).plot_temperature_scale()
        self._temp_graph_figure = fig
        self._temp_graph_canvas = canvas
        return fig

    def _load_area_bundle(self, file_path, kind: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with np.load(file_path, allow_pickle=False) as data:
                values = np.asarray(data["values"])
                valid = np.asarray(data["valid_mask"], dtype=bool)
                full = np.asarray(data["full_mask"], dtype=bool) if "full_mask" in data else np.empty((0, 0), dtype=bool)
            if kind == "calculo":
                self.shape_selector.area_seleccionada = values
                self.shape_selector.area_seleccionada_mask = valid
                self.shape_selector.mask_calculo_full = full if full.size else None
                self.last_matrix_path = file_path
            else:
                self.shape_selector.area_referencia = values
                self.shape_selector.area_referencia_mask = valid
                self.shape_selector.mask_referencia_full = full if full.size else None
                self.last_mask_path = file_path
            return True
        except Exception as exc:
            print(f"[carrusel] no se pudo cargar bundle {kind}: {exc}")
            return False

    def _load_photo_analysis_bundle(self, file_path, entry):
        arrays = {}
        if file_path and os.path.exists(file_path):
            try:
                with np.load(file_path, allow_pickle=False) as data:
                    arrays = {key: np.asarray(data[key]) for key in data.files}
            except Exception as exc:
                print(f"[carrusel] no se pudo cargar análisis fotográfico: {exc}")
                arrays = {}
        if not arrays and not entry.get("algoritmo_sombra"):
            return None
        return {
            "algorithm": entry.get("algoritmo_sombra", "snapshot-restored"),
            "coverage_pct": entry.get("cobertura_sombra", entry.get("porcentaje_sombra")),
            "attenuation_pct": entry.get("atenuacion_sombra"),
            "shadow_transmittance": entry.get("transmitancia_sombra"),
            "effective_transmittance": entry.get("transmitancia_efectiva"),
            "effective_attenuation_pct": entry.get("atenuacion_efectiva"),
            "threshold_ratio": entry.get("umbral_sombra_ratio"),
            "reference_gray": entry.get("promedio_gris"),
            "legacy_shadow_index_pct": entry.get("indice_sombra_legacy"),
            **arrays,
        }

    def _load_tmrt_bundle(self, file_path) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with np.load(file_path, allow_pickle=False) as data:
                restored = {}
                for key in data.files:
                    value = np.asarray(data[key])
                    if value.ndim == 0:
                        restored[key] = float(value)
                    elif np.issubdtype(value.dtype, np.floating):
                        restored[key] = value.astype(np.float32, copy=False)
                    else:
                        restored[key] = value
            tmrt = restored.get("tmrt")
            if tmrt is None:
                return False
            self.tmrt_hover_data = restored
            self.tmrt_map = np.asarray(tmrt, dtype=np.float32)
            self.curvas_nivel_creadas = True
            self._curve_pinned_pixel = None
            return True
        except Exception as exc:
            print(f"[carrusel] no se pudo cargar datos Tmrt: {exc}")
            return False

    @staticmethod
    def _contour_display_grid(mapa, max_side=320):
        """Malla reducida solo para dibujar contourf.

        El mapa científico y el hover siguen usando la matriz completa.
        Matplotlib contourf construye paths vectoriales y su consumo crece
        mucho en resoluciones altas; dibujar una malla <=320 por lado reduce RAM sin
        alterar los valores guardados ni consultados.
        """
        arr = np.asarray(mapa, dtype=np.float32)
        h, w = arr.shape
        stride = max(1, int(np.ceil(max(h, w) / float(max_side))))
        display = arr[::stride, ::stride]
        xs = np.arange(0, w, stride, dtype=np.float32)[:display.shape[1]]
        ys = np.arange(0, h, stride, dtype=np.float32)[:display.shape[0]]
        return xs, ys, display, stride

    def _render_stored_tmrt_map(self, entry):
        """Redibuja la curva guardada a partir de sus matrices, sin física."""
        mapa = np.asarray(self.tmrt_map, dtype=np.float32)
        finite = mapa[np.isfinite(mapa)]
        if not finite.size:
            return
        from plot_style import CMAP_CURVAS_NIVEL, agregar_colorbar_temperatura

        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None
        self.fig2.clf()
        ax = self.fig2.add_subplot(111)
        self.ax2 = ax
        x_disp, y_disp, mapa_disp, _stride = self._contour_display_grid(mapa)
        tmin, tmax = float(np.min(finite)), float(np.max(finite))
        span = tmax - tmin
        if span > 1e-9:
            niveles = np.linspace(tmin, tmax, 21)
            relleno = ax.contourf(x_disp, y_disp, mapa_disp, levels=niveles, cmap=CMAP_CURVAS_NIVEL, vmin=tmin, vmax=tmax, antialiased=True)
            ax.contour(x_disp, y_disp, mapa_disp, levels=niveles[::2], colors="0.35", linewidths=0.45, alpha=0.55)
            ticks = np.linspace(tmin, tmax, 6)
        else:
            eps = max(0.01, abs(tmin) * 1e-6)
            relleno = ax.contourf(x_disp, y_disp, mapa_disp, levels=[tmin-eps, tmin+eps], cmap=CMAP_CURVAS_NIVEL, vmin=tmin-eps, vmax=tmin+eps)
            ticks = np.array([tmin])
        ax.set_xlim(0, mapa.shape[1] - 1)
        ax.set_ylim(0, mapa.shape[0] - 1)
        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        ax.set_title(f"Tmrt guardada — {entry.get('label', 'elemento')}\nregistro {entry.get('analysis_id', '')[:8]}", fontsize=9)
        agregar_colorbar_temperatura(self.fig2, ax, relleno, unidad="°C", etiqueta="Tmrt", ticks=ticks)
        ax.text(0.01, 0.01, f"Rango guardado: {tmin:.2f}–{tmax:.2f} °C", transform=ax.transAxes, fontsize=7.5,
                va="bottom", ha="left", bbox=dict(boxstyle="round", fc="white", ec="0.75", alpha=0.82))
        self.fig2.tight_layout(pad=0.8)
        widget = self.canvas2.get_tk_widget()
        if not widget.winfo_ismapped():
            widget.pack(fill="both", expand=True)
        self._setup_hover_tmrt_map(ax, self.canvas2)
        self.canvas2.draw_idle()

    def _restaurar_patch(self, datos, color):
        """Reconstruye el patch dibujado (polígono/rectángulo/círculo)
        a partir de lo serializado en el snapshot."""
        if not isinstance(datos, dict):
            return None
        from matplotlib.patches import Circle, Polygon, Rectangle
        tipo = datos.get("tipo")
        pts = datos.get("puntos") or []
        if tipo == "rectangulo" and len(pts) >= 4:
            return Rectangle((pts[0], pts[1]), pts[2], pts[3],
                             edgecolor=color, facecolor="none", linewidth=2)
        if tipo == "circulo" and len(pts) >= 3:
            return Circle((pts[0], pts[1]), pts[2],
                          edgecolor=color, facecolor="none", linewidth=2)
        if len(pts) >= 3:
            return Polygon(pts, closed=True, edgecolor=color,
                           facecolor=color, alpha=0.3, linewidth=2)
        return None

    def _load_image_from_path(self, file_path: str):
        try:
            self.img = None
            self.img_rgb = self.image_processor.load_image_rgb(file_path)
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
        image_dir = project.layout.images_dir
        os.makedirs(image_dir, exist_ok=True)
        destination_path = project.layout.import_input_file(source_path, image_dir)
        print(f"[panel2] Imagen registrada en proyecto: {source_path} -> {destination_path}")
        if not os.path.exists(destination_path):
            raise FileNotFoundError(f"No se pudo copiar la imagen a {destination_path}")

        destination_str = str(destination_path)
        destination_basename = os.path.basename(destination_str)
        self.current_image_path = destination_str
        self.current_image_basename = destination_basename
        self.current_image_stem = os.path.splitext(destination_basename)[0]
        self.last_image_path = destination_str
        return destination_str

    def _copy_excel_to_project(self, source_path: str, folder: str) -> str:
        """Importa un Excel externo como archivo de trabajo estable v19."""
        project = self.project_manager.current_project
        if project is None:
            raise RuntimeError("No hay proyecto abierto")
        low = str(folder).lower()
        destination = project.layout.model_excel if "model" in low else project.layout.edit_excel
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        if os.path.abspath(source_path) != os.path.abspath(destination):
            shutil.copy2(source_path, destination)
        return str(destination)

    def _reset_panel2_for_new_image(self):
        self.shape_selector.clear_panel2_selection()
        self.current_analysis_id = None
        self.drawing_mode = None
        self.selection_mode = None
        self.area_calculo_done = False
        self.area_referencia_done = False
        self.porcentaje_sombra = None
        self.cobertura_sombra = None
        self.atenuacion_sombra = None
        self.shadow_photo_analysis = None
        self.last_shadow_classification_path = None
        self.ref_gray_mean = None
        self.tmrt_map = None
        self.tmrt_hover_data = None
        # Liberar la fotografía pesada del elemento anterior antes de leer
        # la siguiente. Matplotlib conserva su propia referencia hasta clear.
        if hasattr(self, "ax1") and self.ax1 is not None:
            self.ax1.clear()
        self.img = None
        self.img_rgb = None
        self.original_rgb = None
        self._clear_temperature_graph()
        self._curve_pinned_pixel = None
        self.curvas_nivel_creadas = False
        self.lbl_porcentaje_sombra.config(text="Cobertura de sombra: N/A")
        if hasattr(self, "lbl_atenuacion_sombra"):
            self.lbl_atenuacion_sombra.config(text="Atenuación en sombra: N/A")
        if hasattr(self, "lbl_transmitancia_sombra"):
            self.lbl_transmitancia_sombra.config(text="Transmitancia efectiva: N/A")
        if hasattr(self, "shadow_mask_button"):
            self.shadow_mask_button.config(state=tk.DISABLED)
        self.lbl_dimensiones_calculo.config(text="Área de Cálculo: N/A")
        self.lbl_dimensiones_referencia.config(text="Área de Referencia: N/A")
        self.lbl_promedio_referencia.config(text="Promedio Gris Referencia: N/A")
        self.confirm_button.config(state=tk.DISABLED)
        self.curve_button.config(state=tk.DISABLED)
        self.area_ref_button.config(state=tk.DISABLED)
        self.shape_selector.enable_calculo_button()
        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None
            self.curva_img_pil_original = None
        if self.canvas2 is not None:
            # Al cambiar de imagen eliminamos también colorbar, anotaciones
            # y conexiones visuales de la curva anterior.
            if self._curve_hover_cid is not None:
                try:
                    self.canvas2.mpl_disconnect(self._curve_hover_cid)
                except Exception:
                    pass
                self._curve_hover_cid = None
            if self._curve_click_cid is not None:
                try:
                    self.canvas2.mpl_disconnect(self._curve_click_cid)
                except Exception:
                    pass
                self._curve_click_cid = None
            self._curve_hover_annotation = None
            self._curve_hover_canvas = None
            if hasattr(self, "fig2") and self.fig2 is not None:
                self.fig2.clf()
                self.ax2 = self.fig2.add_subplot(111)
            widget = self.canvas2.get_tk_widget()
            if widget.winfo_exists():
                widget.pack(fill="both", expand=True)
                self.canvas2.draw_idle()
        collect_and_log("panel2 liberado")
                
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
        with Image.open(file_path) as img:
            self.curva_img_pil_original = img.copy()
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
                self.shape_selector.area_referencia_mask = np.ones_like(self.shape_selector.area_referencia, dtype=bool)
            elif ext in (".png", ".jpg", ".jpeg"):
                with Image.open(file_path) as img:
                    self.shape_selector.area_referencia = np.asarray(img.convert("L"), dtype=np.uint8).copy()
                self.shape_selector.area_referencia_mask = np.ones_like(self.shape_selector.area_referencia, dtype=bool)
        except Exception:
            return
        
    def setup_variables(self):
        """Inicializa las variables de control para la aplicación"""
        self.selection_type = tk.StringVar(value="Polígono")
        self.matriz_size = tk.IntVar(value=DEFAULT_MATRIX_SIZE)
        self.panel2_advanced_mode = tk.BooleanVar(value=False)        
        self.tmrt_model_mode = tk.StringVar(value=self.settings.get("tmrt_model_mode", "standard"))
        self.surface_model_mode = tk.StringVar(value=self.settings.get("surface_model_mode", "standard"))
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
        self.modo_temperatura = tk.StringVar(value="simple")
        self.panel2_advanced_mode = tk.BooleanVar(value=False)
        self.simple_country = tk.StringVar()
        self.simple_city = tk.StringVar()
        self.simple_cloudiness = tk.StringVar(value="Despejado")
        self.simple_temp_air_c = tk.DoubleVar(value=25.0)
        self.simple_rh = tk.DoubleVar(value=60.0)
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
        manager = getattr(self, "project_manager", None)
        if manager is not None:
            manager.schedule_autosave()

    def _install_autosave_variable_traces(self):
        """Observa parámetros editables y dispara autosave con debounce.

        Los resultados pesados (imágenes, matrices, máscaras, SQLite) se
        persisten en el momento en que se generan. Este rastreo cubre el otro
        caso: cambios de campos/combos que antes podían quedar solo en RAM
        hasta que el usuario pulsara Guardar.
        """
        if getattr(self, "_autosave_trace_tokens", None):
            return
        self._autosave_trace_tokens = []
        seen = set()

        def register(var):
            if not isinstance(var, tk.Variable) or id(var) in seen:
                return
            seen.add(id(var))
            try:
                token = var.trace_add("write", self._on_project_variable_changed)
                self._autosave_trace_tokens.append((var, token))
            except Exception:
                pass

        for mapping in (getattr(self, "vars", {}), getattr(self, "vars_modelo", {})):
            if isinstance(mapping, dict):
                for value in mapping.values():
                    register(value)

        for name in (
            "selection_type", "matriz_size", "panel2_advanced_mode",
            "tmrt_model_mode", "surface_model_mode", "modo_modelo",
            "modo_edicion", "modo_temperatura", "simple_country", "simple_city",
            "simple_cloudiness", "simple_temp_air_c", "simple_rh",
            "temp_unit", "distance_unit", "shadow_detector_enabled",
            "use_pvlib_engine", "radiation_source_mode", "manual_ghi",
            "manual_dni", "manual_dhi",
        ):
            register(getattr(self, name, None))

    def _on_project_variable_changed(self, *_args):
        if getattr(self, "_suspend_autosave_tracking", False):
            return
        manager = getattr(self, "project_manager", None)
        if manager is None or getattr(manager, "current_project", None) is None:
            return
        self.mark_dirty()

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
            "humedad": tk.DoubleVar(value=50.0),
            "viento": tk.StringVar(value="moderado"),
            "nubosidad": tk.StringVar(value="Despejado"),
            "timezone": tk.StringVar(value="America/Argentina/Buenos_Aires"),
            "arboles": [],
            "estructuras": [],
            "_update_required": True,
            "_app_instance":self,
        }
        # Controles de parámetros
        
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
        self.cargar_imagen_button.pack(fill="x", padx=20, pady=4)
        self.panel2_advanced_check = tk.Checkbutton(
            panel,
            text="Modo avanzado\n(resolución 64–640)",
            justify="left",
            variable=self.panel2_advanced_mode,
            bg=panel.cget("bg"),
            command=self._toggle_panel2_advanced,
        )
        self.panel2_advanced_check.pack(fill="x", padx=20, pady=2)
        self.shadow_detector_check = tk.Checkbutton(
            panel,
            text="Detector sombras IA",
            variable=self.shadow_detector_enabled,
            bg=panel.cget("bg"),
        )
        self.shadow_detector_check.pack(fill="x", padx=20, pady=2)

        # Selección del tamaño de la matriz
        matrix_label = tk.Label(panel, text="Resolución de matriz (N × N):", bg=panel.cget("bg"), fg="black")
        matrix_label.pack(fill="x", padx=20, pady=(4, 0))

        self.matrix_size_combo = ttk.Combobox(
            panel,
            textvariable=self.matriz_size,
            values=MATRIX_SIZE_OPTIONS,
            state="readonly",
        )
        self.matrix_size_combo.pack(fill="x", padx=20, pady=(0, 1))
        tk.Label(
            panel,
            text="Paso 32 · predeterminado: 128 × 128",
            bg=panel.cget("bg"),
            fg="#555555",
            font=("Arial", 8),
        ).pack(fill="x", padx=20, pady=(0, 3))

        # Botones de selección de área
        self.area_calc_button = tk.Button(panel, text="Seleccione área de cálculo",bg='blue',fg='white', command=self.shape_selector.select_area_calculo, state=tk.DISABLED)
        self.area_calc_button.pack(fill="x",padx=20, pady=4)

        self.area_ref_button = tk.Button(panel, text="Seleccione área de referencia",bg='red',fg='white', command=self.shape_selector.select_area_referencia, state=tk.DISABLED)
        self.area_ref_button.pack(fill="x",padx=20, pady=4)

        # Botones de confirmación y cálculo
        process_label = tk.Label(panel, text="Calcular y procesar:", bg=panel.cget("bg"), fg="black")
        process_label.pack(fill="x", padx=20, pady=(4, 0))

        self.confirm_button = tk.Button(panel, text="Confirmar selección y calcular", command=self.confirmar_seleccion, state=tk.DISABLED)
        self.confirm_button.pack(fill="x",padx=20, pady=4)

        self.shadow_mask_button = tk.Button(
            panel,
            text="Ver máscara sombra / sol",
            command=self.mostrar_mascara_sombra,
            state=tk.DISABLED,
        )
        self.shadow_mask_button.pack(fill="x", padx=20, pady=4)

        self.curve_button = tk.Button(panel, text="Generar curva de nivel", command=self.mostrar_curvas_nivel, state=tk.DISABLED)
        self.curve_button.pack(fill="x",padx=20, pady=4)
        
        self.save_dataset_button = tk.Button(panel, text="Respaldar Dataset", command=self.save_dataset, state=tk.DISABLED)
        self.save_dataset_button.pack(fill="x", padx=20, pady=4)

        self._toggle_panel2_advanced()
        
    def setup_panel_3(self):
        """Configura el contenido del Panel 3"""
        panel = self.panel_frames[2]

        for widget in panel.winfo_children():
            widget.destroy()        

        # MISMO BUG QUE EL PANEL 4 (ver docstring de setup_panel_4 en
        # ui/panels.py): acá se creaba un SEGUNDO canvas scrolleable
        # anidado vía _build_scrollable_content dentro del frame de
        # contenido que YA vive en un canvas con scrollbar + rueda del
        # mouse. El canvas anidado quedaba con altura propia chica y
        # sin rueda propia — los controles de abajo (radios de modo,
        # ubicación del proyecto, viento, fecha/hora) quedaban cortados
        # e inalcanzables ("ocultos"). Ahora los widgets van directo
        # sobre `panel`, igual que en los paneles 1/2/4.
        panel.grid_columnconfigure(0, weight=1)
        contenido = panel
        contenido.grid_columnconfigure(0, weight=1)
        # Mismo fix aplicado a setup_panel_4 (ui/panels.py): sin esto,
        # simple_edit_frame/advanced_edit_frame (fila 3, sticky="nsew")
        # nunca reciben el alto sobrante del panel aunque el Canvas
        # contenedor ya lo tenga disponible.
        contenido.grid_rowconfigure(3, weight=1)

        diseno_label = tk.Label(contenido, text="Modo de Edición:", bg=panel.cget("bg"), fg="black")
        diseno_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        acciones = tk.Frame(contenido, bg=panel.cget("bg"))
        acciones.grid(row=1, column=0, sticky="ew", pady=2)
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
        add_arbol.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=3)

        add_estructura = tk.Button(
            acciones,
            text="Añadir Estructura",
            command=lambda: self._run_with_project("editar la escena", lambda: design.establecer_modo('estructura', self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        add_estructura.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=3)

        seleccionar = tk.Button(
            acciones,
            text="Seleccionar",
            command=lambda: self._run_with_project("editar la escena", lambda: design.establecer_modo(None, self)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        seleccionar.grid(row=2, column=0, sticky="ew", padx=(0, 12), pady=3)

        guardar = tk.Button(
            acciones,
            text="Respaldar Excel",
            command=lambda: self._run_with_project(
                "respaldar el archivo de edición",
                lambda: design.guardar(self.vars, self, filepath=self.project_manager.current_project.layout.edit_excel),
            ),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        guardar.grid(row=3, column=0, sticky="ew", padx=(0, 12), pady=3)

        abrir = tk.Button(
            acciones,
            text="Abrir",
            command=lambda: self.abrir_excel_edicion(),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        abrir.grid(row=4, column=0, sticky="ew", padx=(0, 12), pady=3)

        grafico = tk.Button(
            acciones,
            text="Generar gráfico",
            command=lambda: self._run_with_project("generar el gráfico de edición", lambda: self.actualizar_grafico_diseno(self.frame7)),
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        grafico.grid(row=5, column=0, sticky="ew", padx=(0, 12), pady=4)

        vista_3d = tk.Button(
            acciones,
            text="Vista 3D",
            command=self.mostrar_vista_3d_diseno,
            bg='#4CAF50',
            fg='white',
            font=("Arial", 8, "bold"),
        )
        vista_3d.grid(row=6, column=0, sticky="ew", padx=(0, 12), pady=4)

        modo_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        modo_frame.grid(row=2, column=0, sticky="w", pady=2)
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
        self.simple_edit_frame.grid(row=3, column=0, sticky="nsew", pady=3)
        self.simple_edit_frame.grid_columnconfigure(1, weight=1)
        tk.Label(self.simple_edit_frame, text="Ubicación fija del proyecto", bg=panel.cget("bg")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 3)
        )
        self.edit_location_label = tk.Label(self.simple_edit_frame, text="Sin proyecto", bg=panel.cget("bg"))
        self.edit_location_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=1)
        self.edit_latlon_label = tk.Label(self.simple_edit_frame, text="", bg=panel.cget("bg"))
        self.edit_latlon_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=1)

        self.advanced_edit_frame = tk.Frame(contenido, bg=panel.cget("bg"))
        self.advanced_edit_frame.grid(row=3, column=0, sticky="nsew", pady=3)
        self.advanced_edit_frame.grid_columnconfigure(1, weight=1)

        tk.Label(self.advanced_edit_frame, text="Viento", bg=panel.cget("bg")).grid(
            row=0, column=0, sticky="w", pady=(3, 2))
        ttk.Combobox(
            self.advanced_edit_frame,
            textvariable=self.vars["viento"],
            values=["nulo", "moderado", "fuerte"],
            state="normal",
        ).grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=2)
        tk.Label(
            self.advanced_edit_frame,
            text="Categoría o m/s: nulo≈0.5 · moderado≈4 · fuerte≈10",
            bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
        ).grid(row=1, column=0, columnspan=2, sticky="w")

        tk.Label(self.advanced_edit_frame, text="Nubosidad", bg=panel.cget("bg")).grid(
            row=2, column=0, sticky="w", pady=2)
        ttk.Combobox(
            self.advanced_edit_frame,
            textvariable=self.vars["nubosidad"],
            values=["Despejado", "Parcial", "Nublado"],
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=(8, 12), pady=2)

        tk.Label(
            self.advanced_edit_frame, text="Modelo de superficie",
            bg=panel.cget("bg"), font=("Arial", 8, "bold"),
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 1))
        surface_frame = tk.Frame(self.advanced_edit_frame, bg=panel.cget("bg"))
        surface_frame.grid(row=4, column=0, columnspan=2, sticky="w")
        for label, value in (
            ("Estándar", "standard"),
            ("Avanzado seco", "advanced"),
            ("Vegetación + ET", "advanced_vegetation"),
        ):
            tk.Radiobutton(
                surface_frame, text=label, variable=self.surface_model_mode, value=value,
                bg=panel.cget("bg"), anchor="w",
            ).pack(anchor="w")
        tk.Label(
            self.advanced_edit_frame,
            text="Humedad y nubosidad intervienen plenamente en los balances avanzados; el modo Estándar conserva el modelo histórico.",
            bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
            justify="left", wraplength=210,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(1, 3))

        tk.Label(
            self.advanced_edit_frame, text="Configuraciones rápidas",
            bg=panel.cget("bg"), font=("Arial", 8, "bold"),
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(5, 2))
        preset_frame = tk.Frame(self.advanced_edit_frame, bg=panel.cget("bg"))
        preset_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 3))
        preset_frame.grid_columnconfigure(0, weight=1)
        preset_frame.grid_columnconfigure(1, weight=1)
        for idx, (label, preset) in enumerate((
            ("Verano", "verano"), ("Invierno", "invierno"),
            ("Soleado", "soleado"), ("Nublado", "nublado"),
        )):
            tk.Button(
                preset_frame, text=label,
                command=lambda p=preset: modelo.cargar_preset(p, self.vars),
                bg="#4CAF50", fg="white", font=("Arial", 7, "bold"),
            ).grid(row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=2)
        tk.Label(
            self.advanced_edit_frame,
            text="Verano/Invierno adaptan la fecha al hemisferio. Soleado/Nublado ajustan radiación y nubosidad.",
            bg=panel.cget("bg"), fg="#666666", font=("Arial", 7),
            justify="left", wraplength=210,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 3))

        panelin = tk.Frame(self.advanced_edit_frame, bg=panel.cget("bg"))
        panelin.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=(0, 12), pady=3)
        for texto, var, fila, rango, es_fecha in self.controles:
            self.crear_control(panelin, texto, var, fila, rango, es_fecha)
        self._toggle_edicion_mode()    
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

    def _validate_kelvin_input(self):
        """Valida que los campos de temperatura del modo modelo estén en
        Kelvin (el modelo trabaja internamente en K y la UI lo dice
        explícitamente en los labels). Antes solo se validaba T_amb_base;
        ahora también T_min y T_max."""
        for var, nombre in (
            (self.vars_modelo["T_min"], "Temp. Mín"),
            (self.vars_modelo["T_max"], "Temp. Máx"),
        ):
            temp_k = var.get()
            if temp_k < 260 or temp_k > 330:
                temp_c = temp_k - 273.15
                if not messagebox.askyesno(
                    "Temperatura en Kelvin",
                    f"{nombre} está en Kelvin. Equivale a {temp_c:.1f} °C. ¿Es correcto?",
                ):
                    return False
        return True

    def _fecha_modelo_actual(self):
        iso = self.vars_modelo.get("_date_iso") if isinstance(self.vars_modelo, dict) else None
        if hasattr(iso, "get"):
            iso = iso.get()
        if iso:
            try:
                return datetime.strptime(str(iso), "%Y-%m-%d").date()
            except ValueError:
                pass
        day = int(float(self.vars_modelo["dia"].get()))
        year = int(self.vars_modelo.get("_year", datetime.now().year))
        day = max(1, min(day, 366))
        return (datetime(year, 1, 1) + timedelta(days=day - 1)).date()

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
            # Entrada simple usa su esquema rápido propio. Una fuente manual,
            # pvlib o una serie seleccionada en el modo avanzado no puede
            # seguir modificando este cálculo mientras está oculta.
            self.vars_modelo["I_sol_base"].set(i_max)
            self.vars_modelo["humedad"].set(float(self.simple_rh.get()))
            if hasattr(self.vars_modelo.get("nubosidad"), "set"):
                self.vars_modelo["nubosidad"].set(cloudiness)
            else:
                self.vars_modelo["nubosidad"] = cloudiness
        else:
            if not self._validate_kelvin_input():
                return
        self.vars_modelo["_modo_modelo"] = self.modo_modelo.get()
        self.vars_modelo["_surface_model_mode"] = self.surface_model_mode.get()

        # Fuente radiativa efectiva. En modo simple se mantiene el esquema
        # rápido histórico; fuentes meteorológicas/pvlib son opciones detalladas.
        self.vars_modelo["_radiation_override_ghi"] = None
        self.vars_modelo["_radiation_override_dni"] = None
        self.vars_modelo["_radiation_override_dhi"] = None
        self.vars_modelo["_radiation_source_label"] = "Configuración histórica Panel 4"
        self.vars_modelo["_radiation_quality"] = "legacy_configured"
        self.vars_modelo["_cloud_fraction_override"] = None
        self.vars_modelo["_air_temp_override_k"] = None
        source_mode = (
            self.radiation_source_mode.get()
            if self.modo_modelo.get() == "advanced" else "clear_sky"
        )
        use_clear_sky_engine = (
            self.modo_modelo.get() == "advanced"
            and source_mode == "clear_sky"
            and bool(self.use_pvlib_engine.get())
            and bool(getattr(self.solar_engine, "pvlib_available", False))
        )
        use_external_radiation = (
            source_mode in {"manual_measured", "manual_scenario", "observed_series"}
            or use_clear_sky_engine
        )
        if use_external_radiation:
            try:
                fecha_modelo = self._fecha_modelo_actual()
                lat = float(self.vars_modelo["lat"].get())
                lon = float(self.vars_modelo["lon"].get())
                hora = float(self.vars_modelo["hora"].get())
                manual_ghi = float(self.vars_modelo["I_sol_base"].get()) if source_mode.startswith("manual_") else None
                met = self._obtener_datos_solares(lat, lon, fecha_modelo, hora, manual_ghi=manual_ghi)

                # En cielo claro modelado, la categoría de nubosidad genera un
                # escenario atenuado. Datos observados/medidos no se atenúan dos veces.
                if source_mode == "clear_sky":
                    cloud_var = self.vars_modelo.get("nubosidad", "Despejado")
                    cloudiness = cloud_var.get() if hasattr(cloud_var, "get") else str(cloud_var)
                    factor_cloud = factor_ghi_nubosidad(cloudiness)
                    if factor_cloud != 1.0:
                        scenario_ghi = max(0.0, float(met["ghi"]) * float(factor_cloud))
                        comp = descomponer_radiacion(
                            scenario_ghi, float(met.get("elevation", 0.0)), cloudiness
                        )
                        met = dict(met)
                        met["ghi"] = scenario_ghi
                        met["dni"] = float(comp["dni_normal"])
                        met["dhi"] = float(comp["dhi"])
                        met["source_label"] = f"{met.get('source_label', 'Cielo claro')} · {cloudiness}"
                        met["quality"] = f"{met.get('quality', 'modeled')} + escenario_nubosidad"

                self.vars_modelo["_radiation_override_ghi"] = float(met["ghi"])
                self.vars_modelo["_radiation_override_dni"] = float(met["dni"])
                self.vars_modelo["_radiation_override_dhi"] = float(met["dhi"])
                self.vars_modelo["_radiation_source_label"] = met.get("source_label", source_mode)
                self.vars_modelo["_radiation_quality"] = met.get("quality", "external")
                if source_mode == "observed_series":
                    if met.get("ta_c") is not None:
                        observed_ta_k = float(met["ta_c"]) + 273.15
                        self.vars_modelo["T_amb_base"].set(observed_ta_k)
                        self.vars_modelo["_air_temp_override_k"] = observed_ta_k
                        if self.modo_modelo.get() == "simple":
                            self.simple_temp_air_c.set(float(met["ta_c"]))
                    if met.get("rh_pct") is not None:
                        self.vars_modelo["humedad"].set(float(met["rh_pct"]))
                        if self.modo_modelo.get() == "simple":
                            self.simple_rh.set(float(met["rh_pct"]))
                    if met.get("wind_m_s") is not None:
                        self.vars_modelo["viento"].set(float(met["wind_m_s"]))
                    if met.get("cloud_fraction") is not None:
                        self.vars_modelo["_cloud_fraction_override"] = float(met["cloud_fraction"])
            except Exception as exc:
                messagebox.showerror("Meteorología", f"No se pudo resolver la fuente meteorológica seleccionada:\n{exc}")
                return

        view2d, _view3d, notebook = self._get_scene_view_frames("modelo")
        result = modelo.generar_grafico(self.vars_modelo, view2d)
        if result:
            notebook.select(view2d)
            self.last_T = result.get("T")
            self.last_shadow = result.get("shadow")
            self.last_meta = result.get("meta")
    def _ancho_viewport_actual(self):
        """Ancho usable para dimensionar el lateral en el estado actual."""
        try:
            ancho = int(self.root.winfo_width())
        except (TypeError, ValueError, tk.TclError):
            ancho = 1
        if ancho <= 200:
            try:
                ancho = int(self.root.winfo_screenwidth())
            except (TypeError, ValueError, tk.TclError):
                ancho = 1366
        return max(ancho, 1)

    def _reservar_ancho_sidebar(self, ancho):
        """Reserva físicamente la columna 0 para que frame1 no se comprima.

        ``place`` no participa en el cálculo de tamaño de ``grid``. Por eso
        configurar solo ``frame1.config(width=...)`` no garantizaba que la
        columna 0 recibiera ese ancho. El ``minsize`` de la columna sí lo
        garantiza y evita que el panel quede recortado contra frame2/frame4.
        """
        ancho = max(int(ancho), 1)
        self.frame1.configure(width=ancho)
        self.root.grid_columnconfigure(0, weight=0, minsize=ancho)
        return ancho

    def _recalcular_ancho_sidebar_abierto(self):
        self.panel_width = calcular_ancho_sidebar_abierto(self._ancho_viewport_actual())
        return self.panel_width

    def _crear_panel_desplazable(self, contenedor):
        """Crea el viewport común de TODOS los paneles laterales.

        v24 (sobre la geometría segura de v22):
        - reducción HORIZONTAL real: el sidebar completo es ~30 % más angosto
          y los widgets con ancho explícito se reducen al 70 %;
        - el contenido ocupa el 96 % del Canvas, con márgenes de ~2 % por lado,
          para no desperdiciar espacio lateral;
        - la barra vertical vive en una columna propia (fuera del Canvas),
          por lo que jamás se superpone con botones, entradas o etiquetas;
        - el texto largo se envuelve automáticamente al ancho real;
        - la rueda del mouse se vincula localmente a widgets no editables,
          evitando un ``bind_all`` global que podía interferir con otros
          controles de la aplicación.
        """
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=0)

        canvas = tk.Canvas(
            contenedor,
            bg=self.palette["panel"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=18,
        )
        scrollbar = tk.Scrollbar(
            contenedor,
            orient="vertical",
            command=canvas.yview,
            width=10,
            takefocus=False,
        )
        contenido = tk.Frame(canvas, bg=self.palette["panel"], bd=0)

        # La scrollbar se reserva en column=1. El Canvas solamente usa
        # column=0, así que su viewport ya excluye físicamente la barra.
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        ventana_id = canvas.create_window((0, 0), window=contenido, anchor="nw")

        def _actualizar_scrollregion():
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        def _ajustar_textos(widget, ancho):
            # Label/Checkbutton/Radiobutton/Button admiten wraplength.
            # Esto cubre también textos de botones largos que antes podían
            # quedar cortados al reducir el ancho del contenido.
            wrap = max(80, int(ancho) - 10)
            for hijo in widget.winfo_children():
                if isinstance(hijo, (tk.Label, tk.Checkbutton, tk.Radiobutton, tk.Button)):
                    try:
                        hijo.config(wraplength=wrap)
                    except tk.TclError:
                        pass
                _ajustar_textos(hijo, ancho)

        def _escalar_horizontal(valor, factor=PANEL_HORIZONTAL_SCALE):
            """Reduce sólo espaciados/ancho horizontales; no toca altura."""
            if valor in (None, "", 0, "0"):
                return valor
            if isinstance(valor, (tuple, list)):
                return tuple(max(0, int(round(float(v) * factor))) for v in valor)
            texto = str(valor).strip()
            if " " in texto:
                partes = [p for p in texto.split() if p]
                try:
                    return tuple(max(0, int(round(float(v) * factor))) for v in partes)
                except ValueError:
                    return valor
            try:
                return max(0, int(round(float(valor) * factor)))
            except (TypeError, ValueError):
                return valor

        def _compactar_widget_horizontal(widget):
            """v24: compacta exclusivamente el ANCHO una sola vez.

            No se modifican font, height, pady ni ipady. Los controles con
            sticky=ew quedan más angostos porque el propio sidebar es ~30 %
            menor; los controles con width/length explícitos también se
            reducen al 70 %. Así la reducción es visible y no vertical.
            """
            if getattr(widget, "_panel_horizontal_v24", False):
                return
            widget._panel_horizontal_v24 = True

            # Sólo padding horizontal administrado por grid/pack.
            try:
                manager = widget.winfo_manager()
                if manager == "grid":
                    info = widget.grid_info()
                    cambios = {}
                    for clave in ("padx", "ipadx"):
                        if clave in info:
                            cambios[clave] = _escalar_horizontal(info[clave])
                    if cambios:
                        widget.grid_configure(**cambios)
                elif manager == "pack":
                    info = widget.pack_info()
                    cambios = {}
                    for clave in ("padx", "ipadx"):
                        if clave in info:
                            cambios[clave] = _escalar_horizontal(info[clave])
                    if cambios:
                        widget.pack_configure(**cambios)
            except (tk.TclError, ValueError, TypeError):
                pass

            # Sólo ancho explícito. La altura se conserva intacta.
            try:
                valor = float(widget.cget("width"))
                if valor > 1:
                    widget.configure(width=max(1, int(round(valor * PANEL_HORIZONTAL_SCALE))))
            except (tk.TclError, ValueError, TypeError):
                pass

            # En Scale, length es la dimensión horizontal principal.
            if isinstance(widget, tk.Scale):
                try:
                    valor = float(widget.cget("length"))
                    if valor > 5:
                        widget.configure(length=max(5, int(round(valor * PANEL_HORIZONTAL_SCALE))))
                except (tk.TclError, ValueError, TypeError):
                    pass

        def _compactar_arbol_horizontal(widget):
            for hijo in widget.winfo_children():
                _compactar_widget_horizontal(hijo)
                _compactar_arbol_horizontal(hijo)

        # La rueda se aplica solo a elementos que no tienen un comportamiento
        # de rueda propio. Entradas, escalas y Combobox quedan intactos; la
        # scrollbar sigue estando siempre visible para esos casos.
        _wheel_bound = set()

        def _on_mousewheel(event):
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            return "break"

        def _vincular_rueda(widget):
            for hijo in widget.winfo_children():
                # No interceptar la rueda de controles editables/interactivos.
                if not isinstance(hijo, (tk.Entry, tk.Scale, ttk.Combobox, tk.Listbox, tk.Text)):
                    key = str(hijo)
                    if key not in _wheel_bound:
                        hijo.bind("<MouseWheel>", _on_mousewheel, add="+")
                        hijo.bind("<Button-4>", _on_mousewheel, add="+")
                        hijo.bind("<Button-5>", _on_mousewheel, add="+")
                        _wheel_bound.add(key)
                _vincular_rueda(hijo)

        canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        canvas.bind("<Button-4>", _on_mousewheel, add="+")
        canvas.bind("<Button-5>", _on_mousewheel, add="+")
        contenido.bind("<MouseWheel>", _on_mousewheel, add="+")
        contenido.bind("<Button-4>", _on_mousewheel, add="+")
        contenido.bind("<Button-5>", _on_mousewheel, add="+")

        _vertical_sync_job = None

        def _sincronizar_alto_y_scroll():
            nonlocal _vertical_sync_job
            _vertical_sync_job = None
            alto = max(canvas.winfo_height(), contenido.winfo_reqheight())
            try:
                actual = float(canvas.itemcget(ventana_id, "height") or 0)
            except (TypeError, ValueError, tk.TclError):
                actual = 0
            if abs(actual - alto) > 1:
                canvas.itemconfig(ventana_id, height=alto)
            _actualizar_scrollregion()

        def _on_contenido_configure(_event):
            nonlocal _vertical_sync_job
            _compactar_arbol_horizontal(contenido)
            _vincular_rueda(contenido)
            # El wrap de textos puede aumentar el alto pedido DESPUÉS del
            # resize horizontal. Sin esta segunda sincronización, el Canvas
            # podía conservar el alto previo y recortar las últimas filas.
            if _vertical_sync_job is None:
                _vertical_sync_job = canvas.after_idle(_sincronizar_alto_y_scroll)

        contenido.bind("<Configure>", _on_contenido_configure, add="+")

        def _on_canvas_resize(event):
            # v24: contenido al 96 % del Canvas (~2 % de margen por lado).
            # La reducción horizontal no se logra con márgenes grandes, sino
            # con el sidebar y anchos explícitos más compactos.
            x, ancho = calcular_geometria_contenido_panel(
                event.width, PANEL_CONTENT_RATIO
            )
            canvas.coords(ventana_id, x, 0)
            canvas.itemconfig(ventana_id, width=ancho)

            # Si el contenido entra verticalmente, completar el alto visible;
            # si no, respetar su alto pedido para que la barra pueda recorrerlo.
            alto = max(event.height, contenido.winfo_reqheight())
            canvas.itemconfig(ventana_id, height=alto)
            _ajustar_textos(contenido, ancho)
            canvas.after_idle(_actualizar_scrollregion)

        canvas.bind("<Configure>", _on_canvas_resize, add="+")

        # Guardar referencias facilita depuración y mantiene viva la relación
        # explícita panel -> canvas -> scrollbar.
        if not hasattr(self, "panel_canvases"):
            self.panel_canvases = []
        if not hasattr(self, "panel_scrollbars"):
            self.panel_scrollbars = []
        self.panel_canvases.append(canvas)
        self.panel_scrollbars.append(scrollbar)

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

        GEOMETRÍA v22: los paneles internos usan .place(), por lo que no
        participan del cálculo de tamaño de grid. Configurar solamente
        ``frame1.width`` no alcanzaba: en una prueba 1400x900 frame1
        pedía 260 px pero la columna 0 recibía 218 px, y el borde derecho
        del panel quedaba recortado al comenzar frame2/frame4. Ahora la
        apertura reserva el ancho completo mediante ``minsize`` en la
        columna 0 antes de animar. close_panel devuelve esa reserva al
        ancho de la barra de íconos al terminar.
        """
        if not self.require_project("acceder a los paneles"):
            return
        token = self._panel_anim_token
        self.active_panel = index
        self.is_animating = True
        # BUG CORREGIDO ("los íconos no manejan bien el cambio de
        # paneles"): antes la barra de íconos se pasaba a horizontal
        # DESPUÉS de arrancar la animación y frame1 se agrandaba a
        # iconos+panel — pero grid ignora ese config(width) y el panel,
        # que crece al ancho que le pide su contenido (~400px), quedaba
        # superpuesto sobre el área de escena. Ahora: íconos
        # horizontales primero, frame1 = ancho del panel, y la
        # animación fuerza el ancho exacto del panel (place width).
        self.switch_buttons_to_horizontal()
        self._recalcular_ancho_sidebar_abierto()
        self._reservar_ancho_sidebar(self.panel_width)
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

        ANCHO: place() lleva width= explícito en cada paso, así el
        panel mide EXACTAMENTE self.panel_width (antes, sin width,
        place usaba el ancho pedido por el contenido y el panel quedaba
        superpuesto al área de escena). button_height se toma con
        winfo_reqheight() para no depender de si los íconos ya se
        redibujaron en horizontal.

        Cada paso se encola vía _panel_anim_step (comando Tcl
        persistente — ver __init__) en vez de re-registrar callables
        con widget.after(), que colisionaba por reuso de id().
        """
        self._panel_anim_step("open", index, current_width, token)

    def _panel_anim_step(self, op, index, width, token):
        """Un único handler Tcl persistente para los pasos de las
        animaciones de panel (op = "open" | "close"). Se registró UNA
        vez en __init__ (_anim_cmd); cada paso se encola con
        tk.call("after", 10, _anim_cmd, ...) sobre ese nombre estable.

        Recibe los argumentos como strings (los pasa Tcl) — acá se
        convierten. Primero se valida el token: si la animación que
        encoló este paso ya no es la actual, el paso se descarta sin
        re-encolar (así las corridas viejas se abortan solas)."""
        index = int(index)
        width = int(width)
        token = int(token)
        if token != self._panel_anim_token:
            return
        button_height = max(self.buttons[0].winfo_reqheight(), 30)
        outer = self.panel_outer_frames[index]
        if op == "open":
            if width < self.panel_width:
                outer.config(width=width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=width,
                )
                self.root.tk.call("after", 10, self._anim_cmd, "open", index, width + 10, token)
            else:
                outer.config(width=self.panel_width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=self.panel_width,
                )
                self.is_animating = False
        else:
            if width > 0:
                outer.config(width=width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=width,
                )
                self.root.tk.call("after", 10, self._anim_cmd, "close", index, width - 10, token)
            else:
                outer.place_forget()
                if self._open_after_close.get(index) == token:
                    del self._open_after_close[index]
                    callback = self._close_callbacks.pop(index, None)
                    if callback is not None:
                        callback()
                    else:
                        self.open_panel(index)
                else:
                    icon_width = max(self.sidebar_closed_width, self.icon_frame.winfo_reqwidth(), 40)
                    self._reservar_ancho_sidebar(icon_width)
                    self.is_animating = False

    def close_panel(self, index, on_complete=None):
        """Cierra el panel 'index'. Si se pasa on_complete, se llama
        recién cuando la animación de cierre TERMINÓ de verdad — así
        se encadena una apertura sin adivinar tiempos (ver toggle_panel).

        BUG CORREGIDO: cuando el cierre va encadenado a una apertura
        (on_complete != None) ya no se vuelve a vertical la barra de
        íconos — antes la volteaba y al toque open_panel la volvía
        horizontal, y el panel saltaba de lugar durante el cambio."""
        token = self._panel_anim_token
        self.is_animating = True
        self.animate_panel_close(index, self.panel_width, token, on_complete)
        self.reset_button(index)
        if on_complete is None:
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

        Igual que animate_panel_open: width explícito en place() y
        button_height con winfo_reqheight() (ver docstring de open).
        Los pasos se encolan vía _panel_anim_step (comando Tcl
        persistente). Si viene on_complete, se guarda el token en
        self._open_after_close (y el callback en _close_callbacks) y
        _panel_anim_step recién encadena la apertura cuando el cierre
        terminó de verdad.
        """
        if on_complete is not None:
            self._open_after_close[index] = token
            self._close_callbacks[index] = on_complete
        self._panel_anim_step("close", index, current_width, token)

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
            [self.frame2, self.frame3, self.frame4, self.frame5, self.frame15],
            [self.frame7, self.frame8, self.frame9, self.frame10, self.frame11, self.frame12, self.frame13, self.frame14],
        )
    def show_diseno_frames(self):
        # v30: un único host ocupa las cuatro celdas centrales. Esto evita
        # tres cuartos vacíos alrededor del gráfico 2D/3D y permite que el
        # Notebook de Edición use todo el viewport disponible.
        self._toggle_frames(
            [self.frame7],
            [self.frame2, self.frame3, self.frame4, self.frame5,
             self.frame8, self.frame9, self.frame10,
             self.frame11, self.frame12, self.frame13, self.frame14, self.frame15],
        )
    def show_modelo_frames(self):
        # v30: mismo criterio para Modelo. frame11 tiene rowspan=2 y
        # columnspan=2, por lo que ocupa el bloque frame2..frame5 completo.
        self._toggle_frames(
            [self.frame11],
            [self.frame2, self.frame3, self.frame4, self.frame5,
             self.frame7, self.frame8, self.frame9, self.frame10,
             self.frame12, self.frame13, self.frame14, self.frame15],
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
            # Cerrar explícitamente el período de proyecto antes de destruir
            # la ventana. MainApp cerrará después la sesión completa.
            if self.db_manager is not None and self.session_id:
                try:
                    self.db_manager.end_project_work(self.session_id)
                except Exception as exc:
                    print(f"[sesion] No se pudo cerrar proyecto activo: {exc}")
            try:
                self.root.destroy()
            finally:
                if not self._session_exit_notified and callable(self.on_session_exit):
                    self._session_exit_notified = True
                    self.on_session_exit()

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
        prepare_dialog(preferences, self.root, modal=False, resizable=False)
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
        tmrt_model_var = tk.StringVar(value=self.settings.get("tmrt_model_mode", "standard"))
        surface_model_var = tk.StringVar(value=self.settings.get("surface_model_mode", "standard"))
        ground_veg_var = tk.StringVar(value=str(self.settings.get("ground_vegetation_fraction", 0.50)))
        water_var = tk.StringVar(value=str(self.settings.get("vegetation_water_availability", 0.75)))
        canopy_water_var = tk.StringVar(value=str(self.settings.get("canopy_water_availability", 0.75)))

        header = ttk.Frame(preferences, padding=(18, 16, 18, 0))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Preferencias", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header, text="Configuración general de interfaz, unidades y modelos.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        card = tk.Frame(preferences, bg="white", padx=18, pady=14, bd=0, relief="flat")
        card.grid(row=1, column=0, padx=18, pady=(8, 16))

        tk.Label(card, text="Unidades", bg="white", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(card, textvariable=temp_unit_var, values=["C", "F", "K"], state="readonly", width=10).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Combobox(
            card, textvariable=distance_unit_var,
            values=["cm", "m", "km", "in", "ft", "yd", "mi"],
            state="readonly", width=10,
        ).grid(row=1, column=1, sticky="w")

        tk.Label(card, text="Modo de interfaz", bg="white", font=("Arial", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(card, text="Simple", variable=ui_mode_var, value="simple", bg="white").grid(
            row=3, column=0, sticky="w"
        )
        tk.Radiobutton(card, text="Detallado", variable=ui_mode_var, value="advanced", bg="white").grid(
            row=3, column=1, sticky="w"
        )

        tk.Label(card, text="Modelo térmico Tmrt", bg="white", font=("Arial", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(
            card, text="Estándar (empírico, predeterminado)",
            variable=tmrt_model_var, value="standard", bg="white",
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado (balance radiativo v1)",
            variable=tmrt_model_var, value="advanced", bg="white",
        ).grid(row=6, column=0, columnspan=2, sticky="w")
        tk.Label(
            card,
            text=("El modelo avanzado usa GHI, DNI y DHI por separado y parámetros "
                  "radiativos humanos. Es más físico, pero todavía requiere validación local."),
            bg="white", fg="#666666", wraplength=380, justify="left", font=("Arial", 7),
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(card, text="Modelo térmico de superficies", bg="white", font=("Arial", 9, "bold")).grid(
            row=8, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(
            card, text="Estándar (linealizado, predeterminado)",
            variable=surface_model_var, value="standard", bg="white",
        ).grid(row=9, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado seco (balance energético v1)",
            variable=surface_model_var, value="advanced", bg="white",
        ).grid(row=10, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado vegetación + ET (v2)",
            variable=surface_model_var, value="advanced_vegetation", bg="white",
        ).grid(row=11, column=0, columnspan=2, sticky="w")
        tk.Label(
            card,
            text=("v2 añade evapotranspiración de suelo vegetado mediante FAO-56 Penman-Monteith, "
                  "fenología de caducifolias y diagnóstico separado de transpiración de copa. "
                  "El estándar y el avanzado seco conservan sus resultados anteriores."),
            bg="white", fg="#666666", wraplength=380, justify="left", font=("Arial", 7),
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(card, text="Fracción de suelo vegetado (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=13, column=0, sticky="w", pady=(6, 0)
        )
        tk.Entry(card, textvariable=ground_veg_var, width=10).grid(row=13, column=1, sticky="w")
        tk.Label(card, text="Disponibilidad hídrica suelo (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=14, column=0, sticky="w"
        )
        tk.Entry(card, textvariable=water_var, width=10).grid(row=14, column=1, sticky="w")
        tk.Label(card, text="Disponibilidad hídrica copa (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=15, column=0, sticky="w"
        )
        tk.Entry(card, textvariable=canopy_water_var, width=10).grid(row=15, column=1, sticky="w")

        tk.Label(card, text="País por defecto", bg="white", font=("Arial", 9, "bold")).grid(
            row=16, column=0, sticky="w", pady=(10, 0)
        )
        if self.locations_data:
            country_combo = ttk.Combobox(
                card, textvariable=country_var, values=self.locations_data["countries"], width=22
            )
            country_combo.grid(row=17, column=0, columnspan=2, sticky="w")
        else:
            tk.Entry(card, textvariable=country_var, width=24).grid(row=17, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Ciudad por defecto", bg="white", font=("Arial", 9, "bold")).grid(
            row=18, column=0, sticky="w", pady=(10, 0)
        )
        if self.locations_data:
            city_combo = ttk.Combobox(card, textvariable=city_var, width=22)
            city_combo.grid(row=19, column=0, columnspan=2, sticky="w")
            if country_var.get() in self.locations_data["cities"]:
                city_combo["values"] = self.locations_data["cities"][country_var.get()]

            def update_city_options(*_args):
                cities = self.locations_data["cities"].get(country_var.get(), [])
                city_combo["values"] = cities
                if cities and city_var.get() not in cities:
                    city_var.set(cities[0])

            country_combo.bind("<<ComboboxSelected>>", update_city_options)
        else:
            tk.Entry(card, textvariable=city_var, width=24).grid(row=19, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Nubosidad", bg="white", font=("Arial", 9, "bold")).grid(
            row=20, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Combobox(
            card, textvariable=cloudiness_var, values=["Despejado", "Parcial", "Nublado"], width=22
        ).grid(row=21, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Viento", bg="white", font=("Arial", 9, "bold")).grid(
            row=22, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Combobox(
            card, textvariable=wind_var, values=["nulo", "moderado", "fuerte"], width=22
        ).grid(row=23, column=0, columnspan=2, sticky="w")

        def save_preferences():
            try:
                ground_veg = float(ground_veg_var.get().replace(",", "."))
                water = float(water_var.get().replace(",", "."))
                canopy_water = float(canopy_water_var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Vegetación", "Las fracciones de vegetación/agua deben ser numéricas.", parent=preferences)
                return
            if not all(0.0 <= v <= 1.0 for v in (ground_veg, water, canopy_water)):
                messagebox.showerror("Vegetación", "Las fracciones de vegetación/agua deben estar entre 0 y 1.", parent=preferences)
                return
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
                    "tmrt_model_mode": tmrt_model_var.get(),
                    "surface_model_mode": surface_model_var.get(),
                    "ground_vegetation_fraction": ground_veg,
                    "vegetation_water_availability": water,
                    "canopy_water_availability": canopy_water,
                }
            )
            self.settings_manager.write(self.settings)
            self.apply_settings(self.settings)
            preferences.destroy()

        actions = tk.Frame(card, bg="white")
        actions.grid(row=24, column=0, columnspan=2, pady=(12, 0), sticky="e")
        tk.Button(actions, text="Guardar", command=save_preferences).grid(row=0, column=0, padx=(0, 8))
        tk.Button(actions, text="Cancelar", command=preferences.destroy).grid(row=0, column=1)

    def _confirm_discard_changes(self, action_label):
        """Vacía primero el autosave; solo pregunta si el guardado falla."""
        if not self.is_dirty:
            return True
        manager = getattr(self, "project_manager", None)
        if manager is not None and getattr(manager, "current_project", None) is not None:
            try:
                if manager.autosave_project():
                    return True
            except Exception as exc:
                print(f"[autosave] No se pudo guardar antes de {action_label}: {exc}")
        response = messagebox.askyesnocancel(
            "Cambios sin guardar",
            f"{action_label}: el guardado automático no pudo completarse. ¿Desea reintentar?",
        )
        if response is None:
            return False
        if response:
            return bool(self.save_project())
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
        self.tmrt_model_mode.set(self.settings.get("tmrt_model_mode", "standard"))
        self.surface_model_mode.set(self.settings.get("surface_model_mode", "standard"))
        self.matriz_size.set(DEFAULT_MATRIX_SIZE)        
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
        if frame is self.frame7:
            self._cleanup_scene_view_host("diseno")
        elif frame is self.frame11:
            self._cleanup_scene_view_host("modelo")
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
            self.last_model_excel_path = self._copy_excel_to_project(filepath, "modelos")
            # El archivo nuevo contiene también los parámetros del cálculo.
            # Regeneramos inmediatamente para que cargar el Excel signifique
            # realmente reproducir la escena guardada, sin exigir tocar otro
            # control ni dejar una gráfica anterior en pantalla.
            try:
                self.vars_modelo["_update_required"] = True
                self.generar_grafico_modelo()
            except Exception as exc:
                messagebox.showwarning(
                    "Modelo",
                    f"Los datos se cargaron, pero no se pudo regenerar el gráfico automáticamente:\n{exc}",
                )
            self.mark_dirty()

    def guardar_excel_modelo(self):
        """Guarda Modelo directamente en escena/modelo.xlsx, sin preguntar."""
        if not self.require_project("guardar Excel de modelo"):
            return
        project = self.project_manager.current_project
        target = project.layout.model_excel
        saved = modelo.guardar_excel(self.vars_modelo, filepath=target, app=self)
        if saved:
            self.last_model_excel_path = saved
            self.mark_dirty()

    def open_execution_dialog(self):
        """Abre el selector de ejecución puntual / secuencia diurna.

        La animación es cuasi-estacionaria: cada cuadro utiliza exactamente
        el modelo científico actual en una hora distinta y se almacena antes
        de reproducir. La reproducción no recalcula física.
        """
        if not self.require_project("ejecutar el modelo"):
            return
        if self.active_panel not in (2, 3):
            self.run_model_for_active_panel()
            return

        dlg = tk.Toplevel(self.root)
        prepare_dialog(dlg, self.root, modal=True, resizable=False)
        dlg.title("Ejecutar simulación")

        body = ttk.Frame(dlg, padding=(18, 16, 18, 16))
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text="Ejecutar simulación", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            body,
            text="Elegí entre un cálculo puntual o una secuencia diurna de sombra y temperatura.",
            style="Muted.TLabel",
            wraplength=410,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 14))

        mode = tk.StringVar(value="animation")
        ttk.Label(body, text="Tipo de ejecución", style="DialogSection.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        ttk.Radiobutton(body, text="Instantánea", variable=mode, value="instant").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Radiobutton(
            body, text="Animación diurna (sombra + temperatura)",
            variable=mode, value="animation",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 12))

        start_var = tk.DoubleVar(value=8.0)
        end_var = tk.DoubleVar(value=18.0)
        step_var = tk.IntVar(value=60)
        speed_var = tk.IntVar(value=500)

        ttk.Label(body, text="Hora inicial:").grid(row=5, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Spinbox(body, from_=0, to=23.75, increment=0.25, textvariable=start_var, width=12).grid(
            row=5, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="Hora final:").grid(row=6, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Spinbox(body, from_=0.25, to=24, increment=0.25, textvariable=end_var, width=12).grid(
            row=6, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="Paso temporal:").grid(row=7, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Combobox(body, textvariable=step_var, values=(15, 30, 60), state="readonly", width=12).grid(
            row=7, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="Velocidad reproducción:").grid(row=8, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Combobox(body, textvariable=speed_var, values=(1000, 750, 500, 300, 150), state="readonly", width=12).grid(
            row=8, column=1, sticky="ew", pady=6)
        ttk.Label(
            body,
            text=("Cada fotograma se calcula primero y luego se reproduce desde memoria. "
                  "Es una secuencia cuasi-estacionaria: no incorpora inercia térmica temporal entre cuadros."),
            style="Muted.TLabel", justify="left", wraplength=410,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))

        def execute():
            selected = mode.get()
            if selected == "instant":
                dlg.destroy()
                self.run_model_for_active_panel()
                return
            try:
                start = float(start_var.get())
                end = float(end_var.get())
                step = int(step_var.get())
                speed = int(speed_var.get())
            except (TypeError, ValueError):
                messagebox.showerror("Animación", "Revise las horas, el paso y la velocidad.", parent=dlg)
                return
            if not (0.0 <= start < 24.0) or not (0.0 < end <= 24.0) or end <= start:
                messagebox.showerror("Animación", "La hora final debe ser mayor que la inicial y ambas deben estar entre 0 y 24.", parent=dlg)
                return
            if step not in (15, 30, 60):
                messagebox.showerror("Animación", "El paso debe ser 15, 30 o 60 minutos.", parent=dlg)
                return
            count = int(round((end - start) * 60.0 / step)) + 1
            if count > 97:
                messagebox.showerror("Animación", "La secuencia solicitada es demasiado larga.", parent=dlg)
                return
            dlg.destroy()
            self._start_diurnal_animation(start, end, step, speed)

        ttk.Button(buttons, text="Cancelar", command=dlg.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Ejecutar", command=execute, style="DialogSuccess.TButton").pack(side="left")
        dlg.bind("<Return>", lambda _e: execute())
        dlg.wait_visibility()
        dlg.focus_set()

    @staticmethod
    def _snapshot_tk_mapping(mapping):
        snapshot = {}
        for key, value in mapping.items():
            if isinstance(value, tk.Variable):
                try:
                    snapshot[key] = ("tk", value.get())
                except tk.TclError:
                    pass
            elif key.startswith("_") and key not in {"_app_instance", "_current_fig"}:
                # Metadatos transitorios que las fuentes meteorológicas pueden cambiar.
                if isinstance(value, (str, int, float, bool, type(None))):
                    snapshot[key] = ("plain", value)
        return snapshot

    @staticmethod
    def _restore_tk_mapping(mapping, snapshot):
        for key, (kind, value) in snapshot.items():
            if kind == "tk" and key in mapping and isinstance(mapping[key], tk.Variable):
                try:
                    mapping[key].set(value)
                except tk.TclError:
                    pass
            elif kind == "plain":
                mapping[key] = value

    def _capture_diurnal_frame(self, mapping, hour, shadow, meta=None):
        X = np.asarray(mapping.get("X"), dtype=np.float32).copy()
        Y = np.asarray(mapping.get("Y"), dtype=np.float32).copy()
        T = np.asarray(mapping.get("T"), dtype=np.float32).copy()
        T_display = np.asarray(self.convert_temperature_for_display(T), dtype=np.float32)
        return {
            "hour": float(hour),
            "X": X,
            "Y": Y,
            "T": T,
            "T_display": T_display,
            "shadow": np.asarray(shadow, dtype=np.float32).copy(),
            "solar_altitude_deg": float(mapping.get("_render_solar_altitude_deg", 0.0)),
            "solar_azimuth_deg": float(mapping.get("_render_solar_azimuth_deg", 0.0)),
            "temp_unit": self.get_temperature_unit_symbol(),
            "trees": tuple(mapping.get("arboles", ()) or ()),
            "structures": tuple(mapping.get("estructuras", ()) or ()),
            "meta": dict(meta or {}),
        }

    def _start_diurnal_animation(self, start_hour, end_hour, step_minutes, speed_ms):
        """Calcula la secuencia de a un cuadro por ciclo Tk y luego la reproduce."""
        if self.active_panel not in (2, 3):
            messagebox.showinfo("Animación", "Abra Edición o Modelo para generar una secuencia diurna.")
            return
        mode = "diseno" if self.active_panel == 2 else "modelo"
        mapping = self.vars if mode == "diseno" else self.vars_modelo

        # En Modelo sincronizamos primero los controles visibles con vars_modelo.
        if mode == "modelo":
            self.generar_grafico_modelo()

        snapshot = self._snapshot_tk_mapping(mapping)
        previous_suspend = getattr(self, "_suspend_autosave_tracking", False)
        self._suspend_autosave_tracking = True

        total_minutes = int(round((float(end_hour) - float(start_hour)) * 60.0))
        offsets = list(range(0, total_minutes + 1, int(step_minutes)))
        if offsets[-1] != total_minutes:
            offsets.append(total_minutes)
        hours = [float(start_hour) + value / 60.0 for value in offsets]
        frames = []

        progress = tk.Toplevel(self.root)
        prepare_dialog(progress, self.root, modal=True, resizable=False)
        progress.title("Calculando secuencia diurna")
        progress.transient(self.root)
        progress.resizable(False, False)
        tk.Label(progress, text="Calculando sombras y temperaturas…", padx=18).pack(pady=(14, 5))
        progress_var = tk.DoubleVar(value=0.0)
        bar = ttk.Progressbar(progress, variable=progress_var, maximum=len(hours), length=360)
        bar.pack(padx=18, pady=5)
        status = tk.Label(progress, text="", padx=18)
        status.pack(pady=(3, 12))
        cancelled = {"value": False}
        tk.Button(progress, text="Cancelar", command=lambda: cancelled.__setitem__("value", True)).pack(pady=(0, 12))
        progress.grab_set()

        def finish(success=True, error=None):
            try:
                self._restore_tk_mapping(mapping, snapshot)
            finally:
                self._suspend_autosave_tracking = previous_suspend
            try:
                progress.grab_release()
                progress.destroy()
            except tk.TclError:
                pass
            if not success:
                if error is not None:
                    messagebox.showerror("Animación", f"No se pudo completar la secuencia:\n{error}")
                return
            if not frames:
                messagebox.showinfo("Animación", "No se generaron fotogramas válidos.")
                return
            view2d, view3d, notebook = self._get_scene_view_frames(mode)
            old_player = getattr(view2d, "_sombra_diurnal_player", None)
            if old_player is not None:
                try:
                    old_player.close()
                except Exception:
                    pass
            old_player3d = getattr(view3d, "_sombra_diurnal_3d_player", None)
            if old_player3d is not None:
                try:
                    old_player3d.close()
                except Exception:
                    pass
            title = "Edición · evolución diurna" if mode == "diseno" else "Modelo · evolución diurna"
            player2d = DiurnalAnimationPlayer(view2d, frames, self, title=title)
            player2d.speed_ms.set(int(speed_ms))
            player3d = Diurnal3DAnimationPlayer(view3d, frames, self, title=title)
            player3d.speed_ms.set(int(speed_ms))
            self.diurnal_animation_frames = frames
            self.diurnal_animation_mode = mode
            self.diurnal_animation_player_2d = player2d
            self.diurnal_animation_player_3d = player3d
            # La animación pedida se abre en 3D: un único viewport persistente.
            notebook.select(view3d)
            player3d.play()

        def compute_one(index=0):
            if cancelled["value"]:
                finish(False)
                return
            if index >= len(hours):
                finish(True)
                return
            hour = hours[index]
            try:
                mapping["hora"].set(hour)
                if mode == "modelo":
                    self.generar_grafico_modelo()
                    shadow = self.last_shadow
                    meta = self.last_meta or {}
                else:
                    # Forzar regeneración porque actualizar_grafico marca False al terminar.
                    mapping["_update_required"] = True
                    self.actualizar_grafico_diseno(self.frame7)
                    shadow = mapping.get("_last_shadow")
                    meta = mapping.get("_last_meta", {})
                if shadow is None:
                    raise RuntimeError("El modelo no devolvió la matriz de sombra del fotograma.")
                frames.append(self._capture_diurnal_frame(mapping, hour, shadow, meta))
                progress_var.set(index + 1)
                hh = int(hour) % 24
                mm = int(round((hour - int(hour)) * 60)) % 60
                status.configure(text=f"{index + 1}/{len(hours)} · {hh:02d}:{mm:02d}")
            except Exception as exc:
                finish(False, exc)
                return
            self.root.after(1, lambda: compute_one(index + 1))

        self.root.after(1, compute_one)

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
        cobertura de sombra, atenuación y ΔTmrt lado a lado, más estadística descriptiva.
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
        analisis_dir = project.layout.project_results_dir
        os.makedirs(analisis_dir, exist_ok=True)
        chart_path = project.layout.comparison_chart
        resultado = analysis_service.grafico_comparativo(self.snapshots, str(chart_path))
        if resultado is None:
            messagebox.showinfo(
                "Análisis comparativo",
                "Ningún elemento guardado tiene cobertura de sombra calculada todavía.",
            )
            return
        self.last_comparative_chart_path = str(chart_path)
        # La tabla consolidada forma parte del resultado del análisis y se
        # actualiza automáticamente; el botón visible queda como respaldo manual.
        try:
            analysis_service.exportar_tabla_excel(self.snapshots, str(project.layout.elements_excel))
        except Exception as exc:
            print(f"[autosave] No se pudo actualizar elementos_proyecto.xlsx: {exc}")
        self.mark_dirty()

        ventana = tk.Toplevel(self.root)
        prepare_dialog(ventana, self.root, modal=False, resizable=True, minsize=(640, 560))
        ventana.title("Análisis comparativo del proyecto")
        ventana.geometry("720x950")

        s = resumen["cobertura_sombra"]
        a = resumen["atenuacion_sombra"]
        d = resumen["delta_tmrt"]
        lineas = [f"Elementos analizados: {resumen['n_elementos']}"]
        if s["n"]:
            lineas.append(
                f"Cobertura de sombra — media {s['media']:.1f}% · mín {s['min']:.1f}% · "
                f"máx {s['max']:.1f}% · σ {s['desvio']:.1f}%"
            )
        if a["n"]:
            lineas.append(
                f"Atenuación en sombra — media {a['media']:.1f}% · mín {a['min']:.1f}% · "
                f"máx {a['max']:.1f}% · σ {a['desvio']:.1f}%"
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

        # Dispersión entre cobertura fotográfica y ΔTmrt modelada. No se
        # denomina "dato real": ambas magnitudes son derivadas/modeladas.
        scatter_path = project.layout.scatter_chart
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
                text="(Se necesitan al menos 2 elementos con cobertura de sombra y ΔTmrt "
                     "para la dispersión)",
                fg="#888888",
            ).pack(pady=5)

        tk.Button(
            ventana, text="Respaldar tabla Excel",
            command=lambda: self._exportar_tabla_elementos_excel(analisis_dir),
        ).pack(pady=(4, 12))

    def _exportar_tabla_elementos_excel(self, analisis_dir: str):
        """Actualiza la tabla consolidada en resultados/proyecto/."""
        if not self.snapshots:
            messagebox.showinfo("Exportar tabla", "No hay elementos para exportar.")
            return
        chart_path = self.project_manager.current_project.layout.elements_excel
        try:
            resultado = analysis_service.exportar_tabla_excel(self.snapshots, str(chart_path))
            self.last_elements_excel_path = str(resultado)
            self.mark_dirty()
        except Exception as exc:
            messagebox.showerror("Exportar tabla", f"No se pudo exportar: {exc}")
            return
        messagebox.showinfo("Exportar tabla", f"Tabla exportada a:\n{resultado}")

    def mostrar_curva_sensibilidad(self):
        """Grafica cómo responde el Tmrt a la cobertura de sombra
        (0-100%) según el propio modelo, con la ubicación/fecha/hora/
        temperatura actuales del Panel 1. Herramienta pura de
        exploración del modelo — no requiere ninguna imagen."""
        if not self.require_project("generar curva de sensibilidad"):
            return
        temp_ambient, hora, fecha, lat, lon = self._leer_parametros_tmrt()
        calculador = Temperatura(
            lat, lon, k_factor=self.k_factor, model_mode=self.tmrt_model_mode.get()
        )

        project = self.project_manager.current_project
        analisis_dir = project.layout.project_results_dir
        os.makedirs(analisis_dir, exist_ok=True)
        chart_path = project.layout.sensitivity_chart
        resultado_path, _, _ = analysis_service.curva_sensibilidad(
            calculador, temp_ambient, fecha, hora, str(chart_path),
        )
        self.last_sensitivity_chart_path = str(resultado_path)
        self.mark_dirty()

        ventana = tk.Toplevel(self.root)
        prepare_dialog(ventana, self.root, modal=False, resizable=True, minsize=(560, 480))
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
        Se guarda directamente en resultados/informes/ del proyecto
        (sin diálogo de guardado) para que quede siempre junto con el
        resto de los resultados del proyecto."""
        if not self.require_project("generar el informe completo"):
            return
        project = self.project_manager.current_project
        analisis_dir = project.layout.reports_dir
        os.makedirs(analisis_dir, exist_ok=True)
        destino = project.layout.full_report
        try:
            ruta_final = report_service.generar_informe_proyecto(self, project, destino)
            self.last_report_path = str(ruta_final)
            self.mark_dirty()
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
        # Los botones de la banda usan toggle_panel (igual que los
        # íconos laterales), no open_panel: si ya hay un panel abierto,
        # open_panel directo lo dejaba abierto y desincronizaba el
        # estado (dos paneles mapeados a la vez, active_panel apuntando
        # al último) — BUG CORREGIDO en v3.1.1.
        _boton(grupo_escena, self.images[0], "Temp.", lambda: self.toggle_panel(0))
        _boton(grupo_escena, self.images[1], "Sombra", lambda: self.toggle_panel(1))
        _boton(grupo_escena, self.images[2], "Edición", lambda: self.toggle_panel(2))
        _boton(grupo_escena, self.images[3], "Modelo", lambda: self.toggle_panel(3))
        _separador()

        grupo_modelo = _grupo("Modelo")
        _boton(grupo_modelo, icon_factory.obtener_icono("play"), "Ejecutar", self.open_execution_dialog)
        _separador()

        grupo_analisis = _grupo("Análisis")
        _boton(grupo_analisis, icon_factory.obtener_icono("barras"), "Comparar", self.mostrar_analisis_comparativo)
        _boton(grupo_analisis, icon_factory.obtener_icono("curva"), "Sensib.", self.mostrar_curva_sensibilidad)
        _boton(grupo_analisis, icon_factory.obtener_icono("calibrar"), "Calibrar", self._dialogo_calibrar_k_factor)
        _boton(grupo_analisis, icon_factory.obtener_icono("confort"), "Confort", self._dialogo_confort)
        _boton(grupo_analisis, icon_factory.obtener_icono("arbol"), "Ranking", self._dialogo_ranking_arboles)
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
        """Configura el área de resultados (sección fija del Panel 2)."""
        result_frame = self.create_card(frame)
        result_frame.config(padx=8, pady=6)
        result_frame.pack(expand=True, fill='both', pady=5)

        sombra_frame = tk.Frame(result_frame, bg=self.palette["panel"])
        # Cambiamos a fill='x' para que el contenedor use todo el ancho disponible
        sombra_frame.pack(side=tk.TOP, fill='x', padx=12, pady=2)

        # (Opcional) Configurar las columnas para que se repartan el espacio 50% y 50%
        sombra_frame.columnconfigure(0, weight=1)
        sombra_frame.columnconfigure(1, weight=1)

        self.lbl_dimensiones_calculo = tk.Label(
            sombra_frame,
            text="Área de Cálculo: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        # Fila 0, Columna 0
        self.lbl_dimensiones_calculo.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        self.lbl_dimensiones_referencia = tk.Label(
            sombra_frame,
            text="Área de Referencia: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        # Fila 0, Columna 1
        self.lbl_dimensiones_referencia.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        self.lbl_promedio_referencia = tk.Label(
            sombra_frame,
            text="Promedio Gris Referencia: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        # Fila 1, Columna 0
        self.lbl_promedio_referencia.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        self.lbl_porcentaje_sombra = tk.Label(
            sombra_frame,
            text="Cobertura de sombra: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        # Fila 1, Columna 1
        self.lbl_porcentaje_sombra.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        self.lbl_atenuacion_sombra = tk.Label(
            sombra_frame,
            text="Atenuación en sombra: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_atenuacion_sombra.grid(row=2, column=0, sticky="w", padx=5, pady=2)

        self.lbl_transmitancia_sombra = tk.Label(
            sombra_frame,
            text="Transmitancia efectiva: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_transmitancia_sombra.grid(row=2, column=1, sticky="w", padx=5, pady=2)

    def carrusel(self, frame):
        """Carrusel de elementos analizados — ÁREA PROPIA del Panel 2
        (fila fija debajo de las 4 secciones; no modifica sus tamaños).

        Muestra una miniatura de la FOTO de cada árbol/elemento
        analizado (se agrega al generarse el histograma, vía
        self.snapshots). Un click en una miniatura recarga la foto, las
        áreas dibujadas de sombra y referencia, sus cálculos (% sombra
        y Tmrt) y el histograma.
        """
        result_frame = self.create_card(frame)
        result_frame.pack(fill="both", expand=True)

        strip = tk.Frame(result_frame, bg=self.palette["panel"])
        strip.pack(fill="both", expand=True, padx=6, pady=6)
        self.carrusel_izq = tk.Button(
            strip, text="◀", bd=0, bg=self.palette["panel"], fg="#2c3e50",
            font=("Arial", 10, "bold"), command=lambda: self._carrusel_desplazar(-1),
        )
        self.carrusel_izq.pack(side="left", fill="y")
        self.carrusel_canvas = tk.Canvas(
            strip, height=58, bg=self.palette["panel"], highlightthickness=0,
        )
        self.carrusel_canvas.pack(side="left", fill="both", expand=True)
        self.carrusel_der = tk.Button(
            strip, text="▶", bd=0, bg=self.palette["panel"], fg="#2c3e50",
            font=("Arial", 10, "bold"), command=lambda: self._carrusel_desplazar(1),
        )
        self.carrusel_der.pack(side="right", fill="y")
        self.carrusel_inner = tk.Frame(self.carrusel_canvas, bg=self.palette["panel"])
        self._carrusel_inner_win = self.carrusel_canvas.create_window(
            (0, 0), window=self.carrusel_inner, anchor="nw")
        self.carrusel_inner.bind(
            "<Configure>",
            lambda _e: self.carrusel_canvas.configure(
                scrollregion=self.carrusel_canvas.bbox("all")))
        self._carrusel_photos = []
        self._carrusel_frames = []
        self._carrusel_sel = None
        self.poblar_lista_snapshots()

    def _carrusel_actualizar(self, selected_analysis_id=None):
        """(Re)construye las miniaturas del carrusel desde los snapshots
        que ya tienen imagen cargada (la FOTO del elemento, no el
        histograma)."""
        if not hasattr(self, "carrusel_inner"):
            return
        for widget in self.carrusel_inner.winfo_children():
            widget.destroy()
        # Conservar la selección lógica aunque se reconstruyan los widgets.
        if selected_analysis_id is None and self._carrusel_sel is not None:
            try:
                selected_analysis_id = self.snapshots[self._carrusel_sel].get("analysis_id")
            except Exception:
                selected_analysis_id = None
        self._carrusel_photos = []
        self._carrusel_frames = []
        self._carrusel_sel = None
        project = self.project_manager.current_project
        root_path = project.root_path if project else None
        for idx, entry in enumerate(self.snapshots):
            img = entry.get("image")
            if not img:
                continue
            path = img if os.path.isabs(img) else (
                os.path.join(root_path, img) if root_path else None)
            if not path or not os.path.exists(path):
                continue
            try:
                with Image.open(path) as img:
                    ancho, alto = img.size
                    alto_t = 50
                    ancho_t = max(1, int(ancho * alto_t / alto))
                    thumb = img.resize((ancho_t, alto_t), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb)
                    thumb.close()
            except Exception:
                continue
            self._carrusel_photos.append(photo)
            marco = tk.Frame(
                self.carrusel_inner, bg=self.palette["panel"],
                highlightbackground=self.palette["border"],
                highlightthickness=1, bd=0,
            )
            marco.pack(side="left", padx=3)
            # v21: el carrusel es puramente visual. La miniatura identifica
            # el análisis y el borde azul marca la selección; se eliminan
            # nombres/% debajo de las fotos para ganar altura y evitar
            # recortes cuando hay muchos elementos.
            lbl_img = tk.Label(marco, image=photo, bg=self.palette["panel"], cursor="hand2")
            lbl_img.pack(padx=2, pady=2)
            lbl_img.bind("<Button-1>", lambda _e, i=idx: self._carrusel_seleccionar(i))
            self._carrusel_frames.append((marco, idx))
        if self._carrusel_frames:
            target = None
            if selected_analysis_id:
                for idx, entry in enumerate(self.snapshots):
                    if entry.get("analysis_id") == selected_analysis_id:
                        target = idx
                        break
            if target is None:
                target = len(self.snapshots) - 1
            self._carrusel_marcar(target)

    def _carrusel_marcar(self, index):
        """Resalta la miniatura del elemento cargado."""
        if not hasattr(self, "_carrusel_frames"):
            return
        for marco, idx in self._carrusel_frames:
            if idx == index:
                marco.config(relief="raised", highlightthickness=2,
                             highlightbackground="#2196F3")
                self._carrusel_sel = index
            else:
                marco.config(relief="flat", highlightthickness=1,
                             highlightbackground=self.palette["border"])

    def _carrusel_seleccionar(self, index):
        """Selecciona un análisis SIN recalcularlo ni crear otro registro.

        El click es una operación puramente de lectura: restaura foto, curva,
        máscaras, ROIs y métricas guardadas en la base. Esta separación entre
        seleccionar y calcular elimina la duplicación del carrusel.
        """
        self.cargar_snapshot(index)
        self._carrusel_marcar(index)

    def _carrusel_desplazar(self, direccion):
        """Desplaza el carrusel una 'página' de ~140 px a izquierda o
        derecha (botones ◀ ▶)."""
        canvas = self.carrusel_canvas
        x0, x1 = canvas.xview()
        bbox = canvas.bbox("all")
        total = bbox[2] - bbox[0] if bbox else 0
        if total <= 0:
            return
        paso = 140 / total
        nuevo = min(max(x0 + direccion * paso, 0.0), max(0.0, 1.0 - (x1 - x0)))
        canvas.xview_moveto(nuevo)
    def temp_sombra(self, frame):
        """Configura el área de temperatura en sombra."""
        temp_frame = self.create_card(frame)
        temp_frame.config(padx=8, pady=6)
        temp_frame.pack(expand=True, fill='both', pady=5)

        # 1. Creamos un sub-contenedor (Frame) exclusivo para la fila de etiquetas
        labels_frame = tk.Frame(temp_frame, bg=self.palette["panel"])
        labels_frame.pack(side=tk.TOP, fill='x', pady=2)

        # Configuramos 3 columnas para que los textos se repartan el ancho en partes iguales
        labels_frame.columnconfigure(0, weight=1)
        labels_frame.columnconfigure(1, weight=1)
        labels_frame.columnconfigure(2, weight=1)

        # 2. Ubicamos las etiquetas dentro de 'labels_frame' usando grid
        self.lbl_tmrt_sol = tk.Label(
            labels_frame, # OJO: El padre ahora es labels_frame
            text="Tmrt al sol: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_tmrt_sol.grid(row=0, column=0, sticky="ew", padx=2)

        self.lbl_tmrt_sombra = tk.Label(
            labels_frame,
            text="Tmrt en sombra: N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_tmrt_sombra.grid(row=0, column=1, sticky="ew", padx=2)

        self.lbl_delta_tmrt = tk.Label(
            labels_frame,
            text="ΔTmrt (impacto sombra): N/A",
            font=("Arial", 7, "bold"),
            bg=self.palette["panel"],
            fg="#2c3e50",
        )
        self.lbl_delta_tmrt.grid(row=0, column=2, sticky="ew", padx=2)

        self.lbl_tmrt_uncertainty = tk.Label(
            labels_frame,
            text="Incertidumbre operativa Tmrt sombra: N/A",
            font=("Arial", 7), bg=self.palette["panel"], fg="#555555",
        )
        self.lbl_tmrt_uncertainty.grid(row=1, column=0, columnspan=3, sticky="ew", padx=2, pady=(2, 0))

        # 3. Empaquetamos el frame de la gráfica justo debajo de las etiquetas
        self.graph_frame = tk.Frame(temp_frame, bg=self.palette["panel"])
        # Cambiamos side=tk.RIGHT por tk.TOP y le damos expansión para que ocupe el resto del alto
        self.graph_frame.pack(side=tk.TOP, expand=True, fill='both', padx=4, pady=5)
    def imagen(self, frame):
        """Configura el área de visualización de imágenes."""
        img_frame = self.create_card(frame)
        img_frame.pack(expand=True, fill='both', pady=5)
        from matplotlib.figure import Figure
        self.fig1 = Figure()
        self.ax1 = self.fig1.add_subplot(111)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=img_frame)
        # fill+expand: la foto ocupa TODO el frame (que mantiene su
        # tamaño fijo de ~2/3 del alto de la ventana) y se ve grande
        # para trabajar — antes quedaba chica a la izquierda.
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)
    def curva_de_nivel(self, frame):
        """Configura el área de curvas de nivel."""
        nivel_frame = self.create_card(frame)
        nivel_frame.pack(expand=True, fill='both', pady=5)
        self.curva_frame = nivel_frame
        self.curva_frame.bind("<Configure>", self._on_curva_frame_resize)

        from matplotlib.figure import Figure
        self.fig2 = Figure()
        self.ax2 = self.fig2.add_subplot(111)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=nivel_frame)
        self.canvas2.get_tk_widget().pack(fill="both", expand=True)
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
                # Un análisis nuevo recibe identidad propia desde el momento
                # de cargar la foto. Recalcular/guardar ese mismo árbol hace
                # UPDATE sobre este ID, nunca agrega otra miniatura.
                self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
                self.img = None
                self.img_rgb = self.image_processor.load_image_rgb(saved_image_path)
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
    def _timezone_actual(self):
        loc = self.current_location or {}
        tz = loc.get("tz")
        if not tz and "timezone" in self.vars_modelo:
            var = self.vars_modelo.get("timezone")
            tz = var.get() if hasattr(var, "get") else var
        return tz or "America/Argentina/Buenos_Aires"

    def _construir_instante(self, fecha, hora):
        """Construye el instante local sin errores de redondeo de minutos."""
        hora = float(hora)
        if not np.isfinite(hora):
            raise ValueError("La hora debe ser un número finito.")
        # Se acepta 24.0 como inicio del día siguiente; otros valores fuera
        # de un día se rechazan para evitar ambigüedad de UI.
        if hora < 0.0 or hora > 24.0:
            raise ValueError("La hora debe estar entre 0 y 24.")
        return datetime.combine(fecha, datetime.min.time()) + timedelta(hours=hora)

    def _offset_timezone(self, fecha, hora):
        try:
            tz = zoneinfo.ZoneInfo(self._timezone_actual())
            instante = self._construir_instante(fecha, hora).replace(tzinfo=tz)
            offset = instante.utcoffset()
            return None if offset is None else offset.total_seconds() / 3600.0
        except Exception:
            return None

    @staticmethod
    def _optional_float_text(value):
        if hasattr(value, "get"):
            value = value.get()
        text = str(value if value is not None else "").replace(",", ".").strip()
        if not text:
            return None
        number = float(text)
        if not np.isfinite(number):
            raise ValueError("El valor radiativo debe ser finito.")
        return number

    def _obtener_datos_solares(
        self, latitude, longitude, fecha, hora, *, manual_ghi=None,
        mode_override=None, use_pvlib_override=None,
    ):
        """Resuelve posición solar + radiación con procedencia explícita.

        Fuentes disponibles (v14):
        - clear_sky: cielo despejado modelado (pvlib si se solicita/está disponible,
          fallback analítico en caso contrario);
        - manual_measured: medición puntual ingresada por el usuario;
        - manual_scenario: escenario hipotético ingresado manualmente;
        - observed_series: serie meteorológica CSV importada.

        Los componentes faltantes DNI/DHI pueden derivarse, pero esa derivación
        queda registrada en ``quality``/``derived_components``.
        """
        instante = self._construir_instante(fecha, hora)
        tz = self._timezone_actual()
        try:
            self.solar_engine.set_timezone(tz)
        except Exception:
            self.solar_engine.set_timezone("America/Argentina/Buenos_Aires")
        use_pvlib = (
            bool(use_pvlib_override) if use_pvlib_override is not None
            else bool(self.use_pvlib_engine.get())
        )
        self.solar_engine.set_use_pvlib(use_pvlib)

        mode = (
            str(mode_override) if mode_override is not None
            else (self.radiation_source_mode.get() if hasattr(self, "radiation_source_mode") else "clear_sky")
        )
        if manual_ghi is None:
            manual_ghi = self._optional_float_text(getattr(self, "manual_ghi", ""))
        manual_dni = self._optional_float_text(getattr(self, "manual_dni", ""))
        manual_dhi = self._optional_float_text(getattr(self, "manual_dhi", ""))
        max_gap = float(self.settings.get("meteorology_max_gap_minutes", 90.0))
        data = self.meteorology_service.resolve(
            mode=mode,
            solar_engine=self.solar_engine,
            lat=float(latitude), lon=float(longitude), dt=instante,
            manual_ghi=manual_ghi,
            manual_dni=manual_dni,
            manual_dhi=manual_dhi,
            max_gap_minutes=max_gap,
        )
        self.last_meteorology_data = data
        return data

    def cargar_serie_meteorologica(self):
        """Importa una serie CSV y, si hay proyecto, guarda una copia dentro.

        La copia en ``entradas/meteorologia/`` hace que el proyecto .3es sea reproducible
        y no dependa de una ruta externa que pueda desaparecer.
        """
        file_path = filedialog.askopenfilename(
            title="Importar serie meteorológica",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if not file_path:
            return None
        try:
            tz = self._timezone_actual()
            target = file_path
            project = getattr(self.project_manager, "current_project", None)
            if project is not None:
                folder = project.layout.meteorology_dir
                os.makedirs(folder, exist_ok=True)
                target = project.layout.import_input_file(file_path, folder)
            summary = self.meteorology_service.load_series(target, timezone=tz)
            self.meteorology_series_path = target
            self.radiation_source_mode.set("observed_series")
            self.mark_dirty()
            if hasattr(self, "meteorology_status_label") and self.meteorology_status_label.winfo_exists():
                self._refresh_meteorology_status()
            cols = ", ".join(summary["columns"])
            messagebox.showinfo(
                "Serie meteorológica",
                f"Serie cargada correctamente.\n"
                f"Registros: {summary['n']}\n"
                f"Cobertura: {summary['start']} a {summary['end']}\n"
                f"Variables: {cols}",
            )
            return target
        except Exception as exc:
            messagebox.showerror("Serie meteorológica", f"No se pudo cargar la serie:\n{exc}")
            return None

    def _refresh_meteorology_status(self):
        mode = self.radiation_source_mode.get()
        text = SOURCE_LABELS.get(mode, mode)
        if mode == "clear_sky":
            engine = "pvlib/Ineichen" if bool(self.use_pvlib_engine.get()) and self.solar_engine.pvlib_available else "fallback analítico"
            text += f" · {engine}"
        elif mode == "observed_series":
            series = self.meteorology_service.series
            if series is None:
                text += " · sin serie cargada"
            else:
                text += f" · {os.path.basename(series.path or 'serie')} · n={series.n}"
        met = getattr(self, "last_meteorology_data", None) or {}
        if met and met.get("source_mode") == mode:
            text += f" · calidad: {met.get('quality', 'N/D')}"
        for name in ("meteorology_status_label", "model_meteorology_status_label"):
            label = getattr(self, name, None)
            if label is not None and label.winfo_exists():
                if name == "model_meteorology_status_label" and getattr(self, "modo_modelo", None) is not None and self.modo_modelo.get() == "simple":
                    label.config(text="Entrada simple · radiación simplificada según nubosidad")
                else:
                    label.config(text=text)

    def _obtener_radiacion_pvlib(self, latitude, longitude, fecha, hora):
        """Compatibilidad: devuelve datos solo si cielo despejado usa pvlib."""
        if not bool(self.use_pvlib_engine.get()) or self.radiation_source_mode.get() != "clear_sky":
            return None
        try:
            datos = self._obtener_datos_solares(latitude, longitude, fecha, hora)
            return datos if datos.get("source_detail") == "pvlib" else None
        except Exception:
            return None

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
            
            tz_offset = self._offset_timezone(fecha, hora)
            temp_input_mode = getattr(self, "modo_temperatura", tk.StringVar(value="simple")).get()
            if temp_input_mode == "advanced":
                effective_tmrt_mode = self.tmrt_model_mode.get()
                solar_data = self._obtener_datos_solares(latitude, longitude, fecha, hora)
            else:
                # Modo simple no hereda opciones avanzadas ocultas.
                effective_tmrt_mode = "standard"
                solar_data = self._obtener_datos_solares(
                    latitude, longitude, fecha, hora,
                    mode_override="clear_sky", use_pvlib_override=False,
                )
            self.temp_calculator = Temperatura(
                latitude, longitude, k_factor=self.k_factor, tz_offset_hours=tz_offset,
                model_mode=effective_tmrt_mode,
            )
            # Si la fuente es una serie observada, Ta disponible en esa serie
            # pasa a ser la temperatura de aire del cálculo. Si no existe, se
            # conserva el valor ingresado por el usuario y queda trazado como
            # fallback de entrada.
            if solar_data.get("source_mode") == "observed_series" and solar_data.get("ta_c") is not None:
                temp_ambient = float(solar_data["ta_c"])
            transmittance_override = None
            full_shadow_transmittance = None
            if not manual_text and self.shadow_photo_analysis is not None:
                transmittance_override = self.shadow_photo_analysis.get("effective_transmittance")
                full_shadow_transmittance = self.shadow_photo_analysis.get("shadow_transmittance")

            result = self.temp_calculator.calculate_tmrt(
                temp_ambient,
                porcentaje_sombra,
                shadow_type="tree",
                date_value=fecha,
                time_value=hora,
                radiation_override=solar_data["ghi"],
                solar_altitude_override=solar_data["elevation"],
                dni_override=solar_data.get("dni"),
                dhi_override=solar_data.get("dhi"),
                full_shadow_transmittance=full_shadow_transmittance,
                transmittance_override=transmittance_override,
            )
            result["Fuente_solar"] = solar_data.get("source_label", solar_data.get("source", "fallback"))
            result["Fuente_solar_codigo"] = solar_data.get("source_mode", "clear_sky")
            result["Calidad_meteorologica"] = solar_data.get("quality")
            result["Componentes_derivados"] = list(solar_data.get("derived_components", []))
            result["Advertencias_meteorologicas"] = list(solar_data.get("warnings", []))
            try:
                uncertainty = estimate_tmrt_uncertainty(
                    air_temp_c=temp_ambient,
                    tau=float(result.get("Transmitancia_tau", 1.0)),
                    ghi=float(solar_data["ghi"]),
                    dni=solar_data.get("dni"), dhi=solar_data.get("dhi"),
                    solar_elevation_deg=float(solar_data["elevation"]),
                    model_mode=self.tmrt_model_mode.get(),
                    k_factor=self.k_factor,
                    source_quality=solar_data.get("quality"),
                    advanced_config=getattr(self.temp_calculator, "advanced_config", None),
                )
                result["Incertidumbre_operativa"] = uncertainty
            except Exception as exc:
                result["Incertidumbre_operativa"] = None
                result.setdefault("Advertencias_meteorologicas", []).append(
                    f"No se pudo estimar incertidumbre operativa: {exc}"
                )
            self.tmrt_result = result
            if hasattr(self, "lbl_porcentaje_sombra"):
                if manual_text:
                    etiqueta_sombra = f"Cobertura de sombra manual: {porcentaje_sombra:.2f}%"
                else:
                    etiqueta_sombra = f"Cobertura de sombra fotográfica: {porcentaje_sombra:.2f}%"
                self.lbl_porcentaje_sombra.config(text=etiqueta_sombra)
                if manual_text:
                    tau_full = self.temp_calculator._tau_sombra_total("tree")
                    tau_eff = self.temp_calculator.shadow_transmittance(porcentaje_sombra, "tree")
                    if hasattr(self, "lbl_atenuacion_sombra"):
                        self.lbl_atenuacion_sombra.config(
                            text=f"Atenuación sombra asumida: {(1-tau_full)*100:.2f}%"
                        )
                    if hasattr(self, "lbl_transmitancia_sombra"):
                        self.lbl_transmitancia_sombra.config(
                            text=f"Transmitancia efectiva: {tau_eff*100:.2f}%"
                        )
                elif self.shadow_photo_analysis is not None:
                    if hasattr(self, "lbl_atenuacion_sombra"):
                        self.lbl_atenuacion_sombra.config(
                            text=f"Atenuación en sombra: {self.shadow_photo_analysis['attenuation_pct']:.2f}%"
                        )
                    if hasattr(self, "lbl_transmitancia_sombra"):
                        self.lbl_transmitancia_sombra.config(
                            text=f"Transmitancia efectiva: {self.shadow_photo_analysis['effective_transmittance']*100:.2f}%"
                        )
            
            
            self.lbl_tmrt_sol.config(text=f"Tmrt al sol: {result['Tmrt_sol']:.2f} °C")
            self.lbl_tmrt_sombra.config(text=f"Tmrt en sombra: {result['Tmrt_sombra']:.2f} °C")
            self.lbl_delta_tmrt.config(text=f"ΔTmrt (impacto sombra): {result['Delta_Tmrt']:.2f} °C")
            unc = result.get("Incertidumbre_operativa") or {}
            us = unc.get("tmrt_shade") or {}
            if hasattr(self, "lbl_tmrt_uncertainty"):
                if np.isfinite(us.get("p05", np.nan)) and np.isfinite(us.get("p95", np.nan)):
                    self.lbl_tmrt_uncertainty.config(
                        text=(f"Tmrt sombra · intervalo operativo P05–P95: "
                              f"{us['p05']:.1f}–{us['p95']:.1f} °C · no es IC instrumental")
                    )
                else:
                    self.lbl_tmrt_uncertainty.config(text="Incertidumbre operativa Tmrt sombra: N/D")
            # v18: una sola figura de escala Tmrt; la anterior se libera
            # explícitamente antes de crear la siguiente.
            temp_fig = self._show_temperature_graph(result["Tmrt_sol"], result["Tmrt_sombra"])
            if self.project_manager.current_project:
                if not self.current_analysis_id:
                    self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
                temp_img_path = self.project_manager.current_project.layout.element_paths(self.current_analysis_id)["temperature_summary"]
                temp_fig.savefig(temp_img_path, dpi=120, bbox_inches="tight")
                self.last_temp_graph_path = str(temp_img_path)
                self.mark_dirty()
                
        except ValueError as e:
            messagebox.showerror("Error", f"Error al ingresar los datos: {e}")
    def confirmar_seleccion(self):
        if not self.require_project("confirmar selección"):
            return
        # Verificamos que ambas áreas hayan sido seleccionadas
        if self.shape_selector.area_seleccionada is not None and self.shape_selector.area_referencia is not None:
            # v11: se separan explícitamente cobertura geométrica e
            # intensidad/atenuación de sombra. El porcentaje que alimenta
            # el modelo como S es COBERTURA; la transmitancia de las zonas
            # clasificadas sombra se estima por separado contra la referencia.
            analisis = self.image_processor.analizar_sombra_fotografica(
                self.shape_selector.area_seleccionada,
                self.shape_selector.area_referencia,
                mascara_area=self.shape_selector.area_seleccionada_mask,
                mascara_referencia=self.shape_selector.area_referencia_mask,
            )
            self.shadow_photo_analysis = analisis
            self.cobertura_sombra = analisis["coverage_pct"]
            self.atenuacion_sombra = analisis["attenuation_pct"]
            # Compatibilidad con módulos/proyectos anteriores: porcentaje_sombra
            # pasa a significar cobertura cuando el origen es fotográfico v2.
            self.porcentaje_sombra = self.cobertura_sombra
            self.lbl_porcentaje_sombra.config(
                text=f"Cobertura de sombra: {self.cobertura_sombra:.2f}%"
            )
            self.lbl_atenuacion_sombra.config(
                text=f"Atenuación en sombra: {self.atenuacion_sombra:.2f}%"
            )
            self.lbl_transmitancia_sombra.config(
                text=f"Transmitancia efectiva: {analisis['effective_transmittance']*100:.2f}%"
            )
            if self.shadow_detector_enabled.get() and self.img_rgb is not None:
                detected = self.shadow_detector.detect_shadow_mask(self.img_rgb, method="adaptive")
                roi = self.shape_selector.mask_calculo_full
                if roi is None or np.asarray(roi).shape != detected.shape:
                    roi = np.ones_like(detected, dtype=bool)
                quality_meta = self.shadow_detector.compute_shadow_quality(
                    detected, roi_mask=np.asarray(roi, dtype=bool)
                )
                self.shadow_quality = quality_meta.get("shadow_quality")
                
            # Habilitar el botón para curvas de nivel
            self.curve_button.config(state=tk.NORMAL)
            if hasattr(self, "shadow_mask_button"):
                self.shadow_mask_button.config(state=tk.NORMAL)
            self._guardar_mascara_clasificacion_sombra()
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
            self.mark_dirty()
        else:
            print("Error: No se ha seleccionado un área válida.")

    def _guardar_mascara_clasificacion_sombra(self):
        """Guarda una máscara reproducible sombra/sol para auditoría v11."""
        analisis = self.shadow_photo_analysis
        project = self.project_manager.current_project
        if not analisis or project is None:
            return None
        mask = np.asarray(analisis.get("shadow_mask"), dtype=np.float32)
        if mask.size == 0:
            return None
        valid = np.isfinite(mask)
        if not np.any(valid):
            return None

        if not self.current_analysis_id:
            self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
        out_path = project.layout.element_paths(self.current_analysis_id)["shadow_classification"]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        fig, ax = plt.subplots(figsize=(6, 5))
        display = np.ma.masked_invalid(mask)
        im = ax.imshow(display, cmap="gray_r", vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(
            "Clasificación fotográfica sombra / sol\n"
            f"Cobertura {analisis['coverage_pct']:.1f}% · "
            f"Atenuación sombra {analisis['attenuation_pct']:.1f}% · "
            f"umbral I/Iref={analisis['threshold_ratio']:.3f}",
            fontsize=9,
        )
        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1], fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels(["Sol", "Sombra"])
        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.last_shadow_classification_path = str(out_path)
        return str(out_path)

    def mostrar_mascara_sombra(self):
        """Muestra la clasificación sombra/sol y la atenuación óptica local."""
        analisis = self.shadow_photo_analysis
        if not analisis:
            messagebox.showinfo(
                "Sombra fotográfica",
                "Primero confirme un área de cálculo y un área de referencia.",
            )
            return

        dlg = tk.Toplevel(self.root)
        prepare_dialog(dlg, self.root, modal=False, resizable=True, minsize=(720, 440))
        dlg.title("Cobertura e intensidad de sombra")
        dlg.geometry("920x520")
        dlg.configure(bg=self.palette["background"])

        fig, axes = plt.subplots(1, 2, figsize=(9, 4.5))
        mask = np.asarray(analisis["shadow_mask"], dtype=np.float32)
        att = np.asarray(analisis["local_attenuation_map"], dtype=np.float32)

        m0 = np.ma.masked_invalid(mask)
        im0 = axes[0].imshow(m0, cmap="gray_r", vmin=0, vmax=1, interpolation="nearest")
        axes[0].set_title(f"Cobertura de sombra: {analisis['coverage_pct']:.1f}%")
        axes[0].set_xlabel("X")
        axes[0].set_ylabel("Y")
        cb0 = fig.colorbar(im0, ax=axes[0], ticks=[0, 1], fraction=0.046, pad=0.04)
        cb0.ax.set_yticklabels(["Sol", "Sombra"])

        m1 = np.ma.masked_invalid(att)
        im1 = axes[1].imshow(m1, cmap="viridis", vmin=0, vmax=100, interpolation="nearest")
        axes[1].set_title(f"Atenuación en sombra: {analisis['attenuation_pct']:.1f}%")
        axes[1].set_xlabel("X")
        axes[1].set_ylabel("Y")
        cb1 = fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
        cb1.set_label("Atenuación óptica relativa (%)")

        fig.suptitle(
            f"Método {analisis['algorithm']} · umbral I/Iref={analisis['threshold_ratio']:.3f} · "
            f"transmitancia efectiva={analisis['effective_transmittance']:.3f}",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

        note = tk.Label(
            dlg,
            text=(
                "Cobertura = fracción de píxeles clasificados como sombra.  "
                "Atenuación = reducción fotométrica relativa respecto del área de referencia; "
                "no sustituye una medición radiométrica de irradiancia."
            ),
            bg=self.palette["background"],
            justify="left",
            wraplength=880,
            font=("Arial", 8),
        )
        note.pack(fill="x", padx=10, pady=(0, 8))

        def _close():
            plt.close(fig)
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close)

    def exportar_a_excel(self):
        """Guarda la matriz actual en el análisis activo, sin pedir destino."""
        if not self.require_project("guardar la matriz en Excel"):
            return
        if self.shape_selector.area_seleccionada is not None:
            if not self.current_analysis_id:
                self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
            file_path = self.project_manager.current_project.layout.element_paths(self.current_analysis_id)["matrix"]
            pd.DataFrame(self.shape_selector.area_seleccionada).to_excel(file_path, index=False)
            self.last_matrix_path = file_path
            self.mark_dirty()
            messagebox.showinfo("Excel", f"Matriz guardada en:\n{file_path}")
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

    # ---------------------------------------------------------------- delegados
    # Refactor (README §6): los constructores de panel y los toggles de
    # modo viven en ui/panels.py; SombraApp conserva estos delegados de
    # un renglón porque los llaman módulos externos (settings_manager,
    # app_state) y los call sites internos con los mismos nombres.

    def _build_controles(self, vars_dict):
        return ui_panels._build_controles(vars_dict)

    def setup_panel_1(self):
        return ui_panels.setup_panel_1(self)

    def setup_panel_4(self):
        return ui_panels.setup_panel_4(self)

    def crear_control(self, panel, texto, var, fila, rango=None, es_fecha=False):
        return ui_panels.crear_control(self, panel, texto, var, fila, rango, es_fecha)

    def _toggle_modelo_mode(self):
        return ui_panels._toggle_modelo_mode(self)

    def _toggle_edicion_mode(self):
        return ui_panels._toggle_edicion_mode(self)

    def _toggle_temperatura_mode(self):
        return ui_panels._toggle_temperatura_mode(self)

    def _toggle_panel2_advanced(self):
        return ui_panels._toggle_panel2_advanced(self)

    def _update_city_options(self):
        return ui_panels._update_city_options(self)

    def _filter_city_options(self, event):
        return ui_panels._filter_city_options(self, event)

    def _apply_location(self, show_message):
        return ui_panels._apply_location(self, show_message)

    def mostrar_curvas_nivel(self):
        """Genera un mapa interactivo de Tmrt local.

        La escala de color usa exactamente el mínimo y máximo de Tmrt
        finitos del mapa. Por lo tanto, el rango mostrado en la colorbar
        coincide con el rango de valores que se pueden leer al mover el
        mouse sobre la figura.
        """
        if not self.require_project("generar curvas de nivel"):
            return
        if self.shape_selector.area_seleccionada is None:
            return

        # El mapa se voltea para conservar la orientación visual que ya
        # utiliza la aplicación en la curva de nivel.
        temp_ambient, hora, fecha, lat, lon = self._leer_parametros_tmrt()
        analisis_foto = self.image_processor.analizar_sombra_fotografica(
            self.shape_selector.area_seleccionada,
            self.shape_selector.area_referencia,
            mascara_area=self.shape_selector.area_seleccionada_mask,
            mascara_referencia=self.shape_selector.area_referencia_mask,
        )
        self.shadow_photo_analysis = analisis_foto
        self.cobertura_sombra = analisis_foto["coverage_pct"]
        self.atenuacion_sombra = analisis_foto["attenuation_pct"]
        self.porcentaje_sombra = self.cobertura_sombra

        # Mapa binario de cobertura (0=sol, 100=sombra) separado de la
        # transmitancia óptica local. Así la Tmrt espacial usa la intensidad
        # medida dentro de la sombra sin confundirla con área sombreada.
        shadow_mask = np.asarray(analisis_foto["shadow_mask"], dtype=np.float32)
        mapa_sombra = (shadow_mask * np.float32(100.0)).astype(np.float32, copy=False)
        mapa_sombra_volteado = np.flipud(mapa_sombra)
        tau_photo_map = np.flipud(
            np.asarray(analisis_foto["local_transmittance_map"], dtype=np.float32)
        )
        attenuation_photo_map = np.flipud(
            np.asarray(analisis_foto["local_attenuation_map"], dtype=np.float32)
        )

        tz_offset = self._offset_timezone(fecha, hora)
        calculador = Temperatura(
            lat, lon, k_factor=self.k_factor, tz_offset_hours=tz_offset,
            model_mode=self.tmrt_model_mode.get(),
        )
        solar_data = self._obtener_datos_solares(lat, lon, fecha, hora)
        if solar_data.get("source_mode") == "observed_series" and solar_data.get("ta_c") is not None:
            temp_ambient = float(solar_data["ta_c"])
        resultado_mapa = calculador.calculate_tmrt_map(
            temp_ambient,
            mapa_sombra_volteado,
            shadow_type="tree",
            date_value=fecha,
            time_value=hora,
            radiation_override=solar_data["ghi"],
            solar_altitude_override=solar_data["elevation"],
            dni_override=solar_data.get("dni"),
            dhi_override=solar_data.get("dhi"),
            transmittance_map_override=tau_photo_map,
        )
        resultado_mapa["Solar_azimuth"] = solar_data.get("azimuth")
        resultado_mapa["Fuente_solar"] = solar_data.get("source_label", solar_data.get("source", "fallback"))
        resultado_mapa["Fuente_solar_codigo"] = solar_data.get("source_mode", "clear_sky")
        resultado_mapa["Calidad_meteorologica"] = solar_data.get("quality")
        resultado_mapa["Componentes_derivados"] = list(solar_data.get("derived_components", []))
        mapa_temperatura = np.asarray(resultado_mapa["Tmrt_map"], dtype=np.float32)

        # Variables locales que se mostrarán en el hover. Se derivan del
        # MISMO modelo que genera el mapa para evitar discrepancias entre
        # tooltip, colorbar y curva.
        tau_map = np.asarray(tau_photo_map, dtype=np.float32)
        radiacion_global = max(0.0, float(resultado_mapa["Radiacion_Wm2"]))
        radiacion_efectiva = (np.float32(radiacion_global) * tau_map).astype(np.float32, copy=False)
        # Temperatura del aire local estimada bajo sombra. No se deriva de
        # Tmrt: usa la radiación evitada respecto a pleno sol y un modelo
        # empírico acotado (ver shadow_temp.Temperatura).
        aire_local_estimado = calculador.estimate_local_air_temperature_map(
            temp_ambient,
            mapa_sombra_volteado,
            radiacion_global,
            shadow_type="tree",
            cooling_coefficient=float(
                self.settings.get("local_air_tree_coefficient", 0.0025)
            ),
            max_cooling=float(
                self.settings.get("local_air_tree_max_cooling", 2.5)
            ),
            transmittance_map_override=tau_photo_map,
        )
        tmrt_sol_result = calculador.calculate_tmrt(
            temp_ambient, 0.0, shadow_type="tree", date_value=fecha, time_value=hora,
            radiation_override=solar_data["ghi"],
            solar_altitude_override=solar_data["elevation"],
            dni_override=solar_data.get("dni"),
            dhi_override=solar_data.get("dhi"),
        )
        tmrt_sol = float(tmrt_sol_result["Tmrt_sol"])
        delta_tmrt_map = (np.float32(tmrt_sol) - mapa_temperatura).astype(np.float32, copy=False)

        finite = mapa_temperatura[np.isfinite(mapa_temperatura)]
        if finite.size == 0:
            messagebox.showerror("Error", "El mapa Tmrt no contiene valores válidos.")
            return
        tmrt_min = float(np.min(finite))
        tmrt_max = float(np.max(finite))

        from plot_style import (
            CMAP_CURVAS_NIVEL, CMAP_HISTOGRAMA,
            agregar_colorbar_temperatura, anotar_estadisticas,
            anotar_metadatos,
        )

        # Volvemos al FigureCanvasTkAgg real para que Matplotlib reciba
        # motion_notify_event. La versión anterior convertía la figura en
        # PNG y la mostraba dentro de un Label de Tk, lo que hacía
        # imposible consultar el dato bajo el mouse de forma fiable.
        if self.curva_label is not None:
            self.curva_label.destroy()
            self.curva_label = None
            self.curva_photo = None

        self.fig2.clf()
        ax = self.fig2.add_subplot(111)
        self.ax2 = ax

        # Para dibujar se usa una malla reducida; los datos científicos y
        # el hover permanecen en resolución completa.
        x_disp, y_disp, mapa_disp, _display_stride = self._contour_display_grid(mapa_temperatura)
        span = tmrt_max - tmrt_min
        if span > 1e-9:
            niveles = np.linspace(tmrt_min, tmrt_max, 21)
            relleno = ax.contourf(
                x_disp, y_disp, mapa_disp,
                levels=niveles,
                cmap=CMAP_CURVAS_NIVEL,
                vmin=tmrt_min,
                vmax=tmrt_max,
                antialiased=True,
            )
            ax.contour(
                x_disp, y_disp, mapa_disp,
                levels=niveles[::2],
                colors="0.35",
                linewidths=0.45,
                alpha=0.55,
            )
            ticks = np.linspace(tmrt_min, tmrt_max, 6)
        else:
            eps = max(0.01, abs(tmrt_min) * 1e-6)
            niveles = np.array([tmrt_min - eps, tmrt_min + eps])
            relleno = ax.contourf(
                x_disp, y_disp, mapa_disp,
                levels=niveles,
                cmap=CMAP_CURVAS_NIVEL,
                vmin=tmrt_min - eps,
                vmax=tmrt_min + eps,
            )
            ticks = np.array([tmrt_min])
        ax.set_xlim(0, mapa_temperatura.shape[1] - 1)
        ax.set_ylim(0, mapa_temperatura.shape[0] - 1)

        ax.set_xlabel("Posición X (px)")
        ax.set_ylabel("Posición Y (px)")
        ax.set_title(
            "Tmrt estimada según distribución local de sombra\n"
            f"T aire {temp_ambient:.1f} °C · rad. {radiacion_global:.0f} W/m² · "
            f"alt. solar {resultado_mapa['Solar_altitude']:.1f}° · "
            f"fuente {resultado_mapa.get('Fuente_solar', 'fallback')} · "
            f"{resultado_mapa.get('Modelo_Tmrt_label', 'Modelo Tmrt')}",
            fontsize=9,
        )
        cbar = agregar_colorbar_temperatura(
            self.fig2, ax, relleno, unidad="°C", etiqueta="Tmrt", ticks=ticks
        )
        if span <= 1e-9:
            cbar.ax.set_title(f"uniforme\n{tmrt_min:.2f} °C", fontsize=7)

        # Indicación explícita del rango que puede aparecer en el hover.
        ax.text(
            0.01, 0.01,
            f"Rango consultable con mouse: {tmrt_min:.2f}–{tmrt_max:.2f} °C",
            transform=ax.transAxes,
            fontsize=7.5,
            va="bottom",
            ha="left",
            bbox=dict(boxstyle="round", fc="white", ec="0.75", alpha=0.82),
        )
        add_solar_indicator_2d(
            ax, resultado_mapa.get("Solar_azimuth"), resultado_mapa.get("Solar_altitude"),
            corner="upper-right",
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.fig2.tight_layout(pad=0.8)
        anotar_metadatos(
            self.fig2,
            f"Mover mouse: valores locales · clic izq.: fijar · clic der.: liberar  ·  "
            f"Generado: {timestamp}",
        )

        # Guardamos exactamente las matrices que corresponden a la figura
        # activa. El hover consulta estas matrices, no vuelve a estimar el
        # valor a partir del color del gráfico.
        self.tmrt_map = mapa_temperatura
        self.tmrt_hover_data = {
            "tmrt": mapa_temperatura,
            "air_temp": float(temp_ambient),
            "local_air_est": np.asarray(aire_local_estimado, dtype=np.float32),
            "shadow": np.asarray(mapa_sombra_volteado, dtype=np.float32),
            "attenuation": np.asarray(attenuation_photo_map, dtype=np.float32),
            "transmittance": np.asarray(tau_photo_map, dtype=np.float32),
            "shadow_coverage_pct": float(analisis_foto["coverage_pct"]),
            "shadow_attenuation_pct": float(analisis_foto["attenuation_pct"]),
            "effective_radiation": np.asarray(radiacion_efectiva, dtype=np.float32),
            "delta_tmrt": np.asarray(delta_tmrt_map, dtype=np.float32),
            "tmrt_sun": float(tmrt_sol),
            "global_radiation": float(radiacion_global),
            "tmrt_min": tmrt_min,
            "tmrt_max": tmrt_max,
        }
        self.curvas_nivel_creadas = True
        self._curve_pinned_pixel = None

        canvas_widget = self.canvas2.get_tk_widget()
        if not canvas_widget.winfo_ismapped():
            canvas_widget.pack(fill="both", expand=True)
        self._setup_hover_tmrt_map(ax, self.canvas2)
        self.canvas2.draw_idle()

        project = self.project_manager.current_project
        if not self.current_analysis_id:
            self.current_analysis_id = AnalysisRecordStore.new_analysis_id()
        artifact_paths = project.layout.element_paths(self.current_analysis_id)

        curve_path = artifact_paths["curve"]
        self.fig2.savefig(curve_path, format="png", dpi=150, bbox_inches="tight", pad_inches=0.1)
        self.curva_img_pil_original = None
        self.last_curve_path = str(curve_path)

        hist_path = artifact_paths["histogram"]
        hist_fig, hist_ax = plt.subplots()
        area_hist = np.asarray(self.shape_selector.area_seleccionada)
        mask_hist = self.shape_selector.area_seleccionada_mask
        if mask_hist is not None and np.asarray(mask_hist).shape == area_hist.shape:
            values = area_hist[np.asarray(mask_hist, dtype=bool)]
        else:
            values = area_hist[np.isfinite(area_hist)]
        counts, bins, patches = hist_ax.hist(values, bins=50, alpha=0.95)
        cmap = plt.get_cmap(CMAP_HISTOGRAMA)
        max_count = max(counts) if len(counts) else 1
        for c, patch in zip(counts, patches):
            patch.set_facecolor(cmap(c / max_count if max_count else 0))
        hist_ax.set_xlabel("Nivel de gris")
        hist_ax.set_ylabel("Frecuencia (cantidad de píxeles)")
        hist_ax.set_title(f"Histograma — {self.current_image_stem}")
        anotar_estadisticas(hist_ax, values)
        hist_fig.tight_layout()
        anotar_metadatos(hist_fig, f"Generado: {timestamp}")
        hist_fig.savefig(hist_path, dpi=150)
        plt.close(hist_fig)

        self.last_histogram_path = str(hist_path)
        self._registrar_histograma_en_carrusel()

        excel_path = artifact_paths["matrix"]
        pd.DataFrame(self.shape_selector.area_seleccionada).to_excel(excel_path, index=False)
        self.last_matrix_path = str(excel_path)
        self.mark_dirty()

    def _setup_hover_tmrt_map(self, ax, canvas):
        """Activa lectura local del mapa Tmrt bajo el mouse.

        El cuadro muestra únicamente las variables locales útiles:
        Tmrt, temperatura del aire local estimada, clasificación sombra/sol,
        atenuación óptica local y radiación efectiva. La anotación cambia de
        cuadrante según la posición del cursor para mantenerse dentro del
        área de datos y no invadir los ejes.

        Clic izquierdo fija el punto; clic derecho lo libera.
        """
        if self._curve_hover_canvas is not None:
            if self._curve_hover_cid is not None:
                try:
                    self._curve_hover_canvas.mpl_disconnect(self._curve_hover_cid)
                except Exception:
                    pass
            if self._curve_click_cid is not None:
                try:
                    self._curve_hover_canvas.mpl_disconnect(self._curve_click_cid)
                except Exception:
                    pass

        self._curve_hover_canvas = canvas
        self._curve_pinned_pixel = None

        annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(0.02, 0.98),
            textcoords="axes fraction",
            fontsize=8,
            ha="left",
            va="bottom",
            bbox=dict(boxstyle="round", fc="white", ec="0.35", alpha=0.94),
            arrowprops=dict(arrowstyle="->", color="0.35", lw=0.7),
            zorder=25,
        )
        annotation.set_visible(False)
        self._curve_hover_annotation = annotation

        marker, = ax.plot(
            [], [],
            marker="o", markersize=4.5,
            markerfacecolor="white", markeredgecolor="black",
            linestyle="none", zorder=20,
        )
        marker.set_visible(False)

        def _valor_texto(x, y):
            data = self.tmrt_hover_data
            if not data:
                return None
            tmrt = data["tmrt"]
            if not (0 <= y < tmrt.shape[0] and 0 <= x < tmrt.shape[1]):
                return None
            value = float(tmrt[y, x])
            if not np.isfinite(value):
                return None
            sombra = float(data["shadow"][y, x])
            atenuacion = float(data["attenuation"][y, x])
            rad_eff = float(data["effective_radiation"][y, x])
            aire_local = float(data["local_air_est"][y, x])
            estado = "Sombra" if sombra >= 50.0 else "Sol"
            return (
                f"Tmrt local: {value:.2f} °C\n"
                f"T aire local estimada: {aire_local:.2f} °C\n"
                f"Clasificación: {estado}\n"
                f"Atenuación local: {atenuacion:.1f} %\n"
                f"Radiación efectiva: {rad_eff:.0f} W/m²"
            )

        def _posicionar_dentro_del_mapa(x, y):
            """Mantiene el tooltip completamente dentro del área del mapa.

            El texto usa coordenadas relativas a los ejes (0..1), no un
            desplazamiento en píxeles. Se ubica en el cuadrante opuesto al
            cursor; así la caja nunca invade ticks/etiquetas de los ejes y
            además deja visible la zona que se está inspeccionando.
            """
            data = self.tmrt_hover_data or {}
            tmrt = data.get("tmrt")
            if tmrt is None:
                return
            h, w = tmrt.shape[:2]

            if x < (w - 1) / 2.0:
                tx = 0.98
                annotation.set_ha("right")
            else:
                tx = 0.02
                annotation.set_ha("left")

            if y < (h - 1) / 2.0:
                ty = 0.98
                annotation.set_va("top")
            else:
                ty = 0.02
                annotation.set_va("bottom")

            annotation.set_position((tx, ty))

        def _mostrar(x, y):
            text = _valor_texto(x, y)
            if text is None:
                annotation.set_visible(False)
                marker.set_visible(False)
                canvas.draw_idle()
                return False
            annotation.xy = (x, y)
            _posicionar_dentro_del_mapa(x, y)
            annotation.set_text(text)
            annotation.set_visible(True)
            marker.set_data([x], [y])
            marker.set_visible(True)
            canvas.draw_idle()
            return True

        def on_move(event):
            # Si hay un punto fijado, mover el mouse no lo reemplaza.
            if self._curve_pinned_pixel is not None:
                _mostrar(*self._curve_pinned_pixel)
                return

            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if annotation.get_visible() or marker.get_visible():
                    annotation.set_visible(False)
                    marker.set_visible(False)
                    canvas.draw_idle()
                return
            x = int(round(event.xdata))
            y = int(round(event.ydata))
            _mostrar(x, y)

        def on_click(event):
            if event.button == 3:
                self._curve_pinned_pixel = None
                if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
                    _mostrar(int(round(event.xdata)), int(round(event.ydata)))
                else:
                    annotation.set_visible(False)
                    marker.set_visible(False)
                    canvas.draw_idle()
                return

            if event.button != 1 or event.inaxes != ax or event.xdata is None or event.ydata is None:
                return
            x = int(round(event.xdata))
            y = int(round(event.ydata))
            if _valor_texto(x, y) is not None:
                self._curve_pinned_pixel = (x, y)
                _mostrar(x, y)

        self._curve_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)
        self._curve_click_cid = canvas.mpl_connect("button_press_event", on_click)

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
        """Respalda el informe del elemento actual en resultados/informes/."""
        if not self.require_project("respaldar el informe PDF"):
            return
        pdf_generator = PDFReportGenerator(self)
        path = pdf_generator.generate_report()
        if path:
            self.last_element_report_path = path
            self.mark_dirty()
            messagebox.showinfo("Informe", f"Informe respaldado en:\n{path}")
    def actualizar_dia(self, fecha_str, dia_var):
        # Función para actualizar día del año desde fecha
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            dia_del_año = fecha.timetuple().tm_yday
            dia_var.set(dia_del_año)
            # v14: conservar también la fecha calendario exacta para poder
            # consultar series meteorológicas con año real.
            for _vars in (getattr(self, "vars", {}), getattr(self, "vars_modelo", {})):
                try:
                    if _vars.get("dia") is dia_var:
                        _vars["_date_iso"] = fecha.date().isoformat()
                        _vars["_year"] = fecha.year
                except Exception:
                    pass
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
    def _scene_view_parent(self, mode):
        if mode == "diseno":
            return self.frame7
        if mode == "modelo":
            return self.frame11
        raise ValueError(f"Modo de vista desconocido: {mode}")

    def _cleanup_scene_view_host(self, mode):
        hosts = getattr(self, "_scene_view_hosts", {})
        host = hosts.pop(mode, None)
        if not host:
            return
        frame3d = host.get("view3d")
        controller = getattr(frame3d, "_sombra_scene3d_controller", None) if frame3d is not None else None
        if controller is not None:
            try:
                controller.close()
            except Exception:
                pass
        notebook = host.get("notebook")
        if notebook is not None:
            try:
                notebook.destroy()
            except tk.TclError:
                pass

    def _get_scene_view_frames(self, mode):
        """Devuelve (2D, 3D, notebook) dentro del MISMO frame principal.

        v30 conserva frame7 para Edición y frame11 para Modelo como hosts,
        pero ambos abarcan las cuatro celdas centrales (frame2..frame5).
        Dentro de cada host crea dos pestañas que llenan el 100 % del área.
        No cambia el lateral, el carrusel ni los cálculos científicos.
        """
        parent = self._scene_view_parent(mode)
        if not hasattr(self, "_scene_view_hosts"):
            self._scene_view_hosts = {}
        host = self._scene_view_hosts.get(mode)
        if host is not None:
            notebook = host.get("notebook")
            try:
                if notebook is not None and notebook.winfo_exists():
                    return host["view2d"], host["view3d"], notebook
            except tk.TclError:
                pass
            self._cleanup_scene_view_host(mode)

        # El parent puede contener un canvas legacy si se entra por primera
        # vez desde una versión/proyecto previo. Se limpia solo la capa UI.
        for widget in parent.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass

        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)
        view2d = tk.Frame(notebook, bg=self.palette["panel"])
        view3d = tk.Frame(notebook, bg=self.palette["panel"])
        notebook.add(view2d, text="Vista 2D")
        notebook.add(view3d, text="Vista 3D")
        self._scene_view_hosts[mode] = {
            "notebook": notebook,
            "view2d": view2d,
            "view3d": view3d,
        }
        return view2d, view3d, notebook

    def mostrar_vista_3d_diseno(self):
        if not self.require_project("generar la vista 3D"):
            return
        view2d, view3d, notebook = self._get_scene_view_frames("diseno")
        if not all(k in self.vars for k in ("X", "Y", "T")):
            self.actualizar_grafico_diseno(self.frame7)
        backend = design.generar_3d(self.vars, view3d)
        if backend:
            notebook.select(view3d)

    def mostrar_vista_3d_modelo(self):
        if not self.require_project("generar la vista 3D"):
            return
        view2d, view3d, notebook = self._get_scene_view_frames("modelo")
        if not all(k in self.vars_modelo for k in ("X", "Y", "T")):
            self.generar_grafico_modelo()
        backend = modelo.generar_3d(self.vars_modelo, view3d)
        if backend:
            notebook.select(view3d)

    def render_grafico_en_frame(self, target_frame, grafico_fn, *args):
        for widget in target_frame.winfo_children():
            widget.destroy()
        
        
        # Crear nuevo gráfico en frame2 y capturar el canvas
        return grafico_fn(*args, target_frame)
    def actualizar_grafico_diseno(self, target_frame=None):
        if target_frame is None or target_frame is self.frame7:
            target_frame, _view3d, notebook = self._get_scene_view_frames("diseno")
        else:
            notebook = None

        # El 2D conserva exactamente el renderer Matplotlib existente; solo
        # cambia el contenedor físico en el que se monta.
        fig, ax, self.canvas_diseno = self.render_grafico_en_frame(
            target_frame,
            lambda vars, frame: design.crear_area_grafico(vars, frame, self),
            self.vars,
        )

        if notebook is not None:
            notebook.select(target_frame)
        # El renderer de Edición ya conecta un único handler de click.
        # No volver a conectarlo aquí: hacerlo dos veces abría dos diálogos
        # de Árbol y rompía el flujo de dos clicks de Estructura.
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
            self.dataset_saver.save_dataset(save_image=False)
            self.mark_dirty()
            messagebox.showinfo(
                "Respaldo de dataset",
                f"Dataset actualizado en:\n{self.project_manager.current_project.layout.dataset_dir}"
            )
        except Exception as e:
                        messagebox.showerror("Error", f"No se pudo guardar el dataset: {str(e)}")

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
                text = f"Atenuación fotométrica local: {sombra:.2f}%"

            self._shadow_hover_annotation.xy = (event.xdata, event.ydata)
            self._shadow_hover_annotation.set_text(text)
            self._shadow_hover_annotation.set_visible(True)
            canvas.draw_idle()

        self._shadow_hover_cid = canvas.mpl_connect("motion_notify_event", on_move)