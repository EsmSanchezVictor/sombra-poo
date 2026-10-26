# v24 — Reducción horizontal real de los paneles

## Motivo
La v23 reducía principalmente padding, altura y tipografía. Sin embargo, los widgets con `sticky="ew"` volvían a expandirse hasta ocupar el 90 % del Canvas, por lo que visualmente el ancho apenas cambiaba.

## Cambio aplicado
La v24 compacta exclusivamente en el eje horizontal:

- ancho del sidebar abierto reducido aproximadamente un 30 % respecto de v23;
- 1400 px de ventana: 364 px -> 255 px;
- 1920 px de ventana: 499 px -> ~346 px;
- el contenido usa el 96 % del Canvas, dejando ~2 % de margen por lado;
- los widgets con `width` explícito se reducen al 70 %;
- `Scale.length` se reduce al 70 %;
- `padx` e `ipadx` se reducen al 70 %;
- no se reducen `height`, `pady`, `ipady` ni tipografías;
- los widgets `sticky="ew"` se hacen realmente más angostos porque el sidebar completo es menor;
- se mantiene la reserva física con `grid_columnconfigure(..., minsize=...)`, por lo que no vuelve el recorte de v21/v22;
- scrollbar permanece en columna independiente.

## Medición real con Tkinter (1400x900)

v23:
- frame1: 364 px
- Canvas: 350 px
- contenido: 315 px

v24:
- frame1: 255 px
- Canvas: 241 px
- contenido: 231 px
- frame2 comienza exactamente en x=255
- relación contenido/Canvas: 0.959 (~96 %)

No hay superposición entre frame1 y frame2.

## Validación
Suite completa: 170 tests aprobados, 5 omitidos por dependencias opcionales.
