# Proyecto Sombra — v32

## Objetivo
Corregir la incompatibilidad de la vista 3D VTK con **VTK 9.7.x** detectada en Windows, sin modificar ningún cálculo científico.

## Error observado
En VTK 9.7.0 la vista 3D iniciaba el backend VTK pero fallaba al agregar la barra de colores con:

`AttributeError: 'vtkmodules.vtkRenderingOpenGL2.vtkOpenGLRenderer' object has no attribute 'AddActor2D'`

Esto confirma que VTK estaba instalado e inicializado; el fallo ocurría después, al construir la escena.

## Causa
`vtkRenderer.AddActor2D()` ya no está disponible en la API usada por VTK 9.7. La barra de colores (`vtkScalarBarActor`) sigue siendo un `vtkProp` y puede agregarse mediante la API general `AddViewProp()`.

## Corrección
En `ui/scene3d.py`:

- se reemplaza `renderer.AddActor2D(scalar_bar)` por `renderer.AddViewProp(scalar_bar)`;
- no se cambia el mapa térmico, los árboles, las estructuras, la cámara ni la física;
- la solución también funciona en el VTK 9.6.2 usado para la validación disponible.

## Validación realizada
- Suite completa: **192 passed, 5 skipped**.
- Prueba de regresión agregada: confirma que no queda la llamada heredada `AddActor2D` y que `vtkScalarBarActor` puede agregarse con `AddViewProp`.
- `core/` y `services/` permanecen sin cambios.

## Archivos modificados/agregados
- `ui/scene3d.py`
- `test/test_v32_vtk97_compat.py`
- `CAMBIOS_COMPATIBILIDAD_VTK97_v32.md`
- `CONTEXTO_PROYECTO_SOMBRA_v32.md`
- `INSTRUCCIONES_REEMPLAZO_v32.md`
