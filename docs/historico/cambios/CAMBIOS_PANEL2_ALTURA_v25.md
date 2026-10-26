# Cambios v25 — ocupación vertical del Panel 2

## Problema observado

El contenedor físico del Panel 2 ya ocupaba todo el alto disponible, pero sus controles estaban apilados con `pack` y su alto natural era menor que el viewport. En una prueba de 1400×900, el viewport medía 772 px y los controles necesitaban aproximadamente 480 px, dejando cerca de 292 px vacíos debajo del último botón.

## Solución

`setup_panel_2` se reorganizó con `grid` en cuatro bloques: imagen/detector, resolución, selección de áreas y procesamiento. La fila de selección (`row=2`) tiene `weight=1`, igual que los bloques expansibles ya utilizados en los paneles 3 y 4. De este modo, cuando sobra altura, el espacio se absorbe en la zona central y el bloque **Calcular y procesar** queda apoyado en el borde inferior del viewport.

No se modifican el ancho v24, tipografías, cálculos, matrices, persistencia, carrusel ni modelos térmicos. Si la ventana es más baja que el contenido requerido, el scroll vertical común sigue funcionando.

## Verificación

Prueba Tkinter 1400×900:

- alto del Canvas del Panel 2: 772 px;
- alto forzado del frame de contenido: 772 px;
- borde inferior del bloque de procesamiento: 772 px;
- espacio vacío debajo del bloque final: **0 px**.

Suite completa: **172 passed, 5 skipped** (opcionales).
