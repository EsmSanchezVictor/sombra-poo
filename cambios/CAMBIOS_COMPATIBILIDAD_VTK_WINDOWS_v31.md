# Proyecto Sombra — v31 · compatibilidad VTK en Windows

## Motivo
En v30, una instalación de VTK podía ser detectada correctamente pero fallar al crear el primer contexto gráfico, mostrando únicamente `VTK no pudo inicializarse`. El mensaje ocultaba la excepción real.

## Cambios
- En Windows, el primer contexto VTK se crea con **MSAA = 0**. La documentación de VTK advierte que determinados drivers presentan problemas de render con multisampling. La calidad visual se conserva mediante el supersampling + reducción LANCZOS ya incorporado en v30.
- El primer render se **difiere con `after_idle`** hasta que el widget Tk/Notebook haya completado su construcción.
- Si VTK falla después de crear la pestaña, la aplicación degrada realmente a Matplotlib sin cerrarse.
- El fallback muestra ahora **versión de VTK, versión de Python, sistema operativo y excepción real**.
- Si VTK no devuelve una imagen válida, se genera un error explícito en lugar de fallar silenciosamente.
- Se agrega `DIAGNOSTICO_VTK_WINDOWS.py` para probar VTK/OpenGL de manera aislada.

## Ciencia
No se modifican `core/`, `services/`, fórmulas, matrices ni resultados térmicos. Es una corrección exclusivamente de inicialización/render.

## Validación realizada
- Suite heredada: 187 tests passed, 5 skipped.
- Smoke test VTK/Tk real en el entorno de validación: backend `VTK`, creación y cierre correctos.
- Windows real del usuario: pendiente de verificar en su hardware/driver; por eso se incorpora diagnóstico visible.
