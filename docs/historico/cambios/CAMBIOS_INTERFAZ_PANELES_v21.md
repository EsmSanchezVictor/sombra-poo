# Cambios v21 — Carrusel y paneles laterales

## Objetivo

Mejorar la legibilidad de la interfaz sin modificar cálculos, física, persistencia ni resultados del proyecto.

## 1. Carrusel

- Se eliminaron los nombres y porcentajes que se mostraban debajo de cada miniatura.
- La identificación visual queda dada por la fotografía y por el borde azul del elemento seleccionado.
- La altura del `Canvas` del carrusel se redujo ligeramente de 62 a 58 px porque ya no necesita reservar una segunda línea de texto.
- El clic conserva exactamente el comportamiento v17+: seleccionar un análisis restaura su información y no recalcula ni duplica registros.

## 2. Paneles de `frame1`

Los cuatro paneles laterales comparten ahora una única regla de geometría:

- contenido = **80 % del ancho útil del Canvas**;
- margen izquierdo + derecho = 20 % restante, distribuido simétricamente;
- la regla se aplica desde `_crear_panel_desplazable`, por lo que alcanza a los Paneles 1, 2, 3 y 4 y también a controles que se agreguen en el futuro.

Esto evita que `Entry`, `Combobox`, botones, radiobuttons o labels lleguen hasta el borde del panel y se recorten durante la animación o en pantallas angostas.

## 3. Scroll vertical

La scrollbar ya no comparte el mismo espacio visual con el contenido:

```text
panel_outer
├── columna 0: Canvas + contenido (80 % interno)
└── columna 1: Scrollbar vertical
```

La barra queda siempre a la derecha, en una columna reservada de 12 px, sin superponerse con controles.

Además:

- `scrollregion` se recalcula al cambiar el contenido;
- el alto del frame interno se vuelve a sincronizar después del wrapping de textos;
- se evita el `bind_all` global de la rueda del mouse;
- la rueda se vincula localmente a elementos no editables;
- `Entry`, `Scale`, `Combobox`, `Listbox` y `Text` conservan sus propios eventos y no son interceptados.

## 4. Textos largos

Se ajusta dinámicamente `wraplength` para:

- `Label`;
- `Button`;
- `Checkbutton`;
- `Radiobutton`.

Así, los textos largos aumentan su altura si hace falta en vez de quedar recortados horizontalmente.

## Validación

- Compilación de `ui/app_ui.py` y `ui/layout.py`: correcta.
- Smoke test real de Tkinter bajo Xvfb: contenido 243 px sobre Canvas 304 px, relación **0,799**; scrollbar 14 px en columna separada.
- Suite: **158 tests aprobados, 5 omitidos** por `pvlib` opcional.

## Archivos modificados

- `ui/app_ui.py`
- `ui/layout.py`
- `test/test_ui_layout.py`
- `test/test_v21_interfaz.py`
