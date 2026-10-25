# Continuidad actual — v35.6-etapa3.2

Última base de trabajo: Etapa 3.2. Etapa 3.1 y v35.6 originales preservadas. Aplicación y release científico v35.6-etapa3.2; schema científico sombra-science/1.2 y escenario efectivo 2. IDs de ecuaciones sin cambios. Leer primero CAMBIOS_ETAPA3_2.md, INSTRUCCIONES_ETAPA3_2.md y VALIDACION_ETAPA3_2.md; contextos previos siguen como historia.

Cerrado por código: horas locales ambiguas/inexistentes rechazadas explícitamente sin shift_forward/NaT silencioso, instantes con offset/fold preservados, CSV repetido e interpolación UTC, captura temporal reproducible y ranking coherente con el escenario Tmrt efectivo. UI elige una única escena; no fusiona Edición/Modelo. Ranking potencial individual en dominio fijo centrado en (0,0), no aporte marginal de una escena con solapes ni modelo de evapotranspiración.

Pruebas finales Linux/Python 3.12.14: 532 aprobadas; fallback simulado 523 aprobadas/9 omitidas. Son 453 anteriores + 79 nuevas. Reproducción independiente: seis fallos antes / seis aprobados después; no sumarlos a los 532. Widgets de diálogo simulados + gráfico Agg, no Tk visual.

La corrección Windows fsync r+b de Etapa 3.1 está incluida y sus módulos no cambiaron. Confirmación del usuario en Windows aún pendiente; no afirmar que ya funciona allí. Las generaciones automáticas cubren JSON/Excel/SQLite; fotos/mapas se controlan por hash y sus versiones históricas requieren respaldos .3es. No borrar journals/cuarentenas.

Próximos pendientes, en orden:
1. Control Windows real: guardar con respaldo, reabrir, importar/exportar/copiar y revisar logs.
2. Prueba visual de todos los paneles, Tk/VTK/fallback y uso prolongado/memoria en Windows.
3. Cerrar distribución: dependencias/lock de producción Windows, ejecutar CI allí y empaquetar instalador/actualizaciones. Hay CI y lock de QA Linux de etapas anteriores, no CI remoto ejecutado ni instalador probado.
4. Validación de campo: Tmrt, temperatura del aire local bajo sombra, geometría/copa, viento a alturas conocidas y vegetación/ET. Calibrar con datos reales y validación independiente.
5. Refactor adicional incremental de app_ui.py/scene3d.py, conservando flujos y pruebas; no reescribir todo.

No llamar a la aplicación distribución final validada en Windows ni modelo calibrado por estos tests. Mantener nuevas entregas acumulativas, contexto, instrucciones, SHA256 y fuentes anteriores intactas.
