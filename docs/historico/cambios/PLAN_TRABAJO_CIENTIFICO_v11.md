# Plan de trabajo científico — estado v11

## Etapa 1 — Arquitectura dual de Tmrt
**Estado: implementada (v9).**

- Estándar empírico como predeterminado.
- Avanzado radiativo como opción.

## Etapa 2 — Calibración y validación
**Estado: implementada (v10).**

- MAE, RMSE, sesgo, R².
- Separación calibración/validación.
- k_factor calibrable sin aplicación automática.
- Ta local bajo sombra calibrable.

## Etapa 3 — Cobertura vs intensidad de sombra
**Estado: implementada (v11).**

- Cobertura geométrica fotográfica separada de atenuación óptica.
- Máscara sombra/sol reproducible.
- Transmitancia local por píxel.
- Tmrt alimentada por transmitancia, no por oscuridad interpretada como área.
- Persistencia e informes con ambas magnitudes.

## Etapa 4 — Balance energético avanzado de superficies
**Próxima.**

Objetivo: evolucionar el Panel 4 desde el balance estacionario linealizado hacia un balance energético opcional más físico, manteniendo el actual como modo estándar.

Subetapas propuestas:

1. Resolver Stefan–Boltzmann no lineal sin aproximar `h_r` en Ta.
2. Separar radiación de onda corta y onda larga.
3. Incorporar temperatura radiativa de cielo/entorno mediante un modelo explícito.
4. Incorporar flujo al suelo/almacenamiento con parámetros simples.
5. Incorporar término de calor latente/evapotranspiración para vegetación como módulo opcional.
6. Validar contra temperatura superficial observada.

## Etapa 5 — Especies y fenología
Pendiente.

## Etapa 6 — Radiación meteorológica/nubosidad real
Pendiente.

## Etapa 7 — Materiales transmisivos
Pendiente.

## Etapa 8 — Incertidumbre y reporte científico final
Pendiente.
