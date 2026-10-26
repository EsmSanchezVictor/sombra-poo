# Proyecto Sombra v35.4.1 — Corrección del formulario Forma de copa

Base: **v35.4**.

## Problema observado
En Windows, el campo **Forma de copa** no aparecía al usar **Edición > Añadir árbol**, aunque el modelo, Excel y los renderizados ya soportaban la propiedad.

## Causa real
El paquete v35.4 había sido generado con una herramienta que codificó incorrectamente el nombre Unicode `diseño.py` dentro del ZIP. El archivo quedó almacenado como `dise├▒o.py`, por lo que al descomprimir sobre una instalación anterior **no reemplazaba el `diseño.py` existente**. El programa seguía ejecutando el formulario de una versión anterior.

## Corrección
- El formulario **Nuevo Árbol** muestra ahora, en este orden:
  1. Especie
  2. Forma de copa
  3. Altura
  4. Densidad de copa
  5. Radio de copa
- `Forma de copa` es una lista cerrada con:
  - Esférica
  - Cónica
  - Columnar
  - Piramidal
  - Extendida
  - Irregular
  - Llora
- Se mantiene **Esférica** como valor predeterminado.
- No se modificó ninguna fórmula científica ni cálculo de sombra, radiación o temperatura.
- Los ZIP de esta versión se generan con metadatos UTF-8 correctos para conservar `diseño.py` en Windows.

## Validación
- `python -m compileall -q .`: OK.
- `PYTHONPATH=. pytest -q`: **218 passed, 5 skipped**.
- Smoke test Tk real bajo Xvfb: el diálogo contiene `Forma de copa:` y las siete opciones esperadas.
- Verificación del ZIP: la entrada es exactamente `diseño.py` y tiene el flag UTF-8 activo.
