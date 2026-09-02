# Plan científico — estado final de desarrollo v16

## Desarrollo de software completado

1. Correcciones físicas e integración base — completado.
2. Modelo Tmrt dual — completado.
3. Calibración y validación científica — completado.
4. Cobertura vs. atenuación de sombra — completado.
5. Balance energético avanzado de superficies — completado.
6. Materiales opacos y transmisivos — completado.
7. Vegetación, fenología y evapotranspiración — completado.
8. Meteorología observada y fuentes radiativas explícitas — completado.
9. Incertidumbre operativa y reporte científico — completado.
10. Auditoría integral, consolidación y trazabilidad metodológica — completado en v16.
11. Protocolo y plantilla de validación de campo — completado en v16.

## Único bloque pendiente para afirmar validación científica

### Campaña experimental externa

Requiere datos reales y no puede sustituirse por programación.

Tareas:

- ejecutar campaña según `PROTOCOLO_VALIDACION_CAMPO_v16.md`;
- cargar los datos con `data/plantilla_validacion_termica.csv`;
- separar calibración/validación;
- comparar Estándar, Estándar calibrado y Avanzado;
- validar Ta local;
- validar temperatura superficial;
- validar cobertura de sombra;
- documentar sensores e incertidumbres;
- decidir qué parámetros pasan de “default” a “calibrados”.

## Refinamientos posteriores opcionales

No bloquean la campaña:

- SVF 3D;
- onda larga direccional;
- polígonos espaciales de coberturas;
- LAI/Kc específicos por especie;
- EPW/NetCDF;
- modelos transitorios de almacenamiento;
- perfiles instrumentales automáticos;
- CFD/acoplamiento con modelos microclimáticos externos.

## Criterio de cierre

El proyecto puede considerarse **desarrollo técnico completo y listo para validación** cuando la auditoría interna no presenta fallas.

Puede considerarse **validado para un dominio de uso** solamente después de una campaña independiente que informe explícitamente métricas, rango de condiciones y limitaciones.
