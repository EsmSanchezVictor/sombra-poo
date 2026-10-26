# Guía breve de campaña — validación térmica v10

## Columnas mínimas
Para evaluar Tmrt:
- `ta`: temperatura del aire de referencia (°C)
- `ghi`: radiación global horizontal (W/m²)
- `tmrt` observada (°C) **o** `tg` temperatura de globo (°C)

Si se usa `tg`, conviene incluir `viento` en m/s porque la conversión globo → Tmrt depende de la convección.

## Columnas recomendadas
- `conjunto`: `calibracion` o `validacion`
- `fecha`
- `hora`
- `lat`, `lon`, `timezone`
- `dni`, `dhi`
- `elevacion_solar`
- `sombra_pct`
- `tipo_sombra`: árbol o estructura
- `tau_sombra_total` si se conoce
- `ta_local`: temperatura del aire medida bajo sombra
- `especie`

## Diseño recomendado
1. Tomar mediciones simultáneas o lo más sincronizadas posible.
2. Incluir condiciones de pleno sol y diferentes niveles de sombra.
3. No usar las mismas observaciones para calibrar y declarar validación independiente.
4. Idealmente reservar una fecha/campaña completa para `validacion`.
5. Registrar instrumento, altura de medición y protocolo de exposición fuera del CSV o en la bitácora de campaña.

## Interpretación
- RMSE/MAE menores indican menor error absoluto.
- Sesgo positivo: el modelo sobreestima en promedio.
- Sesgo negativo: subestima.
- R² describe capacidad de reproducir variación, pero no reemplaza MAE/RMSE ni el análisis del sesgo.
- La comparación científica principal debe realizarse sobre el conjunto `validacion`.
