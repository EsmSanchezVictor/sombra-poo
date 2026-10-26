# Cierre de la ronda F3–F7 — v35.6-etapa4.3

La ronda de implementación se apoya en la etapa4.2 de la base actualizada del usuario. Este documento distingue implementación terminada de evidencia externa aún no obtenida. No considera «validado en campo» un modelo por aprobar pruebas unitarias.

| Punto | Implementación de esta ronda | Evidencia externa pendiente |
|---|---|---|
| F3 | Núcleo sin Tk/UI; interacción inyectada y pruebas de física sin entorno gráfico. | Ninguna para este contrato de importación. |
| F4 | Cobertura con alias compatible; límites fotométricos explícitos; exclusiones manuales persistentes; evaluación de máscaras y falsos positivos por material. En 4.3, resúmenes separados por origen/algoritmo, denominadores y exigencia de fotos declaradas reales. | Fotografías reales anotadas y revisadas. La identidad RGB no permite distinguir siempre sombra, copa, asfalto y agua; las exclusiones son manuales. |
| F5 | README, CHANGELOG central, instrucciones, documentación de aceptación y tags Git. `docs/historico/cambios/` queda identificado como archivo histórico. | Ninguna para documentación/versionado. |
| F6 | Conversión de globo, plantillas, separación de campañas e informe reproducible de sesgo/RMSE por modelo, sin aplicar ajustes automáticamente. | Campaña instrumental real y evaluación reservada. No se reportan métricas de campo inexistentes. |
| F7 | Extracciones de física, fotografías, snapshots, validación, sidebar, preferencias, diálogos, Excel y controlador/interacción/backend 3D. Los nombres históricos permanecen disponibles. | La ronda incremental propuesta está implementada; no implica que toda la aplicación haya dejado de depender de SombraApp. |

Un clasificador semántico automático exigiría datos etiquetados y evaluación propia. No se declara implementado ni es equivalente al editor manual. El refactor posterior puede continuar cuando un cambio funcional lo justifique: no se fija un número de líneas como prueba de corrección.

## Lo que se necesita para cerrar la evidencia

1. **Fotos:** copie `validacion/fotos/manifest.plantilla.json` a una carpeta de trabajo. Agregue fotografías y máscaras con las mismas dimensiones. Complete autor y método de anotación. Quite de `confounder_masks` los materiales ausentes; no invente sus máscaras. El conjunto debería cubrir los tres materiales problemáticos en distintas capturas.
2. **Campo:** use `validacion/campo/plantillas/plantilla_validacion_termica.csv` e instrumentos documentados. Reserve campañas completas antes de ajustar; siga [VALIDACION_CAMPO.md](VALIDACION_CAMPO.md).
3. **Windows:** ejecute los controles de componentes y complete el recorrido manual de [ACEPTACION_WINDOWS.md](ACEPTACION_WINDOWS.md).

La anotación de sombra debe establecerse mirando la escena y sus materiales, no copiando la salida del mismo detector evaluado. Use negro para ausencia y blanco para presencia en las máscaras. La ROI selecciona la superficie evaluable; la referencia iluminada debe corresponder a esa misma superficie. No excluya errores del detector solamente para mejorar sus métricas. Para comparar antes/después cree dos casos de la misma foto, con y sin `exclusion_mask`, e identifíquelos así en su `id`. Se cuentan capturas únicas por SHA256 para no presentar esos dos casos como dos fotos independientes.

```bat
python tools/evaluate_shadows.py carpeta_fotos/manifest.json --require-real --report evaluacion_fotos.json
python tools/validate_field_campaign.py mediciones.csv --report evaluacion_campo.json
```

`--require-real` rechaza un banco exclusivamente sintético y exige autor/método de las fotos declaradas reales. No autentica fotografías ni certifica sus etiquetas: esa revisión es humana. Los resúmenes mantienen separados origen y configuración del algoritmo; el umbral estimado por foto se conserva en cada caso. Informe siempre los píxeles de ROI, los excluidos y los evaluados, junto con F1/IoU y falsos positivos por material. Un material sin negativos evaluables no tiene una tasa demostrada: figura sin valor.

Los datos y resultados externos podrán incorporarse en una revisión posterior sin cambiar las ecuaciones ni recalibrar silenciosamente el modelo.
