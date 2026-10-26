# Plan de trabajo científico — estado v13

## Implementado
- Correcciones físicas y de integración base.
- Modelo Tmrt dual: estándar + radiativo avanzado.
- Calibración/validación científica.
- Cobertura vs atenuación fotográfica.
- Balance energético no lineal de superficies.
- Materiales opacos/transmisivos.
- Vegetación, fenología y evapotranspiración v2.

## Siguiente bloque recomendado
### Radiación y meteorología observada
- distinguir explícitamente `pvlib clear-sky`, radiación manual y radiación medida;
- importar series meteorológicas;
- modelar nubosidad a partir de datos observados cuando exista;
- registrar la fuente de cada variable y degradar el nivel de confianza cuando sea estimada.

## Cierre científico posterior
### Incertidumbre y reporte
- propagación/sensibilidad de parámetros;
- intervalos de incertidumbre;
- métricas por modelo y por condición;
- calidad/fuente de datos;
- versión del modelo en cada exportación.

## Mejora futura de geometría vegetal
El v13 usa fracción global de suelo vegetado. La evolución natural es permitir polígonos de césped, canteros, suelo desnudo y superficies húmedas para que `LE` sea espacialmente explícito y no global.
