# Instrucciones de reemplazo — v13

Aplicar sobre la v12 o usar directamente el proyecto integrado v13.

Archivos nuevos/modificados:

- `core/vegetation.py` (nuevo)
- `core/species.py`
- `core/settings_manager.py`
- `core/excel_scene.py`
- `modelo_con_excel.py`
- `diseño.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `services/report_service.py`
- `services/snapshot_service.py`
- `data/settings.json`
- `test/test_vegetation.py` (nuevo)

Después de reemplazar:

1. iniciar la aplicación;
2. abrir Preferencias;
3. dejar `Estándar` para reproducir resultados previos, o elegir `Avanzado vegetación + ET (v2)`;
4. configurar fracción de suelo vegetado y disponibilidad hídrica;
5. si se desea, editar LAI/Kc/transmitancia sin hojas desde la biblioteca de especies;
6. regenerar el gráfico de superficie.

Los Excel previos siguen abriendo. Los archivos v13 guardan además los parámetros de vegetación.
