"""Construcción de la barra de menús y atajos."""

from __future__ import annotations

import tkinter as tk


class MenuBar:
    """Construye la barra de menús principal."""

    def __init__(self, app):
        self.app = app

    def setup(self) -> None:
        """Crea menús y registra atajos de teclado."""
        menu_bar = tk.Menu(self.app.root)

        archivo_menu = tk.Menu(menu_bar, tearoff=0)
        archivo_menu.add_command(label="Nuevo proyecto", accelerator="Ctrl+N", command=self.app.new_project)
        archivo_menu.add_command(label="Abrir proyecto…", accelerator="Ctrl+O", command=self.app.open_project)
        archivo_menu.add_command(label="Guardar proyecto", accelerator="Ctrl+S", command=self.app.save_project)
        archivo_menu.add_command(label="Guardar como…", command=self.app.save_project_as)
        archivo_menu.add_separator()

        importar_menu = tk.Menu(archivo_menu, tearoff=0)
        importar_menu.add_command(label="Importar imagen base…", command=self.app.cargar_imagen)
        importar_menu.add_command(label="Importar proyecto (.3es)…", command=self.app.import_project)
        archivo_menu.add_cascade(label="Importar…", menu=importar_menu)

        exportar_menu = tk.Menu(archivo_menu, tearoff=0)
        exportar_menu.add_command(label="Exportar a Excel…", accelerator="Ctrl+E", command=self.app.exportar_a_excel)
        exportar_menu.add_command(label="Exportar a PDF…", accelerator="Ctrl+P", command=self.app.exportar_a_pdf)
        exportar_menu.add_command(label="Exportar dataset…", command=self.app.save_dataset)
        exportar_menu.add_command(label="Guardar snapshot…", command=self.app.save_snapshot)
        exportar_menu.add_command(label="Exportar proyecto (.3es)…", command=self.app.export_project)
        archivo_menu.add_cascade(label="Exportar…", menu=exportar_menu)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", accelerator="Ctrl+Q", command=self.app.exit_app)
        menu_bar.add_cascade(label="Archivo", menu=archivo_menu)

        edicion_menu = tk.Menu(menu_bar, tearoff=0)
        edicion_menu.add_command(label="Deshacer", accelerator="Ctrl+Z", command=self.app.undo)
        edicion_menu.add_command(label="Rehacer", accelerator="Ctrl+Y", command=self.app.redo)
        edicion_menu.add_separator()
        edicion_menu.add_command(label="Preferencias…", command=self.app.open_preferences)
        menu_bar.add_cascade(label="Edición", menu=edicion_menu)

        escena_menu = tk.Menu(menu_bar, tearoff=0)
        paneles_menu = tk.Menu(escena_menu, tearoff=0)
        paneles_menu.add_command(label="Abrir Panel 1", command=lambda: self.app.open_panel(1))
        paneles_menu.add_command(label="Abrir Panel 2", command=lambda: self.app.open_panel(2))
        paneles_menu.add_command(label="Abrir Panel 3 (Modo diseño)", command=lambda: self.app.open_panel(3))
        paneles_menu.add_command(label="Abrir Panel 4 (Modelo)", command=lambda: self.app.open_panel(3))
        escena_menu.add_cascade(label="Paneles", menu=paneles_menu)
        escena_menu.add_separator()
        escena_menu.add_command(label="Mostrar frames Panel 2", command=self.app.show_panel2_frames)
        escena_menu.add_command(label="Mostrar frames Diseño", command=self.app.show_diseno_frames)
        escena_menu.add_command(label="Mostrar frames Modelo", command=self.app.show_modelo_frames)
        menu_bar.add_cascade(label="Escena", menu=escena_menu)

        modelo_menu = tk.Menu(menu_bar, tearoff=0)
        modelo_menu.add_command(
            label="Ejecutar modelo (Panel activo)",
            accelerator="F5",
            command=self.app.run_model_for_active_panel,
        )
        modelo_menu.add_command(
            label="Ejecutar modelo (Panel 4)",
            accelerator="Ctrl+F5",
            command=self.app.generar_grafico_modelo,
        )
        menu_bar.add_cascade(label="Modelo", menu=modelo_menu)

        analisis_menu = tk.Menu(menu_bar, tearoff=0)
        analisis_menu.add_command(label="Estadísticas rápidas", command=self.app.quick_stats)
        analisis_menu.add_command(
            label="Reporte PDF del modelo",
            command=self.app.exportar_a_pdf,
        )
        analisis_menu.add_command(
            label="Exportar matriz del modelo",
            command=self.app.exportar_a_excel,
        )
        menu_bar.add_cascade(label="Análisis", menu=analisis_menu)

        ayuda_menu = tk.Menu(menu_bar, tearoff=0)
        ayuda_menu.add_command(
            label="Manual de usuario",
            command=lambda: self.app._open_link("manual", "https://www.example.com"),
        )
        ayuda_menu.add_command(
            label="Guía rápida",
            command=lambda: self.app._open_link("guia", "https://www.example.com"),
        )
        ayuda_menu.add_command(label="Acerca de…", command=self.app.show_about)
        menu_bar.add_cascade(label="Ayuda", menu=ayuda_menu)

        self.app.root.config(menu=menu_bar)

        # Atajos globales
        self.app.root.bind_all("<Control-n>", lambda _e: (self.app.new_project(), "break")[1])
        self.app.root.bind_all("<Control-o>", lambda _e: (self.app.open_project(), "break")[1])
        self.app.root.bind_all("<Control-s>", lambda _e: (self.app.save_project(), "break")[1])
        self.app.root.bind_all("<Control-e>", lambda _e: (self.app.exportar_a_excel(), "break")[1])
        self.app.root.bind_all("<Control-p>", lambda _e: (self.app.exportar_a_pdf(), "break")[1])
        self.app.root.bind_all("<Control-q>", lambda _e: (self.app.exit_app(), "break")[1])
        self.app.root.bind_all("<F5>", lambda _e: (self.app.run_model_for_active_panel(), "break")[1])
        self.app.root.bind_all("<Control-F5>", lambda _e: (self.app.generar_grafico_modelo(), "break")[1])