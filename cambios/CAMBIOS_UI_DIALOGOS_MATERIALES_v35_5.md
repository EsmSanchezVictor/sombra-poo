# Proyecto Sombra v35.5 — Diálogos de Edición y catálogo de materiales

Base: **v35.4.2**.

## Problemas reportados

1. Al usar **Edición → Añadir Árbol**, un solo clic podía abrir dos ventanas `Nuevo Árbol`.
2. La segunda ventana quedaba desplazada sobre la primera y daba la impresión de que botones/campos se superponían.
3. `Nueva Estructura` utilizaba el mismo estilo mínimo y podía resultar poco clara.
4. El catálogo visible de materiales contenía el duplicado `Concreto Translúcido` / `concreto translucido` y nombres con capitalización inconsistente.

## Causa de la doble ventana

La vista 2D de Edición conectaba dos veces `button_press_event`:

- una vez en el renderer `diseno.actualizar_grafico()`;
- otra vez en `SombraApp.actualizar_grafico_diseno()`.

Un único clic ejecutaba dos callbacks. Se eliminó la segunda conexión y el renderer queda como única fuente del evento.

Además se agregó una defensa adicional: los diálogos se registran en la instancia de la app (`_dialogo_arbol` / `_dialogo_estructura`). Si ya existe uno, se trae al frente en lugar de crear otro.

## Nuevo formulario “Añadir árbol”

- una única ventana modal;
- título y subtítulo con la posición X/Y seleccionada;
- separación uniforme entre etiquetas y campos;
- campos alineados y más anchos;
- `Forma de copa` claramente visible;
- botones separados: `Cancelar` y `Guardar árbol`;
- `Enter` guarda y `Esc` cancela;
- validación explícita de altura, densidad y radio;
- centrado automático respecto de la aplicación;
- tamaño adaptado al DPI, sin geometrías rígidas.

## Nuevo formulario “Añadir estructura”

- una única ventana modal;
- muestra punto inicial y final;
- `Tipo`, `Altura`, `Opacidad` y `Material` alineados;
- material como selector de solo lectura;
- botones `Cancelar` y `Guardar estructura`;
- validación de altura y opacidad;
- `Enter` guarda y `Esc` cancela;
- misma estética que el formulario de árbol.

## Materiales

El selector visible queda con **43 materiales únicos** y nombres consistentes.

Se elimina del catálogo físico la entrada duplicada `concreto translucido`, manteniendo compatibilidad mediante un alias que resuelve hacia `Concreto Translúcido`.

`Policarbonato` y `Policarbonato (paneles)` se mantienen como entradas separadas porque representan variantes constructivas distintas.

La biblioteca avanzada también elimina el duplicado de concreto translúcido. No se modifican propiedades térmicas ni ópticas.

## Modelo científico

No hay cambios en:

- geometría solar;
- cálculo de sombras;
- Tmrt;
- balance de energía;
- temperatura superficial;
- propiedades físicas de los materiales existentes.

Los cambios son de interfaz, validación, compatibilidad y catálogo visible.

## Validación

- `python -m compileall -q ...`: OK.
- suite completa: **221 passed, 5 skipped**.
- suite con `ResourceWarning` convertido en error: **221 passed, 5 skipped**.
- smoke test Tk/Xvfb:
  - dos llamadas consecutivas a `mostrar_dialogo_arbol()` → **1 Toplevel**;
  - `Forma de copa` visible;
  - árbol: tamaño solicitado aproximado 479×326 px;
  - dos llamadas consecutivas a `mostrar_dialogo_estructura()` → **1 Toplevel**;
  - material: **43 opciones**, sin `concreto translucido` duplicado;
  - estructura: tamaño solicitado aproximado 447×288 px.
- smoke de arranque `main.py`: sin traceback durante 8 s; finalizado por timeout intencional al quedar la GUI abierta.
