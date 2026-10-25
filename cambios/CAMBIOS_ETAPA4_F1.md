# Etapa 4 · F1 — Modelo Tmrt avanzado v2: área proyectada f_p según elevación solar

Base: v35.6-etapa3.2. Decisión del responsable: `projected_area_mode="elevation"` pasa a ser el **predeterminado**.
El modelo v1 (f_p fijo 0.28) sigue disponible con `AdvancedTmrtConfig(projected_area_mode="fixed")`.

## Por qué
El área proyectada de una persona de pie frente a la radiación directa baja con la elevación solar (≈0.31 en el horizonte, ≈0.10 a 82°). v1 usaba 0.28 siempre. Referencia de la fórmula: regresión de Jendritzky et al. (1990), `f_p = 0.308·cos(γ(0.998 − γ²/50000))`, usada en el Klima-Michel-Modell, RayMan y ERA5-HEAT, e independiente de la orientación de la persona.

## Efecto (Ta 34 °C, GHI 1050, DNI 850, DHI 130, elevación 82°)
| | v1 (fijo 0.28) | v2 (elevación) |
|---|---|---|
| Tmrt al sol | 71.4 °C | 58.9 °C |
| Tmrt en sombra tau 0.30 | 46.6 °C | 42.1 °C |
| ΔTmrt sol–sombra tau 0.30 | 24.8 °C | 16.8 °C |
| ΔTmrt sol–sombra tau 0.15 | 30.9 °C | 20.8 °C |

Con sol bajo (25°) ambos modelos casi coinciden. Los mapas de calor y rankings de árboles con el modelo avanzado dejan de exagerar el beneficio de la sombra al mediodía de verano; el modelo estándar (empírico) no cambia.

## Cambios
- `core/radiative_tmrt.py`: `projected_area_factor_standing()`; `AdvancedTmrtConfig.projected_area_mode` (predeterminado `"elevation"`); el resultado trae `model` = `advanced_radiative_v2|v1` y `projected_area_factor_used`.
- `core/model_registry.py`: versión y etiqueta del modelo avanzado → v2.
- `core/uncertainty.py`: Monte Carlo centrado en f_p(elevación); cada muestra se aplica como valor fijo.
- Etiquetas visibles "balance radiativo v1" → v2 en `ui/app_ui.py`, `ui/panels.py`, `services/report_service.py`, `shadow_temp.py`.
- `test/test_stage4_fp_elevation.py`: 7 pruebas (predeterminado v2, v1 reproducido al decimal, puntos de referencia, monotonía, invariantes físicos, modo inválido, incertidumbre).

## Compatibilidad y trazabilidad
- Los resultados avanzados de proyectos/snapshots anteriores se calcularon con v1 (la versión queda registrada como `advanced_radiative_v1`). Recalcularlos hoy da v2. Para reproducir uno viejo: `projected_area_mode="fixed"`.
- `AdvancedTmrtConfig` no se guarda en los proyectos (siempre usa los valores predeterminados), por lo que no hay migración de archivos.
- NO se cambió `APP_RELEASE` ni `SCIENTIFIC_RELEASE` (`v35.6-etapa3.2`): decidir si se emite una versión nueva (p. ej. etapa4.1) y regenerar `MANIFIESTO_*_SHA256.json` con el flujo habitual.

## Limitaciones que siguen vigentes
- Onda larga con cielo y suelo a Ta (por defecto). Sensibilidad en el caso de arriba: con cielo despejado (ε≈0.78) y suelo entre Ta+10 y Ta+20 K, Tmrt al sol queda entre 56 y 61 °C frente a 58.9 °C: efecto de ±3 °C porque ambos sesgos se compensan. No es una validación.
- Una sola transmitancia para directa, difusa y reflejada.
- Sin calibración con mediciones de campo (globo negro). Ver F6.

## Verificación
28 pruebas ejecutadas con un reemplazo mínimo de pytest y sin Tk: 0 fallos (7 nuevas + 21 de Tmrt avanzado, incertidumbre, procesador de imagen y meteorología). No se pudo correr la suite completa (pytest, Tk, VTK, pvlib). Correr en Windows: `python -m pytest -q -ra -p no:cacheprovider` y `python test/run_optional_fallback.py`.
