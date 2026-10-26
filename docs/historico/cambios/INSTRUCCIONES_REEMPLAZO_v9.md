# Reemplazo v9

Aplicar sobre la v8.

Archivos nuevos/modificados:

- `core/radiative_tmrt.py` (nuevo)
- `core/settings_manager.py`
- `core/scenario.py`
- `shadow_temp.py`
- `ui/app_ui.py`
- `ui/panels.py`
- `ui/dialogs.py`
- `services/snapshot_service.py`
- `services/analysis_service.py`
- `services/report_service.py`
- `data/settings.json`
- `test/test_advanced_tmrt.py` (nuevo)

Después de reemplazar:

1. Abrir **Preferencias**.
2. En "Modelo térmico Tmrt" dejar "Estándar" para conservar el comportamiento histórico, o seleccionar "Avanzado" para probar el balance radiativo v1.
3. Regenerar cálculos/curvas: los resultados antiguos no se recalculan automáticamente.
4. No comparar valores Estándar y Avanzado sin registrar qué modelo produjo cada uno.

El modo Estándar sigue siendo el predeterminado.
