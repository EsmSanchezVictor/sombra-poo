# Reemplazo v17

Base recomendada: proyecto integrado v16.

## Archivos nuevos

- `services/analysis_record_store.py`
- `test/test_analysis_record_store.py`

## Archivos modificados

- `ui/app_ui.py`
- `services/snapshot_service.py`
- `services/analysis_service.py`
- `core/project.py`
- `core/app_state.py`
- `core/model_registry.py`

Copiar los archivos respetando la estructura de carpetas.

La primera vez que se abra un proyecto antiguo, v17 creará automáticamente:

`<proyecto>/datos/analisis.sqlite3`

y migrará los snapshots formales existentes. No es necesario crear ni editar la base manualmente.

No borrar el archivo `.sombra`: se mantiene como índice y compatibilidad del proyecto.
