# Instrucciones de reemplazo — v16

## Recomendación

La opción más segura es usar `proyecto_sombra_integrado_v16.zip` como nueva base de trabajo.

Si se actualiza un proyecto v15 existente, reemplazar los archivos conservando exactamente sus carpetas.

## Archivos de código modificados/nuevos

- `core/solar_math.py` (nuevo)
- `core/model_registry.py` (nuevo)
- `core/scientific_audit.py` (nuevo)
- `core/surface_energy.py`
- `core/validation.py`
- `core/app_state.py`
- `core/excel_scene.py`
- `shadow_temp.py`
- `modelo_con_excel.py`
- `services/solar_engine.py`
- `services/snapshot_service.py`
- `services/report_service.py`
- `ui/dialogs.py`
- `ui/app_ui.py`
- `ui/menu_bar.py`

## Dependencias

Instalación núcleo:

```bash
pip install -r requirements.txt
```

Instalación completa con extensiones científicas:

```bash
pip install -r requirements-full.txt
```

La aplicación funciona sin pvlib/pythermalcomfort, pero la auditoría lo indicará como advertencia.

## Después de reemplazar

Ejecutar:

```bash
python -m pytest -q
```

En el entorno usado para construir v16 el resultado fue:

- 128 passed
- 5 skipped (pvlib no instalado)

Luego abrir la aplicación y ejecutar:

**Análisis → Auditoría científica / preparación para validación…**

Antes de una campaña real, revisar además:

- `PROTOCOLO_VALIDACION_CAMPO_v16.md`
- `CHECKLIST_VALIDACION_v16.md`
- `data/plantilla_validacion_termica.csv`
- `data/plantilla_instrumentos_v16.csv`
