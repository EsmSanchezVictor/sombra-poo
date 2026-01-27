import tkinter as tk
from tkinter import messagebox


def build_menu(app) -> None:
    menu_bar = tk.Menu(app.root)

    archivo_menu = tk.Menu(menu_bar, tearoff=0)
    archivo_menu.add_command(label="Nuevo proyecto", accelerator="Ctrl+N", command=app.new_project)
    archivo_menu.add_command(label="Abrir proyecto…", accelerator="Ctrl+O", command=app.open_project)
    archivo_menu.add_command(label="Guardar proyecto", accelerator="Ctrl+S", command=app.save_project)
    archivo_menu.add_command(label="Guardar como…", command=app.save_project_as)
    archivo_menu.add_separator()
    importar_menu = tk.Menu(archivo_menu, tearoff=0)
    importar_menu.add_command(label="Importar imagen base…", command=app.cargar_imagen)
    importar_menu.add_command(label="Importar proyecto (.3es)…", command=app.import_project)
    archivo_menu.add_cascade(label="Importar…", menu=importar_menu)
    exportar_menu = tk.Menu(archivo_menu, tearoff=0)
    exportar_menu.add_command(label="Exportar a Excel…", accelerator="Ctrl+E", command=app.exportar_a_excel)
    exportar_menu.add_command(label="Exportar a PDF…", accelerator="Ctrl+P", command=app.exportar_a_pdf)
    exportar_menu.add_command(label="Exportar dataset…", command=app.save_dataset)
    exportar_menu.add_separator()
    exportar_menu.add_command(label="Exportar proyecto (.3es)…", command=app.export_project)
    archivo_menu.add_cascade(label="Exportar…", menu=exportar_menu)
    archivo_menu.add_separator()
    archivo_menu.add_command(label="Salir", accelerator="Ctrl+Q", command=app.exit_app)
    menu_bar.add_cascade(label="Archivo", menu=archivo_menu)

    edicion_menu = tk.Menu(menu_bar, tearoff=0)
    edicion_menu.add_command(label="Deshacer", accelerator="Ctrl+Z", command=app.undo)
    edicion_menu.add_command(label="Rehacer", accelerator="Ctrl+Y", command=app.redo)
    edicion_menu.add_separator()
    edicion_menu.add_command(label="Preferencias…", command=app.open_preferences)
    menu_bar.add_cascade(label="Edición", menu=edicion_menu)

    escena_menu = tk.Menu(menu_bar, tearoff=0)
    paneles_menu = tk.Menu(escena_menu, tearoff=0)
    paneles_menu.add_command(label="Abrir Panel 1", command=lambda: app.open_panel(1))
    paneles_menu.add_command(label="Abrir Panel 2", command=lambda: app.open_panel(2))
    paneles_menu.add_command(label="Abrir Panel 3 (Modo diseño)", command=lambda: app.open_panel(3))
    paneles_menu.add_command(label="Abrir Panel 4 (Modelo)", command=lambda: app.open_panel(3))
    escena_menu.add_cascade(label="Paneles", menu=paneles_menu)
    escena_menu.add_separator()
    escena_menu.add_command(label="Mostrar frames Panel 2", command=app.show_panel2_frames)
    escena_menu.add_command(label="Mostrar frames Diseño", command=app.show_diseno_frames)
    escena_menu.add_command(label="Mostrar frames Modelo", command=app.show_modelo_frames)
    menu_bar.add_cascade(label="Escena", menu=escena_menu)

    modelo_menu = tk.Menu(menu_bar, tearoff=0)
    modelo_menu.add_command(
        label="Ejecutar modelo (F5)",
        command=lambda: app.run_model_for_active_panel(force=False),
    )
    modelo_menu.add_command(
        label="Forzar recalcular (Shift+F5)",
        command=lambda: app.run_model_for_active_panel(force=True),
    )
    menu_bar.add_cascade(label="Modelo", menu=modelo_menu)

    analisis_menu = tk.Menu(menu_bar, tearoff=0)
    analisis_menu.add_command(label="Estadísticas rápidas", command=app.quick_stats)
    analisis_menu.add_command(
        label="Resumen del último cálculo",
        command=lambda: messagebox.showinfo(
            "Resumen",
            app.last_meta if app.last_meta else "No hay cálculos recientes.",
        ),
    )
    analisis_menu.add_command(
        label="Limpiar resultados",
        command=app.clear_last_results,
    )
    menu_bar.add_cascade(label="Análisis", menu=analisis_menu)

    ayuda_menu = tk.Menu(menu_bar, tearoff=0)
    ayuda_menu.add_command(
        label="Guía rápida",
        command=lambda: messagebox.showinfo(
            "Guía rápida",
            "1) Elegí un panel desde Escena > Paneles.\n"
            "2) Cargá una imagen base en Panel 2.\n"
            "3) En Modo diseño agregá árboles o estructuras.\n"
            "4) Generá el gráfico con F5.\n"
            "5) Exportá resultados desde Archivo > Exportar.\n"
            "6) Revisá estadísticas en Análisis.",
        ),
    )
    ayuda_menu.add_command(
        label="Limitaciones del modelo",
        command=lambda: messagebox.showinfo(
            "Limitaciones del modelo",
            "El modelo actual no contempla microclimas locales ni materiales reflectivos avanzados.\n"
            "Los resultados dependen de la calidad de la imagen y las variables de entrada.",
        ),
    )
    ayuda_menu.add_command(label="Acerca de…", command=app.show_about)
    menu_bar.add_cascade(label="Ayuda", menu=ayuda_menu)

    app.root.config(menu=menu_bar)

    app.root.bind_all("<Control-n>", lambda _e: (app.new_project(), "break")[1])
    app.root.bind_all("<Control-o>", lambda _e: (app.open_project(), "break")[1])
    app.root.bind_all("<Control-s>", lambda _e: (app.save_project(), "break")[1])
    app.root.bind_all("<Control-q>", lambda _e: (app.exit_app(), "break")[1])
    app.root.bind_all("<F5>", lambda _e: (app.run_model_for_active_panel(), "break")[1])
    app.root.bind_all("<Shift-F5>", lambda _e: (app.run_model_for_active_panel(force=True), "break")[1])
    app.root.bind_all("<Control-e>", lambda _e: (app.exportar_a_excel(), "break")[1])
    app.root.bind_all("<Control-p>", lambda _e: (app.exportar_a_pdf(), "break")[1])