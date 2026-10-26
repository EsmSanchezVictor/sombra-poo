# Instrucciones de reemplazo — v35.5 → v35.6

## Opción recomendada: paquete de reemplazo
1. Cerrá Proyecto Sombra y VS Code si está ejecutando `main.py`.
2. Hacé una copia de respaldo de `d:\GitHub\sombra-poo`.
3. Extraé `archivos_reemplazo_dialogos_v35_6.zip` dentro de:
   `d:\GitHub\sombra-poo`
4. Aceptá reemplazar los archivos existentes.
5. Conservá la estructura de carpetas (`ui/`, `core/`, `test/`).
6. Ejecutá nuevamente `main.py`.

## Archivos funcionales del reemplazo
- `ui/modal_style.py` **(nuevo)**
- `ui/theme.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `diseno.py`
- `modelo_con_excel.py`
- `add_user_window.py`
- `modify_user_window.py`
- `admin_panel.py`
- `main_app.py`
- `core/project_manager.py`
- `login_window.py`

El paquete incluye además la prueba de regresión `test/test_v35_6_dialog_style.py`.

## Qué debería verse
Las ventanas propias de Proyecto Sombra deben compartir:
- fondo claro;
- tipografía Segoe UI;
- campos alineados;
- botones consistentes;
- centrado respecto de la aplicación;
- formularios sin controles superpuestos.

Los selectores de archivos/carpetas y los cuadros estándar de información/error siguen teniendo el estilo nativo de Windows intencionalmente.
