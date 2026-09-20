# Contexto Proyecto Sombra v35.5

Base estable inmediata: **v35.4.2**.

Esta revisión corrige la interacción de los formularios de Edición y depura el catálogo visible de materiales.

## Cambios clave

- Se eliminó la doble conexión Matplotlib del clic de Edición que abría dos ventanas.
- Se agregó protección de instancia única para `Nuevo Árbol` y `Nueva Estructura`.
- Ambos formularios fueron rediseñados como diálogos modales, alineados y con botones separados.
- `Forma de copa` continúa disponible con las siete formas de v35.4.x.
- Se depuró el catálogo visible de materiales a 43 nombres únicos.
- `concreto translucido` histórico continúa siendo aceptado y se normaliza a `Concreto Translúcido`.
- No se cambian fórmulas científicas.

## Archivos funcionales modificados

- `diseno.py`
- `ui/app_ui.py`
- `modelo_con_excel.py`
- `core/materials.py`
- `test/test_v35_5_dialogs_materials.py` (nuevo)

## Validación

- 221 tests aprobados, 5 omitidos.
- 0 `ResourceWarning` en ejecución estricta.
- Smoke Tk real de diálogos: OK.
- Smoke de arranque de aplicación: OK (GUI quedó abierta hasta timeout intencional).

## Continuidad

La rama sigue basada en la serie v35 estable. Esta versión no incorpora la rama de auditoría/seguridad v36 pendiente.
