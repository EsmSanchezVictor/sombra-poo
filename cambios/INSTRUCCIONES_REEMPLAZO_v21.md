# Instrucciones de reemplazo — v21

Base: `proyecto_sombra_integrado_v20.zip`.

## Opción recomendada

Usar directamente `proyecto_sombra_integrado_v21.zip`.

## Reemplazo sobre v20

Copiar respetando las carpetas:

- `ui/app_ui.py`
- `ui/layout.py`
- `test/test_ui_layout.py`
- `test/test_v21_interfaz.py`

Los cambios son exclusivamente de interfaz. No se modifican fórmulas, modelos térmicos, base SQLite, estructura de proyecto ni archivos guardados.

## Comprobación visual sugerida

1. Abrir cada uno de los cuatro iconos de `frame1`.
2. Verificar que los controles queden centrados y no ocupen más del 80 % del viewport.
3. Desplazarse con la barra vertical hasta el final de cada panel.
4. Verificar que la barra no tape ningún control.
5. En el Panel 2, cargar varios análisis y comprobar que el carrusel muestre solamente miniaturas, sin nombres debajo.
