# Proyecto Sombra v29 — Archivos de reemplazo

La v29 parte directamente de `proyecto_sombra_integrado_v28.zip`.

Para actualizar una instalación v28 sin reemplazar todo el proyecto, copiar conservando la estructura:

- `ui/scene3d.py` **(nuevo)**
- `ui/app_ui.py`
- `ui/panels.py`
- `diseño.py`
- `modelo_con_excel.py`
- `requirements-full.txt`
- `requirements-optional.txt`

Opcional para desarrollo/validación:

- `test/test_v29_vista3d.py`
- `CAMBIOS_VISTA_3D_VTK_v29.md`

Para activar el motor VTK:

```bash
pip install "vtk>=9.3,<10"
```

Si VTK no está instalado o falla al iniciar OpenGL, la vista usa automáticamente Matplotlib 3D dentro de la misma pestaña.

**No reemplazar `users.db`, proyectos guardados ni bases SQLite del usuario.**
