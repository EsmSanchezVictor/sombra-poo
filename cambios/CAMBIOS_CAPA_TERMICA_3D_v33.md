# Proyecto Sombra — v33

## Objetivo
Separar visualmente la información térmica de los elementos físicos en la vista 3D, sin modificar ningún cálculo científico.

## Cambios visuales
- Capa térmica VTK con opacidad 50 %.
- La capa térmica no recibe iluminación para conservar la lectura cromática.
- Base física del terreno clara y neutra bajo la capa térmica.
- Seis isotermas adaptativas dentro del rango real de temperatura visible.
- Isotermas con doble trazo: contorno oscuro + línea coloreada por la misma LUT térmica.
- Árboles casi opacos y con mayor contraste de iluminación.
- Paredes, galerías y senderos opacos, con bordes oscuros finos.
- Fallback Matplotlib actualizado a 50 % de transparencia e isotermas.

## Principio científico
Las isotermas y la capa térmica consumen exclusivamente X, Y y T ya calculados. No recalculan Tmrt, Ta, radiación, sombra, confort ni balances térmicos.

## Validación
- Suite automática: 194 passed, 5 skipped.
- Render VTK real de validación ejecutado con VTK 9.6.2.
- Compatibilidad v32 con VTK 9.7 preservada (`AddViewProp` para la barra de colores).

## Archivos modificados
- `ui/scene3d.py`

## Archivos agregados
- `test/test_v33_thermal_layers.py`
- `CAMBIOS_CAPA_TERMICA_3D_v33.md`
- `CONTEXTO_PROYECTO_SOMBRA_v33.md`
- `INSTRUCCIONES_REEMPLAZO_v33.md`
