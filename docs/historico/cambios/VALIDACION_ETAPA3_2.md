# Validación — v35.6-etapa3.2

2026-10-05, Linux x86_64 / Python 3.12.14. Entorno aislado limpio de QA de Etapa 3, sin paquetes del sistema, con requirements-qa-linux-py312.lock. `pip check`: sin dependencias rotas. Nuevo requisito explícito tzdata ya estaba presente en ese lock.

| Ejecución | Resultado |
|---|---|
| Suite completa | 532 aprobadas; cero fallos y omisiones |
| Fallback con pvlib/pythermalcomfort bloqueados | 523 aprobadas / 9 omitidas por opcionales |
| Reproducción sobre Etapa 3.1 preservada | 6 fallos: ambos motores ante hora inexistente/ambigua, CSV con offsets repetidos y ranking avanzado sin contexto |
| Mismos seis casos sobre Etapa 3.2 | 6 aprobados |

Comando principal: `python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider`.
Fallback: `python test/run_optional_fallback.py`.
Reproducción independiente: `python -m pytest -q -p no:cacheprovider test/repro_stage3_2.py`.

79 pruebas nuevas de suite: transiciones New York/Lord Howe/Apia, límites de cambio, folds explícitos, horas 24 y fin de año, fechas/rangos inválidos, motor pvlib/fallback, CSV con offsets diferentes e interpolación UTC, carga fallida que conserva la serie, procedencia y coherencia temporal capturada, compatibilidad ordinaria de escenario anterior, rechazo visible en callbacks/mapas, aislamiento Simple/Avanzado, elección de escena, radiación observada/manual cero, comparación real contra mapas Tmrt, área acotada, precisión de orden, geometría, exportación JSON y bloqueo de exportación tras error.

El flujo del diálogo usa widgets simulados y gráfico real Agg; no equivale a una revisión visual de Tk. La suite conserva las pruebas de persistencia y de rechazo Windows simulado de fsync sobre descriptor de sólo lectura de Etapa 3.1. No ejecutamos Windows real, VTK visual, instalador, CI remoto ni trabajo prolongado.

Sintaxis de Python comprobada por AST; SHA256 de fuentes y conservación de Etapa 3.1 verificados. Los tres ZIP pasan testzip; cada parche reconstruye byte a byte los archivos suministrados en el completo desde su base declarada. Se mantienen intactos guardado/recovery, autenticación y el controlador VTK. La captura temporal es aditiva y no migra esquemas de proyecto.

No hay mediciones reales nuevas ni calibración de campo. El ranking sigue usando las aproximaciones geométricas y radiativas existentes. Estas pruebas comprueban consistencia y regresión, no exactitud científica en campo.

Referencias primarias para la política temporal: https://docs.python.org/3.12/library/zoneinfo.html y https://peps.python.org/pep-0495/ . Las dos ocurrencias de una hora repetida tienen offsets distintos; construir un datetime con tzinfo no valida por sí solo todas las horas de pared.
