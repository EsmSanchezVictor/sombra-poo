# Actualizar de 4.2 a 4.3

1. Cierre Sombra y conserve una copia de su carpeta y proyectos.
2. Para la v35.6-etapa4.2 exacta (ZIP SHA256 bae640d1869ed00716d026a5b39d80caa227141b7b1b44a68b2beacf5dfde822), extraiga Actualizar_4_2_a_4_3.zip en la carpeta que contiene main.py, aceptando reemplazar código. El parche no incluye cuentas, configuración local ni máscaras de trabajo.
3. Si tiene otra versión o prefiere una instalación nueva, extraiga sombra-poo.zip completo en otra carpeta. La copia completa conserva los datos que venían en la base actualizada del usuario; no sobrescriba su carpeta de uso con ella si esos datos cambiaron desde entonces.
4. Con el entorno Python de la aplicación, ejecute `python tools/check_installation.py --require-full --report autocomprobacion.json` y después `python main.py`.
5. Abra una copia de su proyecto, genere una escena y guarde/reabra. Las exclusiones de 4.2 mantienen su esquema y compatibilidad: docs/EXCLUSIONES_FOTOGRAFICAS.md.
6. En Windows puede ejecutar `python tools/check_desktop.py --vtk --require-windows --report escritorio_windows.json`; siga después el recorrido manual de docs/ACEPTACION_WINDOWS.md.

No se cambiaron ecuaciones, meteorología, formatos de proyectos ni política de cuentas. Esta entrega divide componentes de interfaz y mejora los informes de evaluación. La ronda de código queda registrada en docs/CIERRE_CLAUDE.md; no se declara completada la campaña de campo ni la aceptación Windows.
