# Reemplazo v32 → v33

1. Cerrar Proyecto Sombra.
2. Hacer una copia de seguridad de la carpeta actual.
3. Reemplazar `ui/scene3d.py` por el incluido en el ZIP de reemplazo.
4. No reemplazar `users.db` ni carpetas de proyectos/datos.
5. Iniciar normalmente la aplicación y abrir Vista 3D.

Resultado esperado:
- `Motor 3D: VTK` si VTK está disponible.
- terreno térmico al 50 %;
- isotermas visibles;
- objetos físicos con mayor contraste respecto de la temperatura.
