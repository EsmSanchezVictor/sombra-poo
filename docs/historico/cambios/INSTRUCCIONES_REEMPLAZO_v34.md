# Instrucciones de reemplazo — Proyecto Sombra v34

## Opción recomendada: ZIP completo

Usar `proyecto_sombra_integrado_v34.zip` como nueva base del proyecto.

1. Cerrar completamente Proyecto Sombra.
2. Hacer una copia de respaldo de la carpeta local actual.
3. Extraer `proyecto_sombra_integrado_v34.zip` en una carpeta nueva.
4. Conservar el `users.db` real que ya utiliza la instalación; no reemplazarlo por una base nueva de prueba.
5. Abrir un proyecto existente y verificar Edición, Modelo y Temperatura.

La migración de la base de usuarios sigue siendo automática.

## Opción incremental: archivos de reemplazo

El ZIP `archivos_reemplazo_modos_avanzados_v34.zip` contiene únicamente archivos nuevos/modificados respecto de v33.

Copiar su contenido sobre una instalación **v33**, preservando las rutas internas.

Archivos principales:
- `database_manager.py`
- `main_app.py`
- `modelo_con_excel.py`
- `core/app_state.py`
- `core/climate_profile.py`
- `core/excel_scene.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `ui/panels.py`
- `test/test_v34_advanced_modes.py`

No reemplazar manualmente `users.db`.

## Qué verificar después de actualizar

### Administración
1. Ingresar como administrador.
2. Abrir **Historial de sesiones**.
3. Confirmar la presencia de **Borrar historial**.
4. La acción debe solicitar confirmación y conservar la sesión administrativa actual.

### Modelo
1. Alternar Simple / Avanzado.
2. En Simple, los controles avanzados no deben quedar visibles ni actuar silenciosamente.
3. En Avanzado, comprobar Verano, Invierno, Soleado y Nublado.
4. Probar viento `nulo`, `moderado`, `fuerte` y una velocidad numérica.
5. Probar Despejado/Parcial/Nublado.
6. Probar Estándar / Avanzado seco / Vegetación + ET.
7. Si `pvlib` está disponible, probar cielo despejado con `pvlib/Ineichen`.
8. Si se dispone de CSV meteorológico, verificar Ta/RH/viento/GHI observados.

### Edición
Repetir la comprobación Simple / Avanzado y presets. Los parámetros deben pertenecer a Edición y no alterar accidentalmente los de Modelo.

### Temperatura
1. En **Entrada simple**, deben verse únicamente los campos básicos.
2. En **Entrada avanzada**, deben aparecer fuente radiativa, pvlib, GHI/DNI/DHI, CSV y selector Tmrt.
3. Volver a Simple: una fuente avanzada previamente seleccionada no debe continuar afectando el cálculo de forma oculta.

## Validación de esta entrega

La versión empaquetada se validó con:
- `python -m compileall -q .`
- `PYTHONPATH=. pytest -q`

Resultado esperado de v34: **202 passed, 5 skipped**.
