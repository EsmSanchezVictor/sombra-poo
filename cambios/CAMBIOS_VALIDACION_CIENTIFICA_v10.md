# v10 — Calibración y validación científica

## Objetivo
Convertir el validador CSV previo en una herramienta reproducible para comparar el modelo **Estándar** y el **Avanzado v1** contra mediciones de campo sin mezclar silenciosamente calibración y validación.

## Implementado

### 1. Dataset de campaña flexible
El lector reconoce aliases de:
- Tmrt observada o temperatura de globo
- temperatura del aire
- GHI, DNI y DHI
- viento y humedad relativa
- fecha/hora, latitud/longitud y zona horaria
- elevación solar
- porcentaje de sombra / transmitancia
- temperatura del aire local bajo sombra
- tipo de sombra y especie
- columna `conjunto` para separar `calibracion` y `validacion`

### 2. Partición científica
- Si el CSV trae `conjunto=calibracion/validacion`, se respeta esa separación.
- Si no existe, con al menos 5 observaciones se genera un holdout interno reproducible.
- Con menos de 5 observaciones se informa que no existe validación independiente.

### 3. Comparación de modelos
Sobre el conjunto de validación se calculan:
- Estándar con k actual
- Estándar con k calibrado en el conjunto de calibración
- Avanzado v1

Métricas:
- MAE
- RMSE
- sesgo
- R²
- n

### 4. Calibración del modelo Estándar
El ajuste ahora usa radiación efectiva:

`GHI_efectiva = GHI * tau`

El k aplicable se estima con regresión forzada por el origen, coherente con la ecuación Estándar.
También se calcula una regresión libre diagnóstica:

`DeltaTmrt = b + k * GHI_efectiva`

El intercepto `b` se informa para detectar sesgo estructural, pero no se aplica automáticamente.

### 5. Calibración de Ta local bajo sombra
Si hay al menos 3 observaciones `ta_local` de un mismo tipo de sombra, se calibra el coeficiente empírico de enfriamiento con el tope térmico actual fijo:
- árbol: máximo 2.5 °C
- estructura: máximo 1.2 °C

La aplicación del coeficiente es explícita y queda registrada en settings.

### 6. Trazabilidad del Avanzado
- usa DNI/DHI observados si están presentes;
- si faltan, los estima a partir de GHI y lo informa;
- usa elevación solar observada si existe;
- si no, intenta calcularla con fecha/hora/ubicación;
- si faltan datos suficientes, esa fila no se incluye en la métrica Avanzada y se informa.

### 7. Exportación de auditoría
El diálogo exporta un XLSX con:
- `Resultados`
- `Metricas`
- `Calibracion`
- `Metadatos`

### 8. Plantilla de campaña
Se puede generar desde el diálogo y también queda disponible en:
`data/plantilla_validacion_termica.csv`

## Compatibilidad
El modo Estándar sigue siendo el predeterminado. Ninguna calibración se aplica automáticamente.
