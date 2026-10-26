# Reemplazo v35.3 → v35.4

Cerrar Proyecto Sombra antes de reemplazar archivos.

Copiar los archivos del ZIP de reemplazo respetando la estructura de carpetas y sobrescribir cuando Windows lo solicite.

Archivos nuevos:
- `core/crown_shapes.py`
- `ui/canopy_rendering.py`
- `test/test_v35_4_canopy_shapes.py`

Archivos modificados:
- `diseño.py`
- `modelo_con_excel.py`
- `core/excel_scene.py`
- `core/scene_objects.py`
- `core/app_state.py`
- `ui/scene3d.py`
- `ui/diurnal_animation.py`

No es necesario modificar manualmente proyectos o Excel antiguos: los árboles sin forma almacenada se interpretan como **Esférica**.
