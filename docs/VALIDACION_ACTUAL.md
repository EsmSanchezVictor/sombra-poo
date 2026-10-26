# Estado de validación — v35.6-etapa4.3

- Regresión completa: **615 pruebas aprobadas**, sin fallos. Con importaciones pvlib/pythermalcomfort bloqueadas en el proceso principal de pruebas: **606 aprobadas y 9 omitidas**; los subprocesos de autocomprobación conservan su entorno instalado.
- Diez casos nuevos: IO Excel real a través de la API histórica; actualización de matrices/cámara/capa de sombra con objetos VTK reales sin Render(); selección/fallback de backend; informes fotográficos; rechazo de evidencia sintética como fotos declaradas reales; reporte de fallo del proceso gráfico y control del sistema operativo.
- Los 49 métodos trasladados conservan AST. Se compararon además los 141 métodos de SombraApp definidos en la base, 12 de HerramientasDialogs, 17 del controlador VTK y 7 funciones Excel, incluyendo los que no se trasladaron: idénticos.
- 66 archivos de física, persistencia, servicios, fotografías y visualización conservan bytes. Nueve escenas de superficie y ocho casos radiativos, más incertidumbre con semilla, producen resultados idénticos a 4.2. El registro científico conserva advanced_radiative_v2.
- El núcleo y sus pruebas físicas siguen ejecutándose con Tk/UI bloqueados. Autocomprobación del código y pip check: aprobados. Cuentas, configuración y máscaras locales de la base conservan sus bytes.
- El banco de sombra entregado sigue siendo sintético: cero fotografías reales y cero mediciones instrumentales. --require-real lo rechaza deliberadamente. Sus métricas no son exactitud de campo.
- Se intentó ejecutar la comprobación de escritorio: Tk no puede abrirse porque este entorno Linux no dispone de pantalla ($DISPLAY). El JSON registra fallo de disponibilidad. No se interpreta como aprobación de Tk, OpenGL, Windows ni del aspecto de las ventanas.

La evidencia vigente está en validacion/qa_linux/etapa4.3. validacion/qa_linux/etapa4.2 y validacion/qa_linux/base_recibida permanecen como informes históricos. La comprobación de componentes con Tk/VTK reales está preparada para el equipo de escritorio, pero no se ejecutó en Windows. Las pruebas VTK sin Render() verifican datos y cámara, no el controlador gráfico. Tampoco sustituyen el recorrido completo de la aplicación.

La ronda incremental de implementación F3–F7 está descrita en CIERRE_CLAUDE.md. Continúan pendientes las fotografías anotadas/revisadas, la campaña instrumental independiente y la aceptación Windows. El software no incorpora clasificación semántica automática ni se declara calibrado científicamente en campo. No se entrega instalador/exe Windows compilado.
