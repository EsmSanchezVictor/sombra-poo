# Proyecto Sombra v35.4.2 — Corrección robusta de módulo de formas de copa

Base funcional: v35.4.1.

## Problema observado en Windows
Al iniciar podía aparecer:

`ModuleNotFoundError: No module named 'core.crown_shapes'`

La causa era doble:

1. El reemplazo v35.4 -> v35.4.1 solo incluía `diseño.py`, asumiendo que `core/crown_shapes.py` ya había llegado con v35.4.
2. El nombre histórico `diseño.py` contiene `ñ` y algunos flujos ZIP/Windows/Git podían mostrarlo o extraerlo con mojibake (`dise�o.py`).

## Corrección

- Se agrega un módulo ASCII estable: `diseno.py`.
- Todos los imports internos de Proyecto Sombra pasan de `diseño` a `diseno`.
- `diseño.py` queda solamente como shim de compatibilidad histórica.
- El paquete de reemplazo v35.4.2 incluye **todos los archivos funcionales de formas de copa**, por lo que puede aplicarse directamente sobre v35.3 o cualquier v35.4.x anterior.
- Se incluye explícitamente `core/crown_shapes.py`.

## Forma de copa
Se mantienen las opciones:
- Esférica
- Cónica
- Columnar
- Piramidal
- Extendida
- Irregular
- Llora

La geometría visual se conserva en 2D/3D de Edición y Modelo. La formulación física de sombra/radiación no se modifica.

## Validación
- `python -m compileall -q .`: OK
- imports directos `core.crown_shapes`, `diseno`, `core.app_state`, `ui.app_ui`: OK
- suite completa: **218 passed, 5 skipped**
- suite con `ResourceWarning` convertido en error: **218 passed, 5 skipped**
