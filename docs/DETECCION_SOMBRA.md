# Cobertura fotométrica y evaluación

shadow_quality era una fracción 0..1 de píxeles clasificados oscuros, no una calidad térmica ni una exactitud del detector. Los estados nuevos guardan shadow_coverage_fraction y leen el nombre antiguo; la propiedad histórica sigue siendo un alias. El análisis fotográfico principal conserva coverage_pct en unidades 0..100.

El umbral de intensidad y la comparación con una referencia iluminada pueden confundir sombra con copa, asfalto, agua o materiales oscuros. Los resultados incluyen semantic_discrimination=false y advertencias. Seleccione la misma superficie al sol y a la sombra y revise la máscara. No se añadió clasificación automática de objetos. En 4.2 se incluye un [editor de exclusiones manuales](EXCLUSIONES_FOTOGRAFICAS.md) mediante rectángulos sobre la rejilla analizada.

La API compute_shadow_coverage acepta una ROI y una exclusion_mask. Las exclusiones se quitan del numerador y del denominador; las máscaras deben ser 2D, finitas y del mismo tamaño. Una ROI vacía devuelve ausencia de valor, no un falso 0%.

```sh
python tools/evaluate_shadows.py test/fixtures/shadow_semantics/manifest.json --report evaluacion_sombra.json
```

Un manifiesto schema_version=1 declara casos con id, image y reference_mask, opcionalmente roi_mask, exclusion_mask y confounder_masks por material. Para el umbral use profile=detector con method/params; para la referencia fotométrica use profile=photo_reference y lit_reference_mask. Las rutas deben permanecer dentro de la carpeta del manifiesto. Las máscaras usan 0 para ausencia y valores positivos para presencia.

Se reportan TP/FP/FN/TN, precisión, recall, F1, IoU, error de cobertura en puntos porcentuales, falsos positivos por material y SHA256 de entradas. Los casos incluidos son controles sintéticos que muestran la ambigüedad de regiones con el mismo RGB. Los iconos de test/imagen y el diagrama test/1.png no son fotografías anotadas. Por eso esta entrega no reporta precisión de campo del detector.


En 4.3 el informe añade `summaries` separados por origen y configuración, y `domain` por caso con tamaño de imagen, ROI, píxeles excluidos y evaluados. Los casos de una misma foto no se presentan como capturas independientes: `unique_real_photo_sha256` cuenta contenido único. `--require-real` exige fotos declaradas reales y autor/método de anotación; no autentica las etiquetas. El banco sintético incluido falla intencionalmente con esa opción. Use la plantilla y las pautas de [CIERRE_CLAUDE.md](CIERRE_CLAUDE.md).
