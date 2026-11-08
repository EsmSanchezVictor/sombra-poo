"""Menús y atajos del escritorio de Proyecto Sombra."""
from __future__ import annotations

import tkinter as tk


class MenuBar:
    """Construye la barra de menús principal."""

    def __init__(self, app):
        self.app = app
        self._project_enabled = False

    def set_project_enabled(self, enabled: bool) -> None:
        self._project_enabled = enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        for menu, labels in self._project_entries:
            for label in labels:
                menu.entryconfigure(label, state=state)

    def _shortcut(self, callback, *, requires_project=False):
        def handler(_event):
            if not requires_project or self._project_enabled:
                callback()
            return "break"
        return handler

    def setup(self) -> None:
        """Crea menús y registra atajos de teclado."""
        menu_bar = tk.Menu(self.app.root)

        archivo_menu = tk.Menu(menu_bar, tearoff=0)
        archivo_menu.add_command(label="Nuevo proyecto", accelerator="Ctrl+N", command=self.app.new_project)
        archivo_menu.add_command(label="Abrir proyecto…", accelerator="Ctrl+O", command=self.app.open_project)
        archivo_menu.add_command(label="Guardar respaldo", accelerator="Ctrl+S", command=self.app.save_project)
        archivo_menu.add_command(label="Guardar como…", accelerator="Ctrl+Shift+S", command=self.app.save_project_as)
        archivo_menu.add_command(label="Duplicar proyecto…", command=self.app.duplicate_project)
        archivo_menu.add_command(label="Exportar .3es…", command=self.app.export_project_3es)
        archivo_menu.add_command(label="Importar .3es…", command=self.app.import_project_3es)
        archivo_menu.add_separator()

        importar_menu = tk.Menu(archivo_menu, tearoff=0)
        importar_menu.add_command(label="Importar imagen base…", command=self.app.cargar_imagen)
        importar_menu.add_command(label="Importar serie meteorológica CSV…", command=self.app.cargar_serie_meteorologica)
        importar_menu.add_command(label="Importar proyecto (.3es)…", command=self.app.import_project_3es)
        archivo_menu.add_cascade(label="Importar…", menu=importar_menu)

        exportar_menu = tk.Menu(archivo_menu, tearoff=0)
        exportar_menu.add_command(label="Respaldar matriz Excel", accelerator="Ctrl+E", command=self.app.exportar_a_excel)
        exportar_menu.add_command(label="Respaldar PDF del elemento", accelerator="Ctrl+P", command=self.app.exportar_a_pdf)
        exportar_menu.add_command(label="Respaldar dataset", command=self.app.save_dataset)
        exportar_menu.add_command(label="Respaldar análisis actual", command=self.app.save_snapshot)
        exportar_menu.add_command(label="Exportar proyecto (.3es)…", command=self.app.export_project_3es)
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
        paneles_menu.add_command(label="Temperatura", command=lambda: self.app.open_panel(0))
        paneles_menu.add_command(label="Sombra", command=lambda: self.app.open_panel(1))
        paneles_menu.add_command(label="Edición de escena", command=lambda: self.app.open_panel(2))
        paneles_menu.add_command(label="Modelo", command=lambda: self.app.open_panel(3))
        escena_menu.add_cascade(label="Paneles", menu=paneles_menu)
        escena_menu.add_separator()
        escena_menu.add_command(label="Vista de sombra y resultados", command=self.app.show_panel2_frames)
        escena_menu.add_command(label="Vista de edición", command=self.app.show_diseno_frames)
        escena_menu.add_command(label="Vista del modelo", command=self.app.show_modelo_frames)
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
        analisis_menu.add_separator()
        analisis_menu.add_command(
            label="Comparar elementos del proyecto",
            command=self.app.mostrar_analisis_comparativo,
        )
        analisis_menu.add_command(
            label="Curva de sensibilidad sombra–temperatura",
            command=self.app.mostrar_curva_sensibilidad,
        )
        analisis_menu.add_separator()
        analisis_menu.add_command(
            label="Asistente de calibración de k_factor…",
            command=self.app._dialogo_calibrar_k_factor,
        )
        analisis_menu.add_command(
            label="Confort térmico (Heat Index / T. aparente)…",
            command=self.app._dialogo_confort,
        )
        analisis_menu.add_command(
            label="Escenario A/B horario…",
            command=self.app._dialogo_escenario_ab,
        )
        analisis_menu.add_command(
            label="Calibración y validación científica (CSV)…",
            command=self.app._dialogo_validar_csv,
        )
        analisis_menu.add_command(
            label="Auditoría científica / preparación para validación…",
            command=self.app._dialogo_auditoria_cientifica,
        )
        analisis_menu.add_command(
            label="Biblioteca de especies…",
            command=self.app._dialogo_especies,
        )
        analisis_menu.add_command(
            label="Editar base de especies…",
            command=self.app._dialogo_editar_especies,
        )
        analisis_menu.add_command(
            label="Efectividad de árboles (ranking)…",
            command=self.app._dialogo_ranking_arboles,
        )
        analisis_menu.add_separator()
        analisis_menu.add_command(
            label="Generar informe completo (PDF)…",
            accelerator="Ctrl+Shift+P",
            command=self.app.generar_informe_completo,
        )
        analisis_menu.add_command(
            label="Reporte PDF del último elemento",
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
            command=self.app.open_user_help,
        )
        ayuda_menu.add_command(
            label="Guía rápida",
            command=lambda: self.app.open_user_help(quick=True),
        )
        ayuda_menu.add_command(label="Acerca de…", command=self.app.show_about)
        menu_bar.add_cascade(label="Ayuda", menu=ayuda_menu)

        self.app.root.config(menu=menu_bar)

        self._project_entries = (
            (menu_bar, ("Escena", "Modelo", "Análisis")),
            (archivo_menu, ("Guardar respaldo", "Guardar como…", "Duplicar proyecto…",
                            "Exportar .3es…", "Exportar…")),
            (importar_menu, ("Importar imagen base…", "Importar serie meteorológica CSV…")),
            (edicion_menu, ("Deshacer", "Rehacer")),
        )
        self.set_project_enabled(False)

        # Los atajos pertenecen al escritorio, no a los diálogos ni al acceso.
        for key, callback, needs_project in (
            ("<Control-n>", self.app.new_project, False),
            ("<Control-o>", self.app.open_project, False),
            ("<Control-q>", self.app.exit_app, False),
            ("<Control-s>", self.app.save_project, True),
            ("<Control-Shift-S>", self.app.save_project_as, True),
            ("<Control-e>", self.app.exportar_a_excel, True),
            ("<Control-p>", self.app.exportar_a_pdf, True),
            ("<F5>", self.app.run_model_for_active_panel, True),
            ("<Control-F5>", self.app.generar_grafico_modelo, True),
            ("<Control-Shift-P>", self.app.generar_informe_completo, True),
        ):
            self.app.root.bind(key, self._shortcut(callback, requires_project=needs_project))
