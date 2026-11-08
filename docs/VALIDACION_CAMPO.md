# Campaña y comparación contra mediciones

Use validacion/campo/plantillas/plantilla_validacion_termica.csv y validacion/campo/plantillas/plantilla_instrumentos_v16.csv. La plantilla ahora incluye campania. Registre identificador, campaña, conjunto (calibracion/validacion), lugar, fecha/hora/zona, instrumentos, altura y procedencia meteorológica. Reserve campañas completas antes del ajuste.

Para convertir globo negro a Tmrt registre Tg, Ta, viento medido, diámetro y emisividad reales. El importador identifica Tmrt observada o convertida y señala geometría/viento asumidos. Para evaluar aire local mida ta_local en los puntos correspondientes; el viento local y el meteorológico de referencia no se intercambian sin documentar la transformación.

```sh
python tools/validate_field_campaign.py mediciones.csv --report informe_campania.json
```

El modo normal exige campañas distintas, identificadores únicos, al menos dos observaciones por conjunto y no descarta silenciosamente filas inválidas. Reporta sesgo, RMSE, MAE, R² y n por modelo, métricas disponibles del aire local, advertencias y SHA256 del CSV. No aplica automáticamente el k sugerido ni modifica preferencias. La autenticidad de mediciones o independencia física de campañas no se acredita solo con etiquetas: revise los registros de instrumentos y la organización de la campaña.

El informe nuevo identifica el balance radiativo avanzado v2 activo en este ZIP. Las columnas canónicas tmrt_avanzado_c y modelo_avanzado acompañan al alias histórico tmrt_avanzado_v1_c de las exportaciones, conservado para compatibilidad; ese nombre antiguo no selecciona la física v1.

Con --diagnostic se permite explorar un holdout interno, identificado como diagnóstico y no como validación independiente. La mejora debe sostenerse en campañas reservadas, considerando incertidumbre de instrumentos y condiciones cubiertas. Los criterios de aceptación se fijan antes de calibrar. En esta entrega solo se probaron informes con datos sintéticos; no se inventaron mediciones reales ni métricas de campo.

## Protocolo mínimo para la próxima campaña

- Hacé un piloto con puntos al sol, bajo árboles y bajo estructuras, con horarios y condiciones comparables. Registrá tipo de superficie, altura de sensores, fecha/hora, viento, radiación, temperatura y humedad de referencia. Para aire local, medí simultáneamente la referencia y el punto a la sombra; documentá protección radiativa y ubicación de sensores.
- Si se usa globo, guardá por separado **Tg, Ta junto al globo, viento junto al globo, diámetro y emisividad** y la **Ta de referencia del escenario**. En esta versión, el importador que convierte automáticamente `tg` usa la columna `ta`; no distingue la Ta junto al globo de la referencia. Además, la conversión implementada solo contiene el término de convección forzada. Antes de aceptar filas con globo, revisá el método para el instrumento y las condiciones, en especial con viento débil. Si ambas Ta difieren, conservá las variables crudas y cargá en `tmrt` la referencia calculada externamente por un método documentado. No uses la misma lectura de aire para los dos roles sin justificación.
- Definí de antemano criterios de error compatibles con el uso previsto y la incertidumbre del equipo. Separá campañas completas de calibración y validación; el mínimo que admite la herramienta es un control de formato, no un tamaño de muestra suficiente. Conservá predicciones originales y trazabilidad de cualquier ajuste.
- Con la herramienta actual, reportá **n, sesgo, MAE y RMSE** para Tmrt y para aire local cuando haya pares. Para **temperatura de superficie**, cotejá manualmente o en un informe separado la medición y la celda simulada a la misma hora y ubicación; la columna de superficie no produce por sí sola sus métricas en el informe de campaña. Separá temperatura de aire, superficie y Tmrt.
- Para fotos, anotá máscaras de referencia sin mirar primero la máscara que entrega Sombra. Usá `tools/evaluate_shadows.py` con `--require-real`; registrá autor, método y criterios de anotación. La opción verifica que haya metadatos y casos declarados reales, no comprueba su autenticidad.

Archivá los registros de instrumentos, datos originales, configuraciones de simulación, informe de comparación y alcance de la conclusión. No apliques una calibración definitiva hasta probarla en los conjuntos reservados.
