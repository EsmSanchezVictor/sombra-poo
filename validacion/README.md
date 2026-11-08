# Estado de validación

La revisión vigente es **v35.6-etapa4.3.6**: 628 pruebas y autocomprobaciones de fuente y copia de compilación aprobadas en Linux. La bienvenida, el tema del escritorio, los paneles laterales, Acerca de y el empaquetado todavía deben comprobarse visualmente en Windows. La tabla de abajo conserva el estado de cierre de la etapa4.3.1 y su antecedente.

| Aspecto | Estado | Evidencia |
|---|---|---|
| Regresión y autocomprobación etapa4.3.1 | Aprobadas en Linux | `qa_linux/etapa4.3.1/` |
| Autocomprobación Windows y componentes Tk/VTK etapa4.3 | Aprobadas para esa versión | `windows/2026-10-25_etapa4.3/` |
| Recorrido Windows etapa4.3.1 | Pendiente | [Planilla de recorrido](windows/recorrido_cierre.md) |
| Ejecutable e instalador etapa4.3.1 | Perfil disponible; binarios pendientes de generación y prueba en Windows | [Guía de compilación](../COMPILAR_WINDOWS.md) |
| Fotografías reales anotadas | Pendiente | `fotos/manifest.plantilla.json` |
| Campaña térmica instrumental | Pendiente | [Plan de campo](../docs/VALIDACION_CAMPO.md) y `campo/plantillas/` |

`estado_actual.json` contiene el estado de esta versión. Los archivos de la 4.3 y anteriores son antecedentes; no prueban la aprobación del recorrido completo ni del instalador actual. Registrá los informes nuevos con fecha, versión y equipo, sin sobrescribir los históricos.
