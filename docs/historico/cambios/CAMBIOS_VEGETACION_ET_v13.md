# v13 — Vegetación, fenología y evapotranspiración

## Arquitectura
Se conservan tres modos independientes de temperatura superficial:

1. `standard`: balance linealizado histórico. Sin cambios.
2. `advanced`: balance energético seco no lineal v1. Sin cambios.
3. `advanced_vegetation`: balance energético v2 con vegetación y ET.

El modo predeterminado continúa siendo `standard`.

## Evapotranspiración del suelo
El modo v2 incorpora un flujo latente `LE` al balance superficial. El potencial se calcula con la forma horaria de FAO-56 Penman-Monteith y se modula por:

- fracción global de suelo vegetado;
- disponibilidad hídrica;
- actividad foliar equivalente;
- radiación local luego de sombra/estructuras;
- temperatura, humedad y viento.

Los senderos se consideran no vegetados y reciben `LE = 0`.

## Transpiración de copa
La ET de las copas se calcula por separado como diagnóstico. No se resta al balance del suelo porque copa y suelo son superficies físicas diferentes. Cada árbol conserva:

- especie;
- LAI típico;
- Kc de ET;
- fenología;
- disponibilidad hídrica;
- calidad/fuente de los parámetros.

## Fenología
En v2 únicamente, las especies caducifolias modifican su transmitancia estacionalmente mediante un factor fenológico suave dependiente de día del año y hemisferio. Los modos anteriores conservan exactamente la transmitancia histórica.

Los nuevos campos de especie son:

- `lai_tipico`;
- `kc_et`;
- `transmitancia_sin_hojas`.

Las bases antiguas siguen siendo válidas. Si esos campos faltan, se usan defaults genéricos explícitos (`LAI=3`, `Kc=1`) y el diagnóstico marca `generic_default`.

## Preferencias nuevas
En Preferencias se agregan:

- Fracción de suelo vegetado (0–1), default 0.50.
- Disponibilidad hídrica del suelo (0–1), default 0.75.
- Disponibilidad hídrica de copa (0–1), default 0.75.

Estos parámetros solo afectan `advanced_vegetation`.

## Persistencia
Los tres parámetros anteriores y el modo de superficie se guardan en Excel y snapshots. El informe PDF identifica el modelo y los parámetros vegetativos activos.

## Validación
Suite final: 114 tests aprobados, 5 omitidos por dependencia opcional `pvlib` no disponible en el entorno de prueba.
