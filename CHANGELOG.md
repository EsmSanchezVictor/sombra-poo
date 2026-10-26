# Historial central

## Reorganización de archivos (sin cambio de versión)

- Solo se reubican archivos que ningún módulo ni prueba lee: evidencia de validación (`validacion/`), notas y manifiestos de etapas anteriores (`docs/historico/`), instrucciones por entrega (`docs/releases/`) e imágenes (`docs/imagenes/`). Código, `data/` de ejecución, cuentas y `requirements*.txt` no se tocan.
- Mapa completo de rutas antiguas y nuevas: [docs/MAPA_DE_ARCHIVOS.md](docs/MAPA_DE_ARCHIVOS.md). Las menciones a rutas antiguas en las entradas de abajo son históricas y se conservan.
- Hecho con `tools/reorganizar_repo.py` (usa `git mv`, conserva el historial).

## v35.6-etapa4.3 — 2026-10-25

- Cierre de la ronda incremental F7: 49 métodos se trasladan sin cambios de AST. Sidebar y preferencias separados de SombraApp; diálogos divididos en calibración, confort y especies; carga/guardado Excel separado del render; VTK dividido en construcción, interacción y backend.
- app_ui.py: 3871 → 3173 líneas; dialogs.py: 948 → 222; scene3d.py: 1047 → 66; modelo_con_excel.py: 707 → 506. La fachada mantiene los nombres históricos.
- F4: informe de evaluación con resúmenes por origen/algoritmo, denominadores de ROI/exclusiones, fotos únicas por SHA256 y --require-real. Se conserva el algoritmo fotográfico y no se añade clasificación semántica automática.
- Kit de evidencia externa: manifiesto fotográfico, procedimiento de campaña y aceptación Windows. Control de componentes Tk/VTK en proceso separado con informe de fallos nativos; no sustituye el recorrido manual de la aplicación.
- F5: cambios/ se identifica como archivo histórico; este CHANGELOG sigue siendo el registro vigente.
- Regresión completa: 615 pruebas aprobadas. Diez pruebas nuevas incluyen IO Excel real y actualización VTK sin contexto OpenGL. Física y meteorología permanecen idénticas a 4.2.
- No hay mediciones de campo ni fotos reales anotadas aportadas. La ejecución gráfica en este entorno sin pantalla registra un fallo de disponibilidad; no se declara aceptación visual o Windows.

## v35.6-etapa4.2 — 2026-10-25

- F7: 15 métodos de restauración/carrusel pasan a ui/snapshot_restoration.py, conservando su API. app_ui.py baja de 4355 a 3871 líneas.
- F4: editor de rectángulos para excluir manualmente materiales ajenos a la superficie comparada; deshacer, limpiar, cancelar y restaurar el elemento guardado.
- La cobertura, la transmitancia, los mapas térmicos y el histograma usan la ROI retenida. Los resultados anteriores se invalidan al editar, y no se permite confundirlos con un cálculo actualizado.
- JSON compacto para correcciones pendientes, NPZ/SQLite para máscaras completas, firma de entradas y selección del elemento activo al reabrir. Se evita aplicar correcciones a otro árbol.
- Esquema de estado 3 solo para proyectos que requieren esta función; se mantienen las migraciones y apertura de esquemas 1/2. Lectores anteriores rechazan la versión nueva.
- En modo con exclusiones se corrige el control de bajo contraste para poblaciones desiguales; sin exclusiones se mantiene el algoritmo anterior. Se registra la política usada.
- Se corrige la restauración de metadatos del detector, que antes se perdían al resetear el panel después de leerlos.
- Física radiativa v2, incertidumbre, meteorología y resultados sin exclusiones preservados. Continúan pendientes fotos anotadas, campaña, Windows y el refactor completo.

## v35.6-etapa4.1 — 2026-10-25

Base: sombra-poo.zip actualizado del usuario, SHA256 5337991567a18628496be162e1688e337c84d339f0bc51b698bae94a5e7d657f. Se conserva su balance radiativo avanzado v2 y sus cambios propios; no es una continuación lineal de la Etapa 4 entregada sobre la base anterior.

- F3: core importable sin tkinter, _tkinter ni ui. AppState no construye variables Tk; el gestor recibe un puerto de interacción y la UI inyecta el adaptador Tk. Los callbacks de presentación de errores se ubican en ui/error_handlers.py.
- F4: shadow_coverage_fraction sustituye a shadow_quality en estados nuevos, con lectura compatible del campo antiguo. ROI/exclusiones validadas, ausencia explícita de valor en ROI vacía, metadatos de ambigüedad y banco de evaluación IoU/F1/falsos positivos. El detector se rotula fotométrico, no IA. No se incorpora un clasificador semántico entrenado.
- F5: README raíz, este CHANGELOG central y documentación vigente en docs/. Las notas del usuario permanecen en cambios/ sin modificaciones. Bundle local de fuentes con etiquetas de base y entrega.
- F6: informe reproducible de campaña con sesgo/RMSE por modelo y separación por campañas. Las etiquetas nuevas y la exportación identifican el modelo activo v2; se conservan claves/columnas históricas v1 por compatibilidad, junto con campos canónicos de valor y versión.
- F7: superficie en core/surface_model.py; selección/mapas fotográficos en ui/photo_analysis.py; CSV de campo en ui/validation_dialogs.py; datos 3D en core/scene3d_data.py. Se mantienen las clases/funciones físicas reexportadas desde modelo_con_excel.py.
- Se actualizan cuatro pruebas de fuentes que ya fallaban en el ZIP recibido: las de v25 eran incompatibles con el contrato posterior de v26; las de indicadores solares apuntaban a un shim y una ubicación/constante histórica. Las comprobaciones del panel ahora construyen controles simulados y verifican geometría y modos, sin modificar el diseño vigente.
- Se normalizan los separadores de .gitignore, conservando sus exclusiones.

## Base actual recibida

Versión declarada de aplicación v35.6-etapa3.2, registro sombra-science/1.2, modelo avanzado advanced_radiative_v2. Esos identificadores científicos y sus archivos se preservan sin sustituirlos por el v1 de otra entrega. Véanse las notas históricas originales en cambios/.
