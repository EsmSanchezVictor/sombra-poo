# Cambios — Proyecto Sombra v35.6-etapa3

Entrega acumulativa: Etapas 1, 2 y 3 sobre la base estable v35.6 preservada. Las carpetas de Etapas 1 y 2 se conservan. No se reutiliza v35.7.

## Guardado y recuperación

- `services/project_storage.py` separa persistencia del controlador. Prepara una generación de estado `.sombra`, copia `config/project.json`, escenas de Edición/Modelo, copia consistente de SQLite mediante su API de backup e inventario SHA256. Si una preparación falla, no publica el conjunto nuevo.
- Publica el journal únicamente después de verificar todos los archivos preparados. La publicación reemplaza cada archivo de forma atómica y deja el índice `.sombra` al final. Un bloqueo reentrante por proyecto impide que los lectores/escritores internos vean un conjunto parcialmente publicado.
- Al abrir, un journal pendiente permite terminar el guardado. Sin journal, los archivos centrales divergentes se preservan en cuarentena antes de restaurar la última generación íntegra. Si ésta está dañada, se intenta la generación anterior verificada. Si ninguna es válida, se detiene la apertura: no se inventan datos.
- Se conservan dos generaciones centrales completas. Las generaciones parciales sin journal se limpian en el siguiente guardado exitoso. La cuarentena no se elimina automáticamente.
- Una base SQLite que cambió después del último guardado del proyecto se conserva en cuarentena antes de recuperar el conjunto central. Esos registros posteriores no se fusionan automáticamente con el estado anterior.
- Archivo temporal, sincronización de archivo y reemplazo también para Excel, NPZ, copias del servicio de snapshots, entradas importadas y ZIP. Los directorios se sincronizan donde el sistema operativo lo permite.
- Un fallo al preparar Excel mantiene el proyecto pendiente de guardar y no actualiza indicadores/rutas a archivos temporales. Si el proyecto quedó guardado pero falla una preferencia auxiliar, el mensaje distingue ambas situaciones. Si falla el respaldo explícito, Guardar devuelve fallo de respaldo y aclara que el estado sí quedó guardado.

## Integridad, copias e importación

- `core/project_integrity.py` registra SHA256, tamaño y modificación de entradas y resultados. La caché en memoria evita volver a leer archivos sin cambios de identidad/tamaño/tiempos del sistema de archivos; la apertura verifica sus bytes.
- Fotos, CSV, mapas y demás artefactos modificados o ausentes se notifican al abrir y el incidente queda en el historial de integridad del proyecto. Al guardar nuevamente se establece el inventario actual sin borrar ese historial.
- Guardar como y Duplicar preparan la carpeta completa antes de publicarla, recrean el inventario y copian SQLite de forma consistente. Rechazan destinos dentro del original, incluidos alias mediante enlaces, y enlaces de archivos/directorios externos.
- Exportación y respaldos `.3es` atómicos, sin respaldos recursivos, locks ni generaciones internas. La importación valida hashes cuando el paquete incluye el inventario nuevo, antes de publicar la carpeta. Los paquetes legacy sin hashes siguen siendo compatibles con las validaciones de rutas de Etapa 1.
- Paquetes `.3es` con controles internos de recuperación se rechazan. El destino de importación/copia queda ausente si la preparación falla.

## Esquemas y diagnóstico

- Esquema de estado 2 con migración explícita, idempotente y conservadora desde 1; formato exterior de proyecto 1 y layout 2 se mantienen. Protocolo de recuperación 1, inventario 1 y análisis SQLite 1 tienen versiones separadas.
- SQLite verifica tanto `PRAGMA user_version` como el marcador histórico antes de configurar, migrar o copiar la base. Los formatos futuros de estado, inventario, análisis y protocolo se rechazan antes de sustituirlos por una generación anterior o publicar otro guardado.
- `core/app_logging.py` añade un registro local rotativo: 1 MiB por archivo, tres rotaciones. Registra fallos de guardado/recuperación/arranque y excepciones de callbacks Tk, sin volcar payloads ni claves de autenticación. Los mensajes pueden contener nombres/rutas de proyecto y detalles de excepciones.
- Versión de aplicación `v35.6-etapa3`, separada de la versión científica `v35.6-etapa2`: esta etapa no cambia las ecuaciones ni afirma una nueva calibración.

## Arquitectura y reproducción

- Servicios separados para serialización de escenas, copia y guardado de proyectos y resolución meteorológica. Se extrajo el backend Matplotlib 3D; el controlador VTK mantiene el mismo AST que Etapa 2.
- Reducción incremental de los módulos principales: `project_manager.py` 627 → 567 líneas; `app_ui.py` 5041 → 4985; `scene3d.py` 1231 → 1114. La interfaz aún es un módulo grande y puede seguir separándose por funciones concretas.
- `requirements-qa-linux-py312.lock` fija las versiones efectivas y transitivas del entorno Linux/Python 3.12 comprobado. Es un perfil de QA con OpenCV headless, alternativo al perfil de escritorio.
- Flujo de GitHub Actions preparado para regresión y ruta sin opcionales en Linux/Windows. No se ha publicado ni ejecutado ese flujo en GitHub; no equivale a una validación Windows.

## Límite de la recuperación

Las generaciones automáticas incluyen estado, escenas e índice SQLite; **no duplican cada fotografía ni cada mapa en cada autosave**. Los artefactos binarios externos a ese conjunto se verifican por hash. Sus versiones anteriores requieren un respaldo `.3es` o una copia conservada. Esto no es una transacción única de todos los artefactos fotográficos ni una garantía probada frente a pérdida física de alimentación.

La seguridad, usuarios y correcciones científicas de las Etapas 1/2 permanecen. Continúan pendientes la revisión visual en Tk/VTK y Windows, política completa de horas locales ambiguas/inexistentes por DST, interpretación del ranking empírico y calibración de Tmrt, Ta local y vegetación con mediciones de campo.
