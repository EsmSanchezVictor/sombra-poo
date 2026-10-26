# Cambios v8 — Hover Tmrt + temperatura local del aire estimada

## 1. Nueva variable: temperatura del aire local estimada bajo sombra

Se agregó a `shadow_temp.py` un modelo empírico, conservador y acotado que NO convierte Tmrt en temperatura del aire.

La estimación usa la reducción local de radiación solar respecto a pleno sol:

    ΔTa_local = min(ΔTa_max, c_air * (GHI - GHI_efectiva))
    Ta_local = Ta_referencia - ΔTa_local

Valores por defecto:

- árbol: c_air = 0.0025 K/(W/m²), descenso máximo = 2.5 °C;
- estructura: c_air = 0.0012 K/(W/m²), descenso máximo = 1.2 °C.

Estos parámetros son deliberadamente moderados y deben considerarse calibrables si se dispone de mediciones microclimáticas locales.

## 2. Cuadro interactivo de la curva de nivel

El hover ahora muestra solamente:

- Tmrt local;
- T aire local estimada;
- sombra local;
- radiación efectiva local.

Se eliminaron:

- coordenadas X/Y;
- T aire de referencia;
- ΔTmrt respecto a pleno sol.

## 3. Tooltip siempre dentro del mapa

El cuadro usa coordenadas relativas al área de datos y se ubica automáticamente en el cuadrante opuesto al cursor. De este modo permanece dentro de la imagen y no invade los ejes.

El clic izquierdo fija realmente el punto. El clic derecho lo libera.

## 4. Título de la curva

Se eliminó el nombre del archivo/imagen del título de la gráfica. El archivo guardado conserva su nombre normal para historial y exportación.

## 5. Escala térmica

La colorbar continúa representando Tmrt y usa el mínimo y máximo reales del mismo `tmrt_map` consultado con el mouse. La nueva temperatura local del aire es una variable adicional del tooltip y no cambia la escala de colores de Tmrt.

## Validación

Suite: 78 tests aprobados, 5 omitidos por dependencia opcional de pvlib no instalada en el entorno de prueba.
