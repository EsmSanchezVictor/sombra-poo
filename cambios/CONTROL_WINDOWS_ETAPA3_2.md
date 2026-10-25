# Control pendiente en Windows — v35.6-etapa3.2

Estado: **NO EJECUTADO** en Windows real. Este documento es una guía para registrar evidencia, no un certificado ni un resultado automático.

Trabajar sobre una copia de un proyecto con imagen, árboles y estructuras. Registrar Windows/Python, versión de aplicación, motor pvlib/UTCI instalado, GPU/VTK y escala de pantalla.

| Control | Resultado esperado | Resultado real |
|---|---|---|
| Guardar con respaldo, cerrar y reabrir | Sin Errno 9; JSON/Excel/SQLite recuperan el mismo estado | Pendiente |
| Copiar proyecto, exportar .3es, importar en otra carpeta | Proyecto íntegro y fotos/mapas presentes | Pendiente |
| Cerrar/reabrir mientras alterna modos y paneles | Sin pérdida de estado ni bloqueo | Pendiente |
| Tmrt Simple/Avanzado y mapas | Fuente/modelo/fecha coherentes con controles | Pendiente |
| Ranking Edición/Modelo, exportar JSON | Una escena, árboles identificados, modelo y procedencia correctos | Pendiente |
| Zona New York, 2024-03-10 02:30 y 2024-11-03 01:30 | Rechazo claro sin mover hora ni generar resultado nuevo | Pendiente |
| CSV hora repetida con offsets -04:00/-05:00 | Dos observaciones distintas | Pendiente |
| Abrir/cerrar 3D VTK y fallback disponible | Interacción/cierre normales, diagnóstico visible si falla VTK | Pendiente |
| Uso prolongado y repetición de gráficos/3D | Sin crecimiento persistente de recursos ni cierres inesperados | Pendiente |

Para la regresión automatizada desde la carpeta con main.py, en un entorno Python 3.12:

```text
python -m pip install -r requirements-full.txt pytest
python -m pip check
python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider
python test/run_optional_fallback.py
```

Conservar stdout/logs y pasos exactos de cualquier fallo. No borrar recuperación ni restaurar una base privada mediante un ZIP de código. El workflow Windows existe pero sólo queda probado al ejecutarlo y revisar sus resultados.
