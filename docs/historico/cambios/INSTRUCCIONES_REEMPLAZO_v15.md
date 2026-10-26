# Reemplazo v15

La forma más segura es realizar una copia de respaldo del proyecto y reemplazar los archivos respetando exactamente sus carpetas.

Archivos nuevos:
- `core/meteorology.py`
- `core/uncertainty.py`
- `services/meteorology_service.py`
- `test/test_meteorology.py`
- `test/test_uncertainty.py`
- `data/plantilla_meteorologia_observada.csv`

Archivos modificados:
- `core/app_state.py`
- `core/excel_scene.py`
- `core/project.py`
- `core/settings_manager.py`
- `diseño.py`
- `modelo_con_excel.py`
- `services/report_service.py`
- `services/snapshot_service.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `ui/menu_bar.py`
- `ui/panels.py`

Después de reemplazar, reinicie la aplicación.

Para usar datos observados:
1. abra o cree un proyecto;
2. Archivo > Importar > Serie meteorológica CSV;
3. seleccione `Serie meteorológica CSV` como fuente radiativa;
4. use una fecha/hora contenida en la serie;
5. ejecute Tmrt o el modelo de superficies.
