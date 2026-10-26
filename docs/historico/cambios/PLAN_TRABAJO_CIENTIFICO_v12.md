# Plan científico — estado v12

## Completado

1. Arquitectura dual Tmrt: Estándar / Avanzado.
2. Calibración y validación científica de Tmrt y Ta local.
3. Separación de cobertura de sombra y atenuación óptica.
4. Balance energético avanzado de superficies v1.
7. Biblioteca avanzada de materiales opacos/transmisivos v1.

## Siguiente bloque recomendado

### Etapa 5 — vegetación y evapotranspiración

Incorporar de forma optativa al balance avanzado:
- flujo latente `LE`
- disponibilidad hídrica / humedad de suelo
- LAI
- resistencia de copa/superficie
- fenología y condición caducifolia
- transmitancia/albedo específicos por especie

Mantener `LE=0` cuando no existan datos suficientes y marcar la limitación.

### Etapa 6 — fuentes radiativas y meteorológicas

Separar explícitamente:
- pvlib cielo despejado
- radiación manual/medida
- archivo meteorológico observado
- nubosidad estimada

Registrar la fuente en cada resultado.

### Etapa 8 — incertidumbre y reporte científico

Incorporar:
- intervalos/incertidumbre de parámetros
- propagación simplificada o Monte Carlo optativo
- RMSE/MAE/Bias/R2/n en reportes
- calidad/fuente de cada input
- versión completa del modelo

## Nota metodológica

La v12 no activa automáticamente física más compleja. El Estándar sigue siendo
el modo predeterminado. El Avanzado solo mejora el rigor cuando los inputs son
suficientes y sus supuestos quedan documentados.
