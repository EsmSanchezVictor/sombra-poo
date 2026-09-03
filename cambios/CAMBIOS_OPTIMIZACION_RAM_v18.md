# v18 — Optimización de memoria RAM y renderizado

La v18 no modifica ecuaciones, parámetros físicos ni resultados científicos. Parte de la v17 y se concentra exclusivamente en consumo de RAM, liberación de recursos gráficos y costo de renderizado.

## Cambios principales

### 1. Una sola copia de la fotografía en RAM
La GUI usa `ImageProcessor.load_image_rgb()` y conserva únicamente `img_rgb`. OpenCV sigue decodificando temporalmente en BGR, pero ese buffer deja de formar parte del estado de la aplicación al finalizar la carga.

La API histórica `load_image()` se conserva para compatibilidad externa, pero ya no la usa `SombraApp`.

### 2. Conversión a gris sin temporal float64
`ShadowDetector._to_gray_array()` reemplaza `np.mean(..., axis=2)` por `cv2.cvtColor(..., COLOR_RGB2GRAY)` para arrays RGB. Así la fotografía no se promociona completa a `float64` durante el análisis automático.

### 3. Figuras Matplotlib temporales liberadas
- La barra Tmrt usa `matplotlib.figure.Figure` en lugar de `plt.figure`.
- La aplicación mantiene una única barra Tmrt y destruye/limpia explícitamente la anterior.
- Los canvases principales de fotografía y Tmrt se crean con `Figure` directo, sin quedar registrados globalmente en pyplot.
- Las vistas 3D de Edición y Modelo cierran su figura al cerrar la ventana.
- Las figuras 2D persistentes de Edición/Modelo se crean con `Figure` directo, sin quedar registradas globalmente en `pyplot`.

### 4. Corrección de recreación duplicada en Modo Edición
`diseño.crear_area_grafico()` en v17 llamaba dos veces a `actualizar_grafico()` y además creaba una figura intermedia. En v18 realiza un único render. `actualizar_grafico()` cierra la figura anterior antes de reemplazarla.

### 5. Mapas de trabajo en float32
Los mapas Tmrt/hover y los mapas fotográficos persistidos se mantienen en `float32` cuando no requieren precisión doble. Las magnitudes escalares continúan calculándose/reportándose como `float` Python.

Esto reduce aproximadamente a la mitad la RAM de los mapas 480×480 almacenados simultáneamente.

### 6. Curvas de nivel: matriz completa para datos, malla reducida para dibujar
La matriz científica Tmrt continúa en 480×480 y el hover consulta esa matriz completa. Solo `contourf/contour` reciben una malla de visualización con lado máximo 320 px. En la configuración actual 480×480 se dibuja como 240×240 con las mismas cotas y escala.

No se alteran los valores guardados, mínimos, máximos, colorbar ni valores consultados por el mouse.

### 7. Eliminación de copia PNG/PIL intermedia de la curva
La figura interactiva se guarda directamente a `curve_path`. Ya no se crea un `BytesIO` + una imagen PIL descomprimida adicional solo para volver a guardarla.

### 8. PIL y carrusel
Las imágenes abiertas para miniaturas y curvas estáticas se manejan con context manager (`with Image.open(...)`) para cerrar inmediatamente archivo/decoder. El carrusel mantiene únicamente `PhotoImage` pequeñas.

### 9. Liberación al cambiar de árbol
`_reset_panel2_for_new_image()` limpia referencias a:
- fotografía activa;
- mapas Tmrt/hover;
- análisis fotográfico;
- figura de escala Tmrt;
- artistas de la foto y curva anterior.

Después ejecuta `gc.collect()` en ese punto de transición, donde es útil romper ciclos de Matplotlib/Tk.

### 10. Compatibilidad de selección tras eliminar BGR
`ShapeSelector` ya no depende de `app.img` (la copia BGR eliminada). La selección de rectángulo/círculo/polígono usa `img_rgb`, por lo que el ahorro de RAM no rompe el dibujo de áreas. También se cierran explícitamente imágenes PIL usadas por loaders legacy.

### 11. Diagnóstico opcional
`core/memory_utils.py` permite consultar RSS sin agregar dependencias. Si se ejecuta con `SOMBRA_MEMORY_DEBUG=1`, la aplicación imprime puntos de control de RAM al liberar el Panel 2.

En PowerShell:

```powershell
$env:SOMBRA_MEMORY_DEBUG="1"
python main.py
```

## Microbenchmarks realizados

Entorno de prueba Linux del asistente; sirven como comparación relativa y no como promesa de consumo exacto en Windows.

### Foto 4000×3000 RGB
- v17: baseline 106.6 MB → 176.3 MB con BGR+RGB retenidos.
- v18: baseline 106.6 MB → 142.0 MB con solo RGB retenido.
- ahorro observado: ~34 MB por foto activa.

### Conversión a gris 4000×3000
Pico adicional sobre el array RGB ya cargado:
- v17 (`np.mean`): ~103 MB.
- v18 (`cv2.cvtColor`): ~12 MB.

### `contourf` representativo 480×480
Pico adicional de construcción de paths:
- matriz completa: ~24 MB.
- malla de visualización 240×240: ~7 MB.

La ganancia real varía con la complejidad espacial de la curva; mapas muy fragmentados pueden beneficiarse más.

## Validación

Suite completa v18:

- 142 tests aprobados.
- 5 tests omitidos por dependencia opcional `pvlib` no instalada en el entorno.

Se agregaron 7 pruebas específicas de v18 para carga RGB, gris uint8, figuras no registradas en pyplot, malla de render, render único de Edición y lectura RSS.

## Limitación de la prueba de RAM

El entorno automático no dispone de display gráfico, por lo que no fue posible ejecutar una sesión Tk completa de 20 cambios de árbol y medir el Working Set real de Windows. La prueba definitiva debe hacerse en la PC objetivo observando `python.exe`. La condición esperada es que después de varias selecciones la RAM alcance una meseta y no crezca de manera aproximadamente lineal con cada clic/recalculo.
