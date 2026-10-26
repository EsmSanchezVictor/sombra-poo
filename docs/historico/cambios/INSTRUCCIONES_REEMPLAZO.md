# Cómo aplicar los archivos de reemplazo

1. Hacer una copia de seguridad del proyecto actual.
2. Cerrar la aplicación.
3. Copiar el contenido del ZIP de reemplazo sobre la raíz del proyecto, respetando las carpetas `core/`, `services/`, `ui/` y `test/`.
4. Aceptar reemplazar los archivos existentes.
5. No copiar carpetas `__pycache__` ni archivos `.pyc` de versiones anteriores.
6. Instalar dependencias desde `requirements.txt` si corresponde.
7. Ejecutar desde la raíz del proyecto: `python -m pytest -q`.

Los archivos incluidos son completos, no parches parciales.
