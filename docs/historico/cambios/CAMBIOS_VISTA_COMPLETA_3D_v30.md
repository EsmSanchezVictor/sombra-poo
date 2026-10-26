# Proyecto Sombra — v30

## Objetivo
Aprovechar todo el bloque central de visualización para los gráficos 2D/3D de **Edición** y **Modelo**, y acercar el 3D embebido a la calidad del render VTK de validación, sin modificar cálculos científicos.

## 1. Área central completa
En v29 `frame7` (Edición) y `frame11` (Modelo) ocupaban solo `row=1, column=1`. En v30 ambos pasan a:

- `row=1`
- `column=1`
- `rowspan=2`
- `columnspan=2`
- `sticky="nsew"`

Por lo tanto cada host ocupa físicamente el área conjunta de `frame2`, `frame3`, `frame4` y `frame5`.

Las pestañas **Vista 2D / Vista 3D** se mantienen dentro del mismo `ttk.Notebook` y llenan el 100 % del host.

Los frames auxiliares 8-10 y 12-14 se conservan por compatibilidad, pero no se muestran en Edición ni Modelo.

## 2. VTK pasa a ser motor principal
En v29 VTK estaba en `requirements-optional.txt`. Si no estaba instalado, la aplicación usaba Matplotlib 3D y la diferencia visual con el render VTK era grande.

En v30:
- `vtk>=9.3,<10` pasa a `requirements.txt`;
- Matplotlib sigue disponible únicamente como fallback;
- el fallback informa explícitamente si VTK no está instalado o no pudo inicializarse.

La importación de VTK sigue siendo diferida: no se carga al arrancar la aplicación, solo cuando se solicita Vista 3D.

## 3. Mejora visual VTK
Cambios exclusivamente de render:
- supersampling estático 1.35x;
- máximo aproximado de 2.6 millones de píxeles por frame para controlar RAM;
- durante el arrastre de cámara se renderiza a 1x;
- al soltar se genera nuevamente el cuadro de alta calidad;
- copas de árboles multilobuladas en lugar de una elipsoide única;
- mayor resolución de malla para copas y troncos;
- iluminación principal cálida, relleno frío y luz de recorte;
- fondo con gradiente más profundo;
- cámara isométrica ajustada automáticamente al contenido;
- MSAA 8x conservado; FXAA sigue desactivado por incompatibilidad detectada en render off-screen.

La geometría visual multilobulada permanece dentro del `radio_copa` y de la altura existentes. No cambia la geometría usada por los cálculos de sombra.

## 4. Validación realizada
- Suite automática: **187 passed, 5 skipped**.
- Pruebas específicas v29/v30: **7 passed**.
- Prueba VTK real bajo Tk/Xvfb:
  - backend: VTK;
  - viewport: 1200×722;
  - render interno de alta calidad: 1620×975.
- `core/` y `services/` no fueron modificados.

## Archivos modificados
- `ui/app_ui.py`
- `ui/scene3d.py`
- `requirements.txt`
- `requirements-optional.txt`
- `requirements-full.txt`

## Archivos agregados
- `test/test_v30_full_scene.py`
- `CAMBIOS_VISTA_COMPLETA_3D_v30.md`
- `CONTEXTO_PROYECTO_SOMBRA_v30.md`
- `INSTRUCCIONES_REEMPLAZO_v30.md`
