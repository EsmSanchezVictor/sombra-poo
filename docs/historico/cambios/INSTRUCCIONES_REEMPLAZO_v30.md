# Reemplazo v29 → v30

La actualización no modifica bases de datos, proyectos guardados, Excel de escena ni módulos científicos.

## Si se usa el ZIP completo
Descomprimir `proyecto_sombra_integrado_v30.zip` en una carpeta nueva y conservar la carpeta/proyectos de trabajo del usuario según el flujo habitual.

## Si se usa el ZIP de reemplazo
Copiar los archivos manteniendo las rutas:
- `ui/app_ui.py`
- `ui/scene3d.py`
- `requirements.txt`
- `requirements-optional.txt`
- `requirements-full.txt`

Después actualizar dependencias del entorno con `requirements.txt`, porque desde v30 VTK es el motor 3D principal.

No reemplazar `users.db` ni bases de datos del usuario.
