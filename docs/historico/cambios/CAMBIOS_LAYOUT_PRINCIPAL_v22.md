# v22 — Corrección de geometría del frame lateral

## Problema reproducido

En v21 se verificó con una ventana Tkinter de 1400×900 que `frame1` solicitaba un panel de 260 px, pero la columna 0 de la grilla principal terminaba recibiendo solo 218 px. Como los paneles internos se posicionan con `place()`, ese gestor no participa del cálculo de tamaño de `grid`: el panel seguía intentando medir 260 px y su extremo derecho quedaba recortado al llegar a los frames de las columnas 1 y 2.

No era una superposición real de `frame2`/`frame4` sobre `frame1`; era una compresión de la columna de `frame1` que producía el mismo efecto visual.

## Corrección

- La columna 0 ahora reserva explícitamente su ancho con `grid_columnconfigure(..., minsize=...)`.
- `frame1` usa `grid_propagate(False)` para que sus hijos no alteren de forma imprevisible el ancho reservado.
- Al abrir un panel, el ancho lateral se recalcula según el viewport actual.
- El ancho abierto usa 28 % del viewport, con mínimo operativo de 380 px y máximo de 520 px, sin superar 45 % en ventanas angostas.
- Al cerrar, la columna vuelve al ancho de la barra vertical de iconos.
- Se mantiene la regla v21: el contenido de cada panel ocupa 80 % del Canvas y la scrollbar permanece en una columna independiente.

## Verificación de geometría

En 1400×900, después del cambio:

- `frame1`: 392 px
- inicio de `frame2`: x=392 px
- ancho del panel interno: 392 px
- ancho útil del contenido al 80 %: ~301 px
- solapamiento entre `frame1` y `frame2`: ninguno

También se verificó en 1024, 1366, 1600 y 1920 px de ancho.
