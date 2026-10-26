# Fronteras del núcleo y refactor

`core/surface_model.py` contiene las tablas, clases y 28 definiciones físicas extraídas de modelo_con_excel.py. La API histórica reexporta los mismos objetos; no se mantienen dos implementaciones. `core/scenario.py` importa el núcleo directamente.

`core/app_state.py` serializa variables por un protocolo get/set y valores simples por defecto. No crea variables Tk ni diálogos. `core/project_manager.py` recibe interaction; el adaptador HeadlessInteraction registra mensajes y rechaza decisiones que requieren una persona, sin responder automáticamente. SombraApp inyecta TkProjectInteraction. Las rutas de proyectos y preferencias continúan siendo las de la base actual.

`ui/photo_analysis.py` conserva los nombres públicos de selección, máscaras, curvas y hover mediante un mixin. `ui/validation_dialogs.py` agrupa CSV/calibración; `core/scene3d_data.py` adapta matrices ya calculadas sin renderer. Los controladores meteorológicos y las implementaciones visuales propias del ZIP recibido permanecen.

| Módulo | Líneas recibidas | Líneas finales |
|---|---:|---:|
| ui/app_ui.py | 4984 | 3173 |
| ui/dialogs.py | 1266 | 222 |
| ui/scene3d.py | 1114 | 66 |
| modelo_con_excel.py | 1427 | 506 |

Importar todos los módulos core y ejecutar test_physics.py con Tk/UI bloqueados forman parte de la regresión. La extracción reduce acoplamiento, pero no elimina todas las dependencias al estado de SombraApp ni sustituye una prueba visual de ventanas y OpenGL en Windows.

## Continuación 4.2

Quince métodos de restauración de proyectos, entradas NPZ y carrusel viven ahora en SnapshotRestorationMixin. La clase principal conserva sus nombres por herencia. El editor visual está en ui/photo_exclusion_editor.py; el vínculo entre máscara y selección en services/photo_selection.py; la codificación compacta y la validación sin Tk en core/photo_exclusions.py. Los cambios pendientes se restauran después del elemento correcto y antes de volver a usar sus resultados.

## Cierre incremental 4.3

- `ui/sidebar.py` conserva geometría, scroll y animación de paneles; `ui/preferences.py`, las preferencias. SombraApp hereda ambos mixins y mantiene los callbacks.
- `ui/calibration_dialogs.py`, `ui/comfort_dialogs.py` y `ui/species_dialogs.py` agrupan cada familia de herramientas. HerramientasDialogs mantiene el constructor y la API por herencia.
- `ui/model_excel.py` conserva las tres funciones de carga/guardado/sincronización; modelo_con_excel las reexporta y mantiene render, edición y presets.
- `ui/scene3d.py` es la fachada de selección del motor y limpieza del frame; `scene3d_controller.py` construye la escena VTK (608 líneas), `scene3d_interaction.py` maneja actualización/cámaras/eventos/cierre (339), y `scene3d_backend.py` contiene disponibilidad/diagnóstico/fallback. El fallback importa datos del núcleo y diagnóstico del backend, sin depender de la fachada.

Los 49 métodos trasladados conservan AST, decoradores y callbacks. La construcción VTK conserva el cuerpo de su inicializador. Las funciones físicas se conservan byte a byte. Las pruebas históricas que buscaban texto en un archivo fijo ahora inspeccionan la implementación vigente, manteniendo sus aserciones; no se borraron para ocultar fallos. Las pruebas de actualización VTK usan objetos VTK reales sin llamar a Render(), por lo que no acreditan OpenGL o Windows.

El objetivo de esta ronda es una extracción incremental revisable. SombraApp todavía coordina estado y flujos; no se afirma una arquitectura totalmente desacoplada ni se introduce otro motor o modelo físico.
