# Instrucciones — v19

## Recomendado

Usar directamente `proyecto_sombra_integrado_v19.zip` como nueva base.

La v19 cambia la estructura de carpetas de los proyectos, por lo que es preferible conservar una copia del proyecto anterior antes de abrirlo por primera vez con esta versión.

## Si se reemplazan archivos manualmente

Copiar respetando las rutas internas del paquete de reemplazo. Los principales cambios están en:

- `core/project_layout.py`
- `core/project.py`
- `core/project_manager.py`
- `core/app_state.py`
- `core/scientific_audit.py`
- `services/analysis_record_store.py`
- `services/snapshot_service.py`
- `services/report_service.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `ui/menu_bar.py`
- `ui/panels.py`
- `DatasetSaver.py`
- `diseño.py`
- `modelo_con_excel.py`
- `save_pdf.py`
- `utils.py`

## Primera apertura de un proyecto anterior

La migración es automática. Los archivos que puedan identificarse con seguridad se reubican. Los sobrantes antiguos se conservan en `_legacy_v18/` para revisión y no forman parte del estado vivo.

Después de la primera apertura conviene pulsar una vez **Guardar respaldo**. Esto crea un `.3es` de la estructura ya migrada dentro de `respaldos/`.

## Flujo v19

1. Crear o abrir proyecto.
2. Trabajar normalmente: el proyecto se autosalva.
3. `Ctrl+S` crea un respaldo local sin preguntar destino.
4. `Guardar como…` solo cuando se desea crear otro proyecto/copia en otra ubicación.
5. `Exportar .3es…` solo para sacar una copia portable fuera de la carpeta del proyecto.
