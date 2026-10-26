# Plan de trabajo científico — v10

## Arquitectura base
- **Estándar / empírico**: predeterminado, rápido, estable y calibrable.
- **Avanzado / radiativo**: optativo, físicamente explícito y progresivamente validado.

La regla se mantiene: una mejora del Avanzado no puede cambiar silenciosamente el Estándar.

## Etapa 1 — Modelo dual + Tmrt radiativa v1
**IMPLEMENTADA EN v9**

- Estándar: `Tmrt = Ta + k * GHI * tau`.
- Avanzado v1: GHI/DNI/DHI, absorptividad, emisividad, geometría corporal y albedo.

## Etapa 2 — Calibración y validación
**IMPLEMENTADA EN v10**

- formato flexible de campaña CSV;
- conversión globo → Tmrt;
- partición explícita calibración/validación o holdout interno reproducible;
- MAE, RMSE, sesgo, R² y n;
- comparación Estándar actual / Estándar calibrado / Avanzado v1;
- ajuste de k con GHI·tau;
- regresión libre diagnóstica para detectar intercepto/sesgo;
- calibración de Ta local bajo sombra cuando existen observaciones;
- exportación XLSX trazable;
- plantilla de campaña.

### Próximo criterio científico
Antes de cambiar defaults, reunir una campaña con validación independiente y comparar modelos sobre esas observaciones.

## Etapa 3 — Sombra fotográfica: cobertura vs atenuación
**PRÓXIMA**

- conservar índice fotográfico actual como intensidad óptica;
- implementar segmentación binaria sol/sombra para cobertura geométrica;
- mostrar por separado cobertura (%) e intensidad/atenuación (%);
- validar contra máscaras manuales de referencia.

## Etapa 4 — Balance de superficies avanzado
Pendiente:
- onda corta y larga;
- convección;
- evapotranspiración;
- flujo al suelo;
- almacenamiento;
- Stefan-Boltzmann no lineal.

## Etapa 5 — Vegetación y especies
Pendiente:
- transmitancia por especie;
- albedo de copa;
- LAI;
- fenología;
- evapotranspiración y disponibilidad hídrica.

## Etapa 6 — Radiación meteorológica
Pendiente:
1. pvlib/Ineichen cielo despejado;
2. radiación manual/medida;
3. datos meteorológicos reales externos.

## Etapa 7 — Materiales y estructuras
Pendiente:
- alpha/rho/epsilon para opacos;
- alpha + rho + tau = 1 para transmisivos;
- temperatura radiativa de paredes/cubiertas;
- factores de vista simplificados.

## Etapa 8 — Incertidumbre y reporte científico
Pendiente:
- versión de modelo;
- fuente solar;
- parámetros calibrados/no calibrados;
- incertidumbre;
- resultados observados vs modelados;
- advertencias metodológicas.
