# Reemplazo v31 → v32

Esta corrección es mínima.

1. Cerrar completamente Proyecto Sombra.
2. Reemplazar `ui/scene3d.py` por el archivo incluido en este paquete.
3. El archivo `test/test_v32_vtk97_compat.py` es opcional para uso normal; se incluye para validación.
4. Volver a iniciar la aplicación y abrir la Vista 3D.

No es necesario reinstalar VTK. La corrección está pensada específicamente para el error observado con VTK 9.7.0.

Resultado esperado: el encabezado debe permanecer como `Motor 3D: VTK` y la escena debe continuar construyéndose después de agregar la barra de temperatura.
