# Proyecto Sombra — Cambios v29: vista 3D VTK integrada

## Objetivo

Mejorar la calidad visual de la vista 3D sin tocar la física ni los resultados científicos y mantenerla dentro del mismo contenedor que la vista 2D.

## Decisión técnica

Se adoptó **VTK estándar** como motor 3D preferido. PyVista se evaluó como alternativa de alto nivel, pero su integración de escritorio recomendada se apoya en Qt/pyvistaqt; migrar una parte de una aplicación Tkinter a Qt agrega un segundo toolkit de GUI y más complejidad de ciclo de eventos.

También se probó `vtkTkRenderWindowInteractor`. En el entorno de validación el módulo Python estaba presente, pero el wheel estándar de VTK no incluía la biblioteca nativa `libvtkRenderingTk.so`. Por esa razón v29 no depende de `vtkRenderingTk`.

La solución final usa:

- VTK real para mallas, actores, cámara, iluminación Phong, antialiasing y barra escalar;
- `vtkRenderWindow` en modo off-screen;
- captura RGBA del frame VTK;
- presentación del frame dentro de un widget Tkinter;
- eventos Tk para rotación, zoom y cambio de vista;
- fallback Matplotlib 3D embebido si VTK no está instalado o no puede inicializar OpenGL.

Así se evita una ventana secundaria y se mantiene un único toolkit de interfaz.

## Interfaz

En los mismos contenedores históricos:

- **Edición:** `frame7`;
- **Modelo:** `frame11`.

se crea un `ttk.Notebook` con dos pestañas:

- `Vista 2D`;
- `Vista 3D`.

La vista 2D conserva el renderer Matplotlib existente. El botón **Vista 3D** selecciona la pestaña 3D y renderiza allí; no abre `Toplevel`.

## Render VTK

El nuevo módulo `ui/scene3d.py` representa:

- la matriz térmica existente `T` sobre el plano X/Y;
- una base de terreno con espesor visual;
- árboles con tronco cilíndrico y copa elipsoidal;
- paredes como prismas orientados;
- galerías y senderos como elementos volumétricos simples;
- escala térmica equivalente a la vista 2D;
- ejes X/Y/altura;
- iluminación principal orientada con los ángulos solares ya calculados;
- cámara isométrica, superior, reencuadre, rotación por arrastre y zoom con rueda.

La geometría vegetal es una representación visual simplificada; no sustituye el modelo científico de sombra ni agrega cálculos físicos.

## Integridad científica

No se modificaron kernels de física, Tmrt, confort, radiación, sombra, superficies, ET, meteorología ni validación.

`diseño.py` y `modelo_con_excel.py` solo guardan dos metadatos de render:

- `_render_solar_altitude_deg`;
- `_render_solar_azimuth_deg`.

Estos valores provienen de los ángulos solares ya calculados y se usan exclusivamente para orientar la luz del render VTK. La vista 3D consume `X`, `Y` y `T` ya existentes; no recalcula el campo térmico.

## Dependencias

VTK se agrega como dependencia opcional:

```text
vtk>=9.3,<10
```

- `requirements-full.txt`: incluye VTK.
- `requirements-optional.txt`: incluye VTK.
- `requirements.txt`: permanece sin cambios.

Por lo tanto, una instalación existente sin VTK sigue pudiendo ejecutar el programa mediante el fallback Matplotlib.

## RAM y ciclo de vida

El controlador 3D:

- conserva una sola imagen Tk del frame renderizado;
- reemplaza la imagen anterior al actualizar la cámara;
- finaliza explícitamente `vtkRenderWindow` al reconstruir/cerrar la vista;
- destruye el controlador anterior antes de regenerar;
- no mantiene ventanas 3D independientes.

## Archivos de código modificados

- `ui/scene3d.py` — nuevo backend 3D.
- `ui/app_ui.py` — contenedor compartido 2D/3D y navegación.
- `ui/panels.py` — botón 3D de Modelo dirigido al contenedor integrado.
- `diseño.py` — render 3D delegado al nuevo backend; metadatos solares visuales.
- `modelo_con_excel.py` — render 3D delegado al nuevo backend; metadatos solares visuales.
- `requirements-full.txt`.
- `requirements-optional.txt`.
- `test/test_v29_vista3d.py` — pruebas específicas de v29.

## Compatibilidad

No se cambia el formato de proyectos, `users.db`, SQLite de análisis, Excel de escena ni archivos de configuración. Los proyectos de v28 se mantienen compatibles.

## Validación ejecutada

- Compilación Python de los archivos modificados: correcta.
- Suite completa: **184 tests aprobados, 5 omitidos**.
- Smoke test VTK real bajo display virtual: backend VTK inicializa, genera frame, cambia entre vista isométrica/superior, reencuadra, rota y hace zoom.
- Smoke test del fallback Matplotlib: correcto y sin abrir `Toplevel`.
- Validación visual del frame VTK: terreno térmico, árboles, pared, galería, ejes y barra escalar visibles y proporcionados.
- Comparación de directorios: `core/` y `services/` no presentan cambios respecto de v28 (fuera de cachés generadas por Python).

### Nota de estabilidad gráfica

En la validación off-screen, activar FXAA produjo un frame negro con el wheel/driver disponible. v29 lo deja desactivado y conserva **MSAA 8x**, que resultó estable. También se evita depth peeling en este backend por compatibilidad; la transparencia de copas usa mezcla alfa estándar.
