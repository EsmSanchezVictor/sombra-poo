# v11 — Etapa 3: cobertura e intensidad de sombra separadas

## Objetivo
Separar dos magnitudes que en versiones anteriores podían confundirse:

1. **Cobertura de sombra (%)**: fracción de píxeles válidos clasificados como sombra.
2. **Atenuación en sombra (%)**: reducción fotométrica relativa dentro de los píxeles clasificados como sombra, respecto del área de referencia iluminada.

Los niveles de gris de una fotografía no se presentan como una medición radiométrica certificada. La atenuación es una estimación fotométrica relativa y queda identificada como tal.

## Nuevo flujo fotográfico
`ImageProcessor.analizar_sombra_fotografica()` devuelve:

- `coverage_pct`
- `attenuation_pct`
- `shadow_transmittance`
- `effective_transmittance`
- `effective_attenuation_pct`
- `threshold_ratio`
- `threshold_gray`
- `shadow_mask`
- `local_transmittance_map`
- `local_attenuation_map`
- `legacy_shadow_index_pct` para auditoría/compatibilidad

La clasificación sombra/sol usa Otsu sobre la razón fotométrica `I/I_ref`, con límites conservadores del umbral y control de áreas de bajo contraste. El umbral efectivo queda guardado para reproducibilidad.

## Integración térmica
El mapa térmico ya no recibe un mapa continuo de “porcentaje de sombra” derivado de oscuridad.

Ahora:

- la **cobertura** es binaria localmente: sol/sombra;
- la **intensidad** se expresa mediante una transmitancia óptica local;
- `Temperatura.calculate_tmrt_map()` acepta `transmittance_map_override`;
- el modelo de temperatura de aire local usa la misma transmitancia local;
- para cálculos escalares de una fotografía se utiliza la transmitancia efectiva promedio de la ROI.

El ingreso manual conserva el comportamiento anterior: el usuario ingresa cobertura y el modelo usa la transmitancia de sombra asumida para el tipo de elemento.

## Interfaz
El Panel 2 muestra ahora por separado:

- Cobertura de sombra
- Atenuación en sombra
- Transmitancia efectiva

Se agregó **Ver máscara sombra / sol**, que muestra:

- clasificación sombra/sol;
- mapa de atenuación óptica relativa;
- umbral utilizado;
- transmitancia efectiva.

El hover de la fotografía deja de decir “% sombra” para una intensidad local y pasa a decir **Atenuación fotométrica local**.

El hover de curvas de nivel muestra:

- Tmrt local
- T aire local estimada
- Clasificación: Sombra/Sol
- Atenuación local
- Radiación efectiva

## Persistencia e informes
Los snapshots v11 guardan:

- cobertura
- atenuación
- transmitancia de sombra
- transmitancia efectiva
- umbral relativo
- versión del algoritmo
- máscara sombra/sol exportada

Los informes y Excel de análisis del proyecto distinguen cobertura y atenuación y evitan llamar “datos reales” a magnitudes derivadas/modeladas.

## Compatibilidad
`porcentaje_sombra` se conserva como alias histórico. Cuando proviene del análisis fotográfico v11 representa **cobertura de sombra**, no intensidad de oscuridad.

Los proyectos anteriores siguen cargando utilizando `porcentaje_sombra` como fallback cuando no existe `cobertura_sombra`.

## Validación
Resultado de la suite en el entorno de desarrollo:

- 96 tests aprobados
- 5 omitidos por dependencia opcional de pvlib no instalada
