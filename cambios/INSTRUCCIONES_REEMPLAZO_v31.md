# Reemplazo v30 → v31

Para actualizar una instalación v30 basta con reemplazar:

- `ui/scene3d.py`

Opcionalmente copiar también:
- `DIAGNOSTICO_VTK_WINDOWS.py`
- `CAMBIOS_COMPATIBILIDAD_VTK_WINDOWS_v31.md`

No reemplazar `users.db`, proyectos guardados ni carpetas de datos.

Después de reemplazar, cerrar completamente la aplicación y volver a iniciarla. Generar primero el gráfico 2D y abrir luego `Vista 3D`.

Si todavía aparece `Matplotlib (fallback) · VTK no pudo inicializarse`, copiar el detalle rojo que ahora aparece debajo del encabezado. También puede ejecutarse:

```powershell
python DIAGNOSTICO_VTK_WINDOWS.py
```

El diagnóstico no modifica el proyecto.
