# CONTEXTO PROYECTO SOMBRA v35.3

Versión base: **v35.2**.

## Estado heredado
v35.2 contiene:
- animación diurna 2D;
- animación diurna 3D VTK en viewport persistente;
- cámara estable entre fotogramas;
- Sol dinámico y capa de sombra 3D;
- corrección de reducción progresiva de los paneles 2D;
- frames 2, 3, 4 y 5 sin borde visible;
- indicador solar 2D/3D.

## Cambio v35.3
Se corrige el ciclo de vida de las conexiones SQLite de `AnalysisRecordStore`.

Principio obligatorio desde esta versión:
**cada conexión de corta duración debe cerrarse explícitamente en `finally`/context manager propio.**

No volver a usar `with sqlite3.connect(...) as conn` o `with self._connect() as conn` suponiendo que ese bloque cierra la conexión; el context manager de sqlite3 controla la transacción, no el cierre.

La conexión de larga duración de `DatabaseManager` sigue siendo válida durante la vida de la aplicación, pero debe cerrarse con `DatabaseManager.close()` al terminar. `main.py` ya garantiza esa llamada en `finally`.

## Validación
- 212 tests aprobados.
- 5 tests omitidos por dependencias/condiciones opcionales.
- suite completa ejecutada con `ResourceWarning` elevado a error: sin advertencias de recursos.

## Próximo criterio de desarrollo
Mantener v35.3 como nueva base estable para cambios posteriores, salvo que se retome explícitamente la rama de auditoría integral v36.
