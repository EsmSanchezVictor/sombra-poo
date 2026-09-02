# Plan de trabajo científico del modelo térmico

## Objetivo general
Mantener un modo **Estándar / empírico** rápido, estable y predeterminado, y desarrollar en paralelo un modo **Avanzado** progresivamente más físico, trazable y validable.

La regla de desarrollo será: ninguna mejora del modelo avanzado debe cambiar silenciosamente los resultados del modo estándar.

## Etapa 1 — Arquitectura de modelo dual + Tmrt radiativa v1 (IMPLEMENTADA EN v9)

### Estándar (predeterminado)
- Conserva `Tmrt = Ta + k * GHI * tau`.
- Conserva calibración mediante `k_factor`.
- Sigue siendo el modo recomendado para uso cotidiano hasta completar la validación del avanzado.

### Avanzado v1
- Balance radiativo humano simplificado.
- Usa GHI, DNI y DHI por separado.
- Parámetros físicos iniciales:
  - absorptividad de onda corta: 0.70
  - emisividad de onda larga: 0.97
  - factor de área proyectada: 0.28
  - factor angular hemisférico: 0.50
  - albedo de suelo: 0.20
- La onda larga cielo/suelo se aproxima inicialmente con temperatura radiativa igual a Ta.
- La transmitancia local se aplica a la onda corta incidente.
- Se registra en resultados qué modelo fue usado.

### Limitaciones explícitas de v1
- No es SOLWEIG ni ENVI-met.
- Aún no calcula SVF tridimensional.
- Aún no separa transmitancia de directo/difuso bajo copa.
- La temperatura radiativa del cielo y del suelo todavía no se modela independientemente.
- Requiere validación de campo.

## Etapa 2 — Calibración y validación de Tmrt y Ta local

1. Formato CSV de campaña de medición:
   - fecha/hora
   - lat/lon
   - Ta
   - RH
   - viento
   - GHI (idealmente DNI/DHI)
   - temperatura de globo / Tmrt observada
   - Ta bajo copa
   - especie / cobertura / LAI si está disponible
2. Separar conjunto de calibración y conjunto de validación.
3. Reportar MAE, RMSE, sesgo, R² y n.
4. Comparar Estándar vs Avanzado con los mismos datos.
5. Calibrar el modelo empírico de Ta local bajo sombra.

## Etapa 3 — Sombra fotográfica: cobertura vs atenuación

- Mantener el índice fotográfico actual como variable óptica.
- Implementar segmentación binaria sol/sombra para obtener cobertura geométrica.
- Mostrar por separado:
  - cobertura de sombra (%)
  - índice de atenuación / intensidad (%)
- Validar máscaras con selección manual de referencia.

## Etapa 4 — Balance de superficies avanzado

Evolucionar el Panel 4 hacia:

`Rn = H + LE + G + S`

- radiación neta de onda corta y larga
- convección
- evapotranspiración
- flujo al suelo
- almacenamiento térmico
- solución no lineal de Stefan-Boltzmann

El modo actual se conserva como balance simplificado.

## Etapa 5 — Vegetación y especies

- transmitancia por especie
- albedo de copa
- LAI
- fenología/caducidad según fecha y hemisferio
- capacidad evapotranspirativa
- disponibilidad hídrica

## Etapa 6 — Radiación meteorológica

Tres fuentes seleccionables y registradas:
1. pvlib/Ineichen cielo despejado
2. radiación manual/medida
3. datos meteorológicos reales externos

Nunca presentar cielo despejado como si fuera una observación meteorológica.

## Etapa 7 — Materiales y estructuras

- materiales opacos: alpha, rho, epsilon
- materiales transparentes/translúcidos: alpha + rho + tau = 1
- temperatura radiativa de paredes/cubiertas
- SVF y factores de vista simplificados

## Etapa 8 — Incertidumbre y reporte científico

- versión del modelo
- fuente solar
- parámetros físicos utilizados
- datos observados vs modelados
- intervalo de incertidumbre
- métricas de validación
- advertencias cuando se usan parámetros no calibrados

## Criterio de adopción
El modelo Avanzado pasará a ser recomendado (no necesariamente predeterminado) cuando supere al Estándar en validación independiente y se disponga de datos suficientes para sus entradas.
