# Proyecto Sombra v35.3 — cierre correcto de recursos SQLite

Base: **v35.2**.

## Problema
Durante el uso normal podían aparecer advertencias como:

`ResourceWarning: unclosed database in <sqlite3.Connection ...>`

La advertencia se hacía visible al ejecutar `gc.collect()` desde `core/memory_utils.py`, pero esa línea no era el origen del problema: el recolector de basura simplemente encontraba conexiones SQLite que habían quedado sin cerrar.

## Causa
`services/analysis_record_store.py` utilizaba repetidamente:

```python
with self._connect() as conn:
    ...
```

El context manager nativo de `sqlite3.Connection` administra commit/rollback, pero no garantiza el cierre del objeto conexión al salir del bloque.

## Corrección
Se incorporó `AnalysisRecordStore._connection()` mediante `contextlib.contextmanager`.

La nueva secuencia garantiza:

1. apertura de la conexión;
2. ejecución de la operación;
3. `commit()` si finaliza correctamente;
4. `rollback()` si ocurre una excepción;
5. `close()` siempre.

Todas las operaciones internas de `AnalysisRecordStore` usan ahora ese administrador de contexto.

## DatabaseManager
`DatabaseManager.close()` quedó además idempotente:

- puede llamarse más de una vez sin error;
- cierra cursor y conexión;
- elimina las referencias internas (`None`) después del cierre.

`main.py` ya disponía de un `finally` que llama a `db_manager.close()`, por lo que la conexión principal queda cerrada incluso si la aplicación termina por una ruta no habitual.

## Validación nueva
Se agregó `test/test_v35_3_sqlite_cleanup.py` para comprobar:

- múltiples ciclos de alta/lectura/listado/conteo;
- recolección de basura sin conexiones SQLite abandonadas;
- posibilidad de obtener inmediatamente un `BEGIN IMMEDIATE` sobre la base;
- cierre idempotente de `DatabaseManager`.

También se corrigió un test que abría `pd.ExcelFile` sin cerrarlo, para que la validación estricta de recursos no produzca falsos positivos ajenos a SQLite.

## Resultados

- `python -m compileall -q ...` → OK
- `PYTHONPATH=. pytest -q` → **212 passed, 5 skipped**
- `PYTHONPATH=. python -W error::ResourceWarning -m pytest -q` → **212 passed, 5 skipped**, sin ResourceWarning

## Alcance
No se modifican:

- modelos científicos;
- sombras;
- temperatura;
- Tmrt;
- animación 2D/3D;
- formato de datos persistidos.

El cambio es de gestión de recursos y estabilidad.
