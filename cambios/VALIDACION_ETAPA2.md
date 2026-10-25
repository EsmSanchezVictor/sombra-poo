# Validación — v35.6-etapa2

Fecha: 2026-10-04. Plataforma: Linux, Python 3.12.14.

## Evidencia automática

- Etapa 1 sin modificar, con las dependencias científicas opcionales instaladas: **290 aprobadas** (antes eran 285 aprobadas/5 omitidas sin pvlib).
- Etapa 2: **377 aprobadas**, 0 fallos, 0 omitidas, sin advertencias en la ejecución final. Incluye **87 casos nuevos** en test/test_stage2_science.py.
- Ruta degradada con importación de pvlib/pythermalcomfort deshabilitada en un proceso separado: **371 aprobadas, 6 omitidas**. Cinco comparaciones pvlib y una prueba real de UTCI requieren las dependencias opcionales. Es una simulación de ausencia de las dependencias, no una instalación limpia de Windows.
- Comando principal: `python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider`.
- PRUEBAS_ETAPA2.txt y PRUEBAS_ETAPA2_FALLBACK.txt contienen la salida de las ejecuciones finales; el manifiesto registra versiones efectivas y SHA256 de fuentes.
- Análisis sintáctico de todos los archivos Python. Integridad de ambos ZIP comprobada, y comparación byte a byte del reemplazo reconstruido contra la carpeta final.

## Cobertura nueva

Año real y DST, bisiestos y fecha Excel; observadores de fecha; aislamiento de selectores y campos ocultos Simple/Avanzado; viento numérico/categorías y altura; observaciones sin mutación de controles; coherencia punto/mapa/sensibilidad con tolerancia por el redondeo histórico del punto a 0.01 °C; motor solar y componentes; límites y presentación de UTCI con pythermalcomfort real; cobertura inválida en mapas; entradas de globo y solver; convergencia/clipping; carga de matrices; exportación de contexto; barrido horario con metadatos. Se ejecutaron los renderizadores reales de Edición y Modelo con FigureCanvasAgg en lugar del canvas Tk para comprobar acuerdo numérico y metadatos.

El test de cableado previo test_v34_advanced_modes.py se actualizó para reconocer el resolver común. Sus comprobaciones visuales existentes se conservan. La prueba funcional del resolver está en el archivo nuevo.

## Límites de la evidencia

No se ejecutó la interfaz Tk real ni VTK en pantalla, ni Windows, instalador, pruebas de memoria prolongadas o mediciones de campo. El canvas Agg comprueba la integración numérica, no la experiencia visual. Python 3.12 no cubre todos los avisos SQLite de Python 3.13. Los horarios locales ambiguos/inexistentes por cambios estacionales requieren revisión específica: este bloque comprobó offsets de años y fechas válidas, no una política completa de desambiguación de horas locales. Se conservan las aproximaciones empíricas y no se afirma exactitud predictiva local.

Estado: candidato Etapa 2 con regresión automática aprobada. No se presenta como distribución final ni modelo calibrado en campo.

## Fuentes metodológicas consultadas

- pythermalcomfort (documentación/código UTCI): https://pythermalcomfort.readthedocs.io/en/stable/_modules/pythermalcomfort/models/utci.html
- pvlib (cielo claro): https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/clearsky.html

La máscara UTCI reproduce los extremos inclusivos de la implementación valid_range de pythermalcomfort comprobada; viento a 10 m. Rangos operativos: Ta [-50,50] °C, Tmrt-Ta [-30,70] °C, viento [0.5,17] m/s; RH física [0,100]%. Una radiación de cielo claro modelada no se etiqueta como medición.
