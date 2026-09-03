# Instrucciones de reemplazo — v18

Base requerida: v17.

Reemplazar/agregar conservando la estructura de carpetas:

- `image_processor.py`
- `shape_selection.py`
- `temp_graph.py`
- `diseño.py`
- `modelo_con_excel.py`
- `ui/app_ui.py`
- `services/shadow_detector.py`
- `services/snapshot_service.py`
- `core/memory_utils.py` (nuevo)
- `test/test_v18_memory.py` (nuevo)

No cambia la base SQLite del carrusel ni su esquema. Los proyectos v17 son compatibles.

Después del reemplazo se recomienda cerrar por completo el proceso Python anterior y abrir nuevamente la aplicación para medir RAM desde un estado limpio.
