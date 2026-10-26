# Instrucciones de reemplazo — v20

Base esperada: **v19**.

## Opción recomendada

Usar directamente `proyecto_sombra_integrado_v20.zip`.

## Reemplazo sobre v19

Copiar respetando las rutas:

- `core/app_state.py`
- `core/scenario.py`
- `core/thermal_comfort.py`
- `image_processor.py`
- `services/snapshot_service.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `ui/panels.py`
- `test/test_v20_confort.py`
- `CAMBIOS_CONFORT_RESOLUCION_v20.md`

No se requiere migración manual de proyectos. Al abrirlos, la resolución se normaliza automáticamente al nuevo rango 64–640.

## Dependencia de UTCI

Para disponer de UTCI:

```bash
pip install pythermalcomfort
```

Las versiones actuales de pythermalcomfort utilizan la ruta vectorizada. Si se instala una versión antigua que rechaza arrays, la app conserva un fallback escalar compatible, aunque más lento.
