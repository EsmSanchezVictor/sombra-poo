# Contexto Proyecto Sombra v35.6

Base estable inmediata: **v35.5**.

## Estado funcional
v35.6 homogeneiza la interfaz de todas las ventanas emergentes propias de la aplicación mediante un nuevo módulo central `ui/modal_style.py`.

## Cambios principales
- Todos los `Toplevel` funcionales de Edición, Modelo, herramientas, análisis y usuarios usan el mismo tratamiento visual.
- Formularios centrados, espaciados y sin superposición de campos/botones.
- Editar árbol/estructura de Edición y Modelo usa el mismo diseño visual que Añadir árbol/estructura.
- Preferencias y Ejecutar simulación fueron actualizados al mismo lenguaje visual.
- Prompts de texto (`Nuevo proyecto`, `Duplicar proyecto`) migrados a formularios propios.
- Restablecimiento de contraseña unificado en un único formulario con confirmación.
- Diálogos de resultados conservan redimensionamiento donde es útil.
- Diálogos nativos del sistema operativo (archivo/carpeta/messagebox) se mantienen nativos.

## Archivos nuevos
- `ui/modal_style.py`
- `test/test_v35_6_dialog_style.py`

## Archivos funcionales modificados
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

## Validación
- 224 tests aprobados.
- 5 tests omitidos por dependencias opcionales.
- 0 fallos.
- 0 `ResourceWarning` en ejecución estricta.
- Smoke Tk de los principales formularios: correcto y sin superposición.

## Ciencia
No hay cambios en fórmulas, constantes o modelos científicos.

## Continuidad
La rama continúa en la serie estable v35 y no incorpora todavía la futura rama integral de seguridad/auditoría v36.
