# Instrucciones de reemplazo — v11

La v11 parte del proyecto integrado v10.

Reemplazar respetando las rutas:

- `image_processor.py`
- `shadow_temp.py`
- `ui/app_ui.py`
- `services/snapshot_service.py`
- `services/analysis_service.py`
- `services/report_service.py`
- `test/test_image_processor.py`
- `test/test_physics.py`

No eliminar los demás archivos de la v10.

Después de reemplazar, abrir un proyecto, cargar una fotografía y volver a seleccionar área de cálculo + área de referencia. Los análisis viejos no contienen todavía la separación cobertura/atenuación hasta ser recalculados.
