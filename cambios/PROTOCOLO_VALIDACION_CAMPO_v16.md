# Protocolo de validación de campo — v16

## 1. Objetivo

Validar por separado los principales resultados del software:

- Tmrt al sol y bajo sombra;
- temperatura del aire local estimada bajo sombra;
- temperatura superficial;
- cobertura de sombra obtenida por fotografía;
- efecto de vegetación/evapotranspiración.

La campaña debe separar **calibración** y **validación** para evitar evaluar un modelo con los mismos datos utilizados para ajustarlo.

## 2. Diseño mínimo recomendado

No existe un número universal de observaciones que garantice validez. Para una campaña piloto se recomienda obtener observaciones repetidas y distribuidas en:

- mañana;
- mediodía;
- tarde;
- pleno sol;
- sombra ligera;
- sombra media;
- sombra densa;
- al menos una estructura artificial de sombra;
- diferentes tipos de superficie.

Conviene repetir condiciones en más de un día y, si es posible, bajo diferentes estados de humedad y viento.

## 3. Variables a medir

### Meteorología

- fecha y hora local;
- zona horaria IANA;
- temperatura del aire de referencia;
- humedad relativa;
- velocidad del viento;
- GHI;
- DNI y DHI cuando sea posible;
- nubosidad o condición del cielo.

### Radiación / Tmrt

Preferencia:

1. Tmrt obtenida mediante instrumentación radiométrica, o
2. temperatura de globo con:
   - diámetro real;
   - emisividad real;
   - velocidad de aire medida a la altura del globo.

No se debe asumir que un globo distinto de 150 mm tiene la misma respuesta instrumental.

### Sombra

- fotografía original sin filtros;
- área de referencia iluminada;
- cobertura de sombra manual de control cuando sea posible;
- cobertura calculada por el software;
- atenuación calculada;
- especie o tipo de estructura.

### Superficie

- temperatura superficial observada;
- material/tipo de superficie;
- estado seco/húmedo;
- disponibilidad hídrica del suelo cuando se use el modelo de vegetación.

### Vegetación

- especie;
- altura;
- diámetro o radio de copa;
- condición fenológica;
- LAI medido o bibliográfico si está disponible;
- estado hídrico aproximado.

## 4. Alturas y simultaneidad

Las variables que se comparan deben corresponder al mismo intervalo temporal.

Registrar siempre:

- altura del sensor de aire;
- altura del anemómetro;
- altura del globo/radiómetro;
- orientación y exposición del sensor.

Para comparaciones de confort peatonal, mantener una geometría de medición consistente entre puntos al sol y bajo sombra.

## 5. Estructura del CSV

La plantilla v16 contiene:

`id, conjunto, fecha, hora, lat, lon, timezone, ta, rh, viento, ghi, dni, dhi, elevacion_solar, sombra_pct, tipo_sombra, tau_sombra_total, tmrt, tg, globe_diameter_m, globe_emissivity, ta_local, especie, surface_temp_c, surface_type, soil_water_fraction`

### Columna `conjunto`

Usar explícitamente:

- `calibracion`
- `validacion`

La aplicación respetará esa separación.

## 6. Secuencia de medición por punto

1. Registrar ID, lugar, fecha y hora.
2. Registrar meteorología de referencia.
3. Medir el punto al sol o bajo sombra.
4. Registrar Tg/Tmrt y viento en el mismo período.
5. Registrar Ta local cuando corresponda.
6. Medir temperatura superficial.
7. Tomar fotografía de sombra sin cambiar exposición de manera deliberada entre referencia y área analizada.
8. Registrar especie, superficie y estado hídrico.
9. Repetir.

## 7. Control de calidad

Antes de aceptar una fila:

- hora válida 0–24;
- RH entre 0–100 %;
- viento no negativo;
- irradiancias no negativas;
- diámetro de globo > 0;
- emisividad de globo entre 0 y 1;
- cobertura entre 0–100 %;
- zona horaria correcta;
- coherencia aproximada `GHI ≈ DNI·sin(elevación)+DHI` cuando las tres son medidas.

Las discrepancias radiométricas no deben corregirse silenciosamente: deben quedar como advertencia.

## 8. Métricas

Para Tmrt, Ta local y temperatura superficial informar al menos:

- n;
- MAE;
- RMSE;
- Bias;
- R² cuando corresponda;
- distribución del error.

No usar R² como única medida de desempeño.

## 9. Criterio de comparación de modelos

Comparar:

1. Estándar con `k` original;
2. Estándar calibrado solo con el conjunto de calibración;
3. Avanzado.

Las métricas finales deben calcularse sobre el conjunto de validación.

## 10. Registro metrológico

Para cada instrumento documentar:

- marca/modelo;
- variable medida;
- resolución;
- exactitud declarada;
- rango;
- fecha de calibración/verificación;
- altura de instalación.

Cuando estos datos estén disponibles, deben reemplazar los supuestos genéricos del Monte Carlo operacional.

## 11. Resultado esperado

La campaña permitirá decidir con datos:

- si `k=0.04` debe mantenerse o cambiar;
- qué modelo Tmrt reproduce mejor las observaciones;
- si el tope de enfriamiento de Ta local es adecuado;
- cuánto error tiene el algoritmo fotográfico;
- qué parámetros de vegetación requieren calibración específica.
