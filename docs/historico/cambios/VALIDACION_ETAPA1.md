# Validación de Proyecto Sombra v35.6-etapa1

Fecha: 2026-10-04. Base: ZIP v35.6 recibido, SHA256 b9c32aef095d2c494304b4ad188bf150098edb1c9fa4bf5f9c9d259af523653d.

## Pruebas ejecutadas

- Baseline sin cambios: 224 aprobadas, 5 omitidas.
- Versión Etapa 1: **285 aprobadas, 5 omitidas**, 0 fallos, 0 advertencias en la ejecución estricta.
- 61 casos nuevos de autenticación e integridad. Tres archivos de pruebas anteriores actualizan solo contraseñas de sus fixtures para cumplir el mínimo nuevo; las comprobaciones originales se conservan.
- Las cinco omitidas son comparaciones solares con pvlib, que no está instalado en este entorno.
- Comando: `python -m pytest test/ -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider`.
- Python 3.12.14, Linux. Se usó OpenCV headless para pruebas; requirements.txt conserva OpenCV de escritorio.
- Análisis sintáctico de todos los archivos Python y revisión de las funciones cambiadas.

## Evidencia de alcance

Conservan exactamente los bytes de v35.6: modelo_con_excel.py, diseno.py, shadow_temp.py, services/solar_engine.py, core/surface_energy.py, core/vegetation.py, core/thermal_comfort.py, ui/scene3d.py y core/crown_shapes.py.
En core/species.py y core/scientific_audit.py solo cambia la escritura de JSON, no el cálculo.
En ui/app_ui.py solo cambia la resolución de rutas al restaurar miniaturas/snapshots.

## Limitaciones reales

- No se ejecutó una prueba gráfica Tk: el servidor gráfico virtual disponible no pudo inicializarse en este entorno. Los tests de UI existentes incluyen inspección del código, no sustituyen una prueba visual.
- No se ejecutó la aplicación en Windows. Comprobar allí el alta inicial, login, recuperación administrativa, gestión e historial, abrir/guardar/importar, carrusel y animación 2D/3D.
- Python 3.12 no emite todos los avisos de cierre SQLite incorporados en Python 3.13. Se mantuvieron los tests de cierre explícito y bloqueo SQLite, pero no se afirma una ejecución en 3.13.
- La escritura es atómica por archivo JSON. La coordinación transaccional Excel/JSON/SQLite y recuperación multiartefacto sigue en Etapa 3.
- No se implementaron aquí cambios de coherencia científica (Etapa 2), arquitectura/distribución (Etapa 3) ni validación de campo.

Estado: Etapa 1 implementada y con regresión automática aprobada; versión candidata para comprobación local. La base estable original v35.6 se conserva.
