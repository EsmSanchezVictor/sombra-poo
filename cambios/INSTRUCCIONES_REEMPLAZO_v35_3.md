# Reemplazo v35.2 → v35.3

Cerrar Proyecto Sombra antes de copiar los archivos.

Reemplazar:

- `services/analysis_record_store.py`
- `database_manager.py`

Opcionalmente, si se mantiene la carpeta de tests:

- `test/test_v35_3_sqlite_cleanup.py` (nuevo)
- `test/test_validation_scientific.py`

Después iniciar normalmente la aplicación.

No hay migración de datos ni cambios de esquema SQLite en esta versión.
