# Comprobación de escritorio en Windows

Este procedimiento completa evidencia que las pruebas Linux sin pantalla no producen. No requiere instalar una versión compilada y no modifica cuentas ni proyectos reales. Use Python 3.12 con el entorno de la aplicación.

```bat
.venv\Scripts\python tools\check_installation.py --require-full --report autocomprobacion_windows.json
.venv\Scripts\python tools\check_desktop.py --vtk --require-windows --report escritorio_windows.json
```

El segundo comando abre ventanas temporales para probar el editor con Tk real, el fallback Matplotlib y el render VTK: dibujo, selección, deshacer, aplicación, cámaras, zoom, actualización y cierre. VTK se ejecuta en otro proceso; si el driver falla o supera 60 segundos se guarda un fallo, nunca una aprobación por haber usado fallback. El informe identifica el sistema operativo. Sin `--vtk`, el control VTK figura como `not_run`. Estos comandos pueden ejecutarse desde otra carpeta usando las rutas completas.

Un resultado `passed` acredita esos componentes automáticos, no la aceptación visual de toda la aplicación. `human_visual_review` y `full_app_workflow_tested` permanecen en `false`: no se cambian automáticamente.

## Recorrido manual sobre una copia

Anote fecha, versión, Windows, resolución, escala de pantalla y GPU/controlador. Registre cada resultado y el error concreto si falla; no alcance con escribir solamente «abre».

| Comprobación | Resultado esperado |
|---|---|
| Iniciar sesión; abrir preferencias y gestión de usuarios | Campos legibles, sin ventanas duplicadas; cancelar conserva datos. |
| Crear proyecto y agregar árbol/estructura | Una sola ventana, botones accesibles y formas de copa persistentes. |
| Cambiar paneles y tamaño de ventana; probar escalas 100% y 150% | Controles y scrollbar accesibles, sin superposición. |
| Generar fotografía; excluir un material, deshacer/cancelar y aplicar | Cancelar conserva el cálculo; aplicar invalida resultados y pide regenerarlos. |
| Guardar una exclusión pendiente, cerrar y reabrir | Se recupera vinculada al elemento correcto. |
| Regenerar curva, guardar y reabrir | Máscara, cobertura y resultados del mismo elemento se conservan. |
| Generar escena 2D/3D; rotar, zoom y animación | Vista embebida, sol y sombra actualizados, cámara estable. |
| Exportar/importar `.3es` y Excel; abrir la copia importada | Se recuperan escena, parámetros y correcciones. |
| Cerrar y abrir repetidamente vista 3D y aplicación | Sin ventanas huérfanas ni errores de callbacks/SQLite. |

Guarde los dos JSON y sus observaciones juntos. Si VTK falla pero Matplotlib funciona, registre ambos resultados por separado. No se incluye un instalador o ejecutable Windows en esta entrega.
