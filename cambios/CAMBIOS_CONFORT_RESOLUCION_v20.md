# v20 — Confort vectorizado y resolución de matriz 64–640

## Objetivo

Esta versión modifica únicamente rendimiento/interfaz del cálculo espacial y la resolución de trabajo. No cambia las ecuaciones de Tmrt, Heat Index, Temperatura Aparente ni UTCI.

## 1. Resolución de matriz

El análisis fotográfico/térmico usa ahora una resolución cuadrada seleccionable entre **64×64 y 640×640**, en incrementos de 32.

- mínimo: 64×64
- predeterminado: **128×128**
- máximo: 640×640

El modo normal usa 128×128. Al activar **Modo avanzado (tamaño de matriz)** se habilita la lista completa.

La resolución seleccionada se guarda en el estado del proyecto y también en cada registro de análisis del carrusel. Al recuperar un árbol, el control vuelve a mostrar la resolución con la que fue analizado.

## 2. UTCI espacial vectorizado

Antes, el mapa de confort llamaba a `pythermalcomfort.utci()` una vez por píxel. Por ejemplo:

- 128×128 = 16.384 llamadas
- 480×480 = 230.400 llamadas
- 640×640 = 409.600 llamadas

v20 agrega `core.thermal_comfort.utci_array()`, que entrega el array completo a pythermalcomfort en una sola llamada cuando la versión instalada admite arrays. Se mantiene un fallback escalar únicamente para compatibilidad con versiones antiguas.

La clasificación de bandas UTCI también se realiza con operaciones NumPy vectorizadas.

## 3. Ventana Confort no bloqueante

La ventana **Confort térmico** se muestra antes de calcular la distribución espacial.

Primero aparecen inmediatamente:

- Tmrt al sol
- Tmrt bajo sombra
- Heat Index
- Temperatura Aparente
- UTCI al sol
- UTCI bajo sombra

Si existe mapa Tmrt, la ventana muestra:

`Calculando distribución espacial UTCI…`

El mapa se procesa en un hilo de trabajo. El hilo no toca Tkinter: entrega el resultado mediante una `Queue`, y el hilo principal actualiza la interfaz.

Al finalizar se informa:

- porcentaje de área por categoría UTCI
- cantidad de celdas procesadas
- tiempo de cálculo

## 4. Memoria

Los mapas se mantienen en `float32`. A 640×640 una matriz ocupa aproximadamente 1,6 MB. El worker de Confort usa una copia compacta del mapa para evitar que un cambio simultáneo de árbol altere el cálculo en curso.

## 5. Compatibilidad

Proyectos previos sin información de resolución se abren con el nuevo valor predeterminado de 128×128. Si un registro del carrusel ya contiene una matriz cuadrada guardada, su dimensión real se usa para restaurar el selector.

Los valores antiguos mayores a 640 se normalizan al máximo permitido de 640.

## 6. Pruebas

Se agregaron pruebas para:

- rango 64–640 e incremento 32;
- default 128;
- normalización de valores heredados;
- llamada UTCI vectorizada única;
- clasificación vectorizada de categorías;
- comportamiento sin pythermalcomfort.

Suite v20: **154 tests aprobados, 5 omitidos**. Los omitidos corresponden a dependencias opcionales de pvlib no instaladas en el entorno de prueba.
