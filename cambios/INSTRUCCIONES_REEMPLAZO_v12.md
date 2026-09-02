# Instrucciones de reemplazo v12

Base requerida: **v11**.

Reemplazar/agregar respetando exactamente las rutas:

- `core/materials.py` (nuevo)
- `core/surface_energy.py` (nuevo)
- `core/settings_manager.py`
- `core/excel_scene.py`
- `modelo_con_excel.py`
- `diseño.py`
- `ui/app_ui.py`
- `services/report_service.py`
- `services/snapshot_service.py`
- `data/settings.json`
- `test/test_surface_energy.py` (nuevo)

Después de reemplazar, iniciar la aplicación normalmente. El comportamiento
predeterminado sigue siendo el modelo Estándar.

Para probar el nuevo modelo:

1. Abrir **Preferencias**.
2. En **Modelo térmico de superficies**, seleccionar
   `Avanzado (balance energético no lineal v1)`.
3. Guardar.
4. Regenerar el gráfico de Modelo o Edición.

Los Excel nuevos guardan el modelo de superficie elegido y lo restauran al
volver a abrirlos.
