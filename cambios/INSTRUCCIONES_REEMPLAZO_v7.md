# Reemplazo v7

Hacé una copia de seguridad de tu proyecto y luego reemplazá/agregá:

- `core/excel_scene.py`
- `diseño.py`
- `modelo_con_excel.py`
- `ui/app_ui.py`

`test/test_excel_scene.py` es opcional para ejecución de la aplicación, pero conviene conservarlo para futuras pruebas.

## Flujo esperado

1. Crear/modificar la escena en **Edición**.
2. Guardar como Excel.
3. El archivo tendrá hojas `Árboles`, `Estructuras` y `Parametros`.
4. Abrir ese mismo Excel desde **Modelo**.
5. La geometría y los parámetros térmicos se restauran y el gráfico se regenera.

Los Excel antiguos siguen siendo compatibles: si no tienen `Parametros`, se carga la geometría y se mantienen los parámetros que estén actualmente en Modelo.

> Nota: el archivo correcto se llama `diseño.py` (con ñ), porque así lo importa la aplicación.
