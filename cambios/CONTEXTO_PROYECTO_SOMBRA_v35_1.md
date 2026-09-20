# CONTEXTO PROYECTO SOMBRA v35.1

## Base estable
La última base estable anterior fue v35. La v36 de seguridad/integridad iniciada después de la auditoría quedó parcial y NO se considera base de release.

v35.1 se reconstruyó desde v34 incorporando los cambios conocidos de v35 (indicador solar) y el parche posterior de bordes invisibles, y agrega la Fase 1 de animación diurna.

## Estado nuevo
El botón **Ejecutar** en Edición/Modelo abre un diálogo de ejecución:
- Instantánea;
- Animación diurna, por defecto.

La animación calcula previamente una serie de estados horarios y luego reproduce los resultados almacenados.

## Fase 1 implementada
- animación 2D;
- sombra efectiva + temperatura superficial;
- indicador solar;
- escala térmica global de toda la secuencia;
- controles de reproducción;
- pasos 15/30/60 min;
- velocidad regulable;
- restauración de parámetros luego del cálculo;
- soporte Edición y Modelo.

## Principio científico
La animación actual es cuasi-estacionaria, no transitoria. No afirmar que modela inercia térmica acumulada entre pasos.

## Siguientes fases previstas
1. Persistencia/exportación de la serie temporal y métricas horarias.
2. Animación 3D VTK con actualización de sol, sombra y capa térmica.
3. Opcional: modelo transitorio real si se justifica científicamente y se valida con datos de campo.

## Validación actual
- 207 passed, 5 skipped.
- integración GUI Edición y Modelo validada bajo Xvfb.
