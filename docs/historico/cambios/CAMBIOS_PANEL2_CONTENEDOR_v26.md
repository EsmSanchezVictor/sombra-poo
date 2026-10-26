# v26 — Altura real del contenedor del Panel 2

## Problema
Al abrir el Panel 2 aparece el carrusel en la fila 4 de la grilla principal (`frame15`).
`frame1`, que contiene los cuatro paneles laterales, estaba configurado con `rowspan=3`, por lo que solo ocupaba las filas 1, 2 y 3. La fila 4 quedaba fuera de su altura y se veía una franja libre debajo del Panel 2.

## Corrección
- `frame1` pasa de `rowspan=3` a `rowspan=4`.
- De esta forma, cuando el carrusel de Panel 2 hace visible la fila 4, el lateral se estira físicamente hasta el mismo borde inferior.
- Cuando la fila 4 está oculta en los otros paneles, no agrega altura artificial.
- Se revierte la redistribución interna de widgets introducida en v25: Panel 2 vuelve a la disposición de v24. No se empujan botones al fondo ni se agrega una fila flexible artificial.
- Se conserva íntegramente el ancho de v24, scroll, carrusel y cálculos.
