# Campañas de campo

Una carpeta por campaña, con nombre `AAAA-MM-DD_lugar` (fecha del primer día medido), por ejemplo `2026-12-03_parana-parque-urquiza`.

```
AAAA-MM-DD_lugar/
├─ protocolo.md        criterios de aceptación y diseño, escritos ANTES de medir
├─ instrumentos.csv    copia completa de ../plantillas/plantilla_instrumentos_v16.csv
├─ mediciones.csv      copia completa de ../plantillas/plantilla_validacion_termica.csv
├─ informe.json        salida de tools/validate_field_campaign.py (no editar a mano)
├─ anexos/             fotos de los puntos, esquema del sitio, hojas de campo escaneadas
└─ crudos/             registros originales del datalogger/globo (ignorada por git)
```

## Antes de medir

1. **Escriba `protocolo.md` y fije los criterios de aceptación** (por ejemplo, el sesgo y el RMSE máximos tolerados en °C para cada modelo), teniendo en cuenta la incertidumbre de sus instrumentos. El proyecto no define umbrales por usted y el informe no aplica ninguna calibración.
2. **Separe calibración de validación por campaña completa**: una campaña (o más) con `conjunto = calibracion` y otras, distintas y reservadas, con `conjunto = validacion`. El modo normal de `validate_field_campaign.py` exige campañas distintas, identificadores únicos y al menos dos observaciones por conjunto. Un holdout interno solo sirve para explorar (`--diagnostic`) y no es validación independiente.
3. **Complete `instrumentos.csv`**: marca, modelo, número de serie, resolución, exactitud, fecha de calibración y altura de cada sensor.
4. **Cubra condiciones distintas**: puntos al sol y a la sombra del mismo lugar, y horas con elevación solar baja, media y alta. Una validación hecha solo al mediodía no dice nada de la mañana.

## Qué registrar por fila (ver la plantilla)

- Fecha, hora y zona horaria; latitud y longitud; sombra (porcentaje y tipo) y especie si es arbolado.
- Meteorología de referencia con su procedencia (GHI/DNI/DHI y viento medidos o tomados de una estación; indique cuál).
- Si usa globo negro: `tg`, `ta`, viento medido junto al globo, `globe_diameter_m` y `globe_emissivity` reales. La conversión a Tmrt depende de ellos; respete el tiempo de equilibrio que indique la norma o el fabricante para su globo.
- Para aire local, `ta_local` en el punto medido. El viento local y el meteorológico de referencia no se intercambian sin documentar la transformación.

## Después de medir

```bat
.venv\Scripts\python tools\validate_field_campaign.py validacion\campo\campanias\<campania>\mediciones.csv --report validacion\campo\campanias\<campania>\informe.json
```

Revise el informe contra `protocolo.md` y registre la conclusión en `validacion/estado_actual.json`. Las etiquetas de campaña no prueban por sí solas que las mediciones sean auténticas ni que las campañas sean físicamente independientes: eso se acredita con los registros de instrumentos y la organización de la campaña.
