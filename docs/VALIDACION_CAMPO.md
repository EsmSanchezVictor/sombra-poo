# Campaña y comparación contra mediciones

Use validacion/campo/plantillas/plantilla_validacion_termica.csv y validacion/campo/plantillas/plantilla_instrumentos_v16.csv. La plantilla ahora incluye campania. Registre identificador, campaña, conjunto (calibracion/validacion), lugar, fecha/hora/zona, instrumentos, altura y procedencia meteorológica. Reserve campañas completas antes del ajuste.

Para convertir globo negro a Tmrt registre Tg, Ta, viento medido, diámetro y emisividad reales. El importador identifica Tmrt observada o convertida y señala geometría/viento asumidos. Para evaluar aire local mida ta_local en los puntos correspondientes; el viento local y el meteorológico de referencia no se intercambian sin documentar la transformación.

```sh
python tools/validate_field_campaign.py mediciones.csv --report informe_campania.json
```

El modo normal exige campañas distintas, identificadores únicos, al menos dos observaciones por conjunto y no descarta silenciosamente filas inválidas. Reporta sesgo, RMSE, MAE, R² y n por modelo, métricas disponibles del aire local, advertencias y SHA256 del CSV. No aplica automáticamente el k sugerido ni modifica preferencias. La autenticidad de mediciones o independencia física de campañas no se acredita solo con etiquetas: revise los registros de instrumentos y la organización de la campaña.

El informe nuevo identifica el balance radiativo avanzado v2 activo en este ZIP. Las columnas canónicas tmrt_avanzado_c y modelo_avanzado acompañan al alias histórico tmrt_avanzado_v1_c de las exportaciones, conservado para compatibilidad; ese nombre antiguo no selecciona la física v1.

Con --diagnostic se permite explorar un holdout interno, identificado como diagnóstico y no como validación independiente. La mejora debe sostenerse en campañas reservadas, considerando incertidumbre de instrumentos y condiciones cubiertas. Los criterios de aceptación se fijan antes de calibrar. En esta entrega solo se probaron informes con datos sintéticos; no se inventaron mediciones reales ni métricas de campo.
