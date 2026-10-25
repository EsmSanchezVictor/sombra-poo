# Validación — v35.6-etapa3

Fecha: 2026-10-04. Plataforma: Linux x86_64, Python 3.12.14.

## Resultados finales

- Etapa 2 preservada: **377 aprobadas** al iniciar el bloque.
- Etapa 3, instalación limpia con el archivo de versiones de QA: **447 aprobadas**, 0 fallos y 0 omitidas. Sin advertencias en la ejecución final. Incluye **70 casos nuevos** en `test_stage3_storage.py` y `test_stage3_integration.py`.
- Mismo entorno, importación de pvlib/pythermalcomfort bloqueada en un proceso separado: **441 aprobadas, 6 omitidas**. Cinco comparaciones requieren pvlib y una prueba UTCI requiere pythermalcomfort. La ausencia de estas bibliotecas se simula; no se instaló un segundo entorno sin ellas.
- Entorno virtual limpio con `include-system-site-packages = false`; instalación mediante `requirements-qa-linux-py312.lock` y `pip check`: sin dependencias incompatibles.
- Comando principal: `python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider`.
- Ruta degradada: `python test/run_optional_fallback.py`.
- Las salidas finales, instalación y comprobación de fuentes se suministran en archivos separados dentro de ambos ZIP. El manifiesto registra versiones y SHA256 de fuentes.

## Fallos ejercitados

Preparación fallida de Excel; publicación detenida después de distintos archivos; terminación real de un proceso hijo mediante `os._exit(77)`; liberación automática del bloqueo; estado principal corrupto y recuperación/cuarentena; SQLite divergente conservado; generación dañada y uso de la anterior; limpieza de parciales y retención de dos generaciones; protocolo/journal falsificado con traversal; falta de un archivo preparado; modificación de fotos; inventarios inválidos y rutas externas; migración idempotente; esquemas futuros JSON/SQLite/inventario/protocolo sin sobrescritura; bloqueo entre procesos; ZIP/copia/importación fallidos sin destino incompleto; enlaces externos y alias del destino; fallo de NPZ/Excel/copias que conserva el archivo anterior; estado de guardado de la UI; respaldo fallido; logs rotativos y excepción de callback.

El test de terminación abrupta comprueba un cierre de proceso. No simula un corte de alimentación, fallos de disco físico ni todos los sistemas de archivos de red.

## Conservación científica y arquitectura

SHA256 confirma que las fuentes Python de v35.6, Etapa 1 y Etapa 2 no se modificaron. Los módulos del motor solar, configuración efectiva, Tmrt, balance superficial, confort, meteorología, geometría solar, registro metodológico y servicios de escenario se conservan respecto de Etapa 2, al igual que Edición/Modelo. Las dos funciones meteorológicas extraídas conservan sus cuerpos AST después de renombrar el argumento `self` por `app`. El AST del controlador VTK no cambia.

Se ejecutó el backend Matplotlib extraído con FigureCanvasAgg y widgets sustitutos: contornos, copa, estructuras, indicador solar, diagnóstico de fallback y cierre del controlador. Comprueba integración funcional sin pantalla, no la interfaz Tk real ni la calidad visual de VTK.

Ambos ZIP se verifican con `testzip`; cada archivo suministrado por el ZIP completo se compara byte a byte contra el resultado de aplicar el reemplazo acumulativo sobre v35.6. No se incluyen bases privadas `users.db`, credenciales, proyectos del usuario, entornos virtuales ni cachés.

## Límites y estado

No se ejecutaron GUI real, Windows, instalador, CI remoto, pruebas prolongadas de memoria ni mediciones de campo. La rama Windows del bloqueo y el flujo CI necesitan ejecución allí. Las versiones de QA se fijan para Linux/Python 3.12; no son un lock de escritorio Windows ni un archivo de hashes de wheels.

La recuperación central no restaura automáticamente versiones anteriores de fotos/mapas sobrescritos. Los cambios binarios se detectan y quedan registrados; para restaurarlos hace falta un respaldo completo.

Se mantienen las limitaciones científicas documentadas en VALIDACION_ETAPA2.md: DST ambiguo/inexistente, altura de viento observada, aproximaciones locales y ranking empírico. Las pruebas sintéticas de calibración no constituyen validación con mediciones reales.

Estado: **candidato v35.6-etapa3 con regresión automática y entorno limpio aprobados**. El cierre de la robustez abordada en este bloque no convierte al modelo en calibrado ni a la aplicación en una distribución final verificada en Windows.
