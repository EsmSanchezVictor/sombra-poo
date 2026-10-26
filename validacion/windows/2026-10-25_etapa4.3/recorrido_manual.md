# Recorrido manual en Windows — v35.6-etapa4.3

Complete este archivo sobre una **copia** de sus proyectos. Marque cada fila con `OK`, `FALLA` o `N/A` y, si falla, anote el error concreto (texto del mensaje, qué estaba haciendo, si se repite). Escribir solo «abre» no alcanza. Procedimiento: [docs/ACEPTACION_WINDOWS.md](../../../docs/ACEPTACION_WINDOWS.md).

## Equipo

| Dato | Valor |
|---|---|
| Fecha del recorrido | |
| Evaluador | |
| Versión de la aplicación | v35.6-etapa4.3 |
| Windows | Windows 10 build 19045 (según `autocomprobacion_windows.json`) |
| Python | 3.12.10 (según `autocomprobacion_windows.json`) |
| Resolución de pantalla | |
| Escala de pantalla (100 % / 125 % / 150 %) | |
| GPU y versión del controlador | |
| Proyecto de prueba (copia) | |

Evidencia automática ya registrada en esta carpeta: `autocomprobacion_windows.json` y `escritorio_windows.json`.

## Comprobaciones

| # | Comprobación | Resultado esperado | Resultado | Observación |
|---|---|---|---|---|
| 1 | Iniciar sesión; abrir preferencias y gestión de usuarios | Campos legibles, sin ventanas duplicadas; cancelar conserva datos | | |
| 2 | Crear proyecto y agregar árbol/estructura | Una sola ventana, botones accesibles, formas de copa persistentes | | |
| 3 | Cambiar paneles y tamaño de ventana; probar escalas 100 % y 150 % | Controles y barra de desplazamiento accesibles, sin superposición | | |
| 4 | Generar fotografía; excluir un material, deshacer/cancelar y aplicar | Cancelar conserva el cálculo; aplicar invalida resultados y pide regenerarlos | | |
| 5 | Guardar una exclusión pendiente, cerrar y reabrir | Se recupera vinculada al elemento correcto | | |
| 6 | Regenerar curva, guardar y reabrir | Máscara, cobertura y resultados del mismo elemento se conservan | | |
| 7 | Generar escena 2D/3D; rotar, zoom y animación | Vista embebida, sol y sombra actualizados, cámara estable | | |
| 8 | Exportar/importar `.3es` y Excel; abrir la copia importada | Se recuperan escena, parámetros y correcciones | | |
| 9 | Cerrar y abrir repetidamente la vista 3D y la aplicación | Sin ventanas huérfanas ni errores de callbacks/SQLite | | |

## Resultado global

- [ ] Todas las filas en `OK` → se puede registrar `human_visual_review` y `full_app_workflow_tested` como realizados **por esta persona**, en `validacion/estado_actual.json`.
- [ ] Hay fallas → abrir un ítem por cada `FALLA` con su observación.

Si VTK falla pero Matplotlib funciona, registre ambos resultados por separado en la columna Observación.
