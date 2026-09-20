# Reemplazo v35.4.2 → v35.5

## Opción recomendada: paquete de reemplazo

1. Cerrá Proyecto Sombra.
2. Hacé una copia de seguridad de `d:\GitHub\sombra-poo`.
3. Extraé `archivos_reemplazo_ui_v35_5.zip` directamente dentro de `d:\GitHub\sombra-poo`.
4. Permití reemplazar los archivos existentes.
5. Verificá que existan:
   - `diseno.py`
   - `modelo_con_excel.py`
   - `core\materials.py`
   - `ui\app_ui.py`
6. Ejecutá `main.py`.

## Qué probar

### Añadir Árbol

- seleccionar `Añadir Árbol`;
- hacer un solo clic en la vista 2D;
- debe abrirse **una sola** ventana;
- `Forma de copa` debe ser visible;
- los campos no deben superponerse;
- `Cancelar` y `Guardar árbol` deben verse separados.

### Añadir Estructura

- seleccionar `Añadir Estructura`;
- marcar extremo inicial y final;
- debe abrirse **una sola** ventana;
- el selector de material debe mostrar una lista limpia;
- `Concreto Translúcido` debe aparecer una sola vez.

## Compatibilidad

Los proyectos viejos que hayan guardado `concreto translucido` siguen funcionando. No es necesario editar los Excel existentes.
