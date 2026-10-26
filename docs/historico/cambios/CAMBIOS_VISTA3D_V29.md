# v29 — Vista 3D VTK embebida

## Objetivo
Reemplazar la ventana 3D simplificada de Matplotlib por una vista 3D más realista,
interactiva y contenida en el mismo frame que el gráfico 2D.

## Motor elegido
Se usa **VTK 9.x**. No se usa PyVistaQt porque la aplicación principal es Tkinter
y mezclar Tk y Qt obligaría a mantener dos loops de eventos. Tampoco se depende de
`vtkRenderingTk`, ya que no está presente en todos los wheels actuales de VTK.

La solución usa VTK en **render off-screen** y presenta el resultado dentro de un
`Canvas` Tkinter. El arrastre rota la cámara y la rueda hace zoom; cada interacción
vuelve a renderizar con VTK. Esto mantiene la vista dentro del mismo frame y evita
ventanas externas.

## Interfaz
Los frames principales de Edición y Modelo contienen ahora un `ttk.Notebook` con:

- **Vista 2D**: Matplotlib, igual que antes.
- **Vista 3D**: VTK, dentro del mismo frame.

El botón `Vista 3D` selecciona la pestaña 3D. Al recalcular el gráfico se vuelve a
la pestaña 2D. No se abre ningún `Toplevel` para la visualización 3D.

## Mejoras visuales
- suelo con el mismo campo térmico y la misma paleta del mapa 2D;
- árboles con tronco cilíndrico y copa compuesta por varios volúmenes, evitando el
  aspecto de una única esfera;
- paredes como prismas orientados;
- galerías con cubierta y postes;
- senderos como superficies con espesor;
- materiales visuales derivados de la biblioteca del modelo (madera, metal,
  hormigón, vidrio/policarbonato, etc.);
- sombreado Phong/materiales ópticos robustos para render off-screen;
- iluminación principal cálida y luz de relleno;
- fondo degradado y antialiasing por multisampling;
- barra de temperatura dentro del render;
- cámara isométrica y vista superior;
- rotación con arrastre y zoom con rueda.

## Rendimiento
La matriz científica no se modifica. Para render 3D solamente, una malla mayor a
240 puntos por lado se submuestrea visualmente. Esto evita enviar cientos de miles
de vértices a la GPU sin afectar el cálculo físico ni los datos guardados.

VTK se carga de forma **perezosa**: la dependencia y la ventana de render no se
inicializan hasta que el usuario abre por primera vez la pestaña 3D.

## Dependencia nueva
`requirements.txt` agrega:

```
vtk>=9.3,<10
```

## Compatibilidad
Las funciones públicas históricas `diseño.generar_3d()` y
`modelo_con_excel.generar_3d()` se conservan, pero ahora delegan a la vista VTK
embebida. Los cálculos de temperatura, sombra y balance no cambian.
