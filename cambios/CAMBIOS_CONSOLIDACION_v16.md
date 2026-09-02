# v16 — Consolidación, auditoría y preparación para validación

Esta versión cierra el plan de desarrollo de software previo a la campaña experimental.

## Cambios principales

1. **Núcleo solar único** (`core/solar_math.py`)
   - elimina duplicación matemática entre Tmrt, Panel 4 y fallback de SolarEngine;
   - conserva las APIs históricas como wrappers compatibles.

2. **Solver de superficies más robusto**
   - convergencia exige ΔT pequeño y cierre energético;
   - agrega `max_abs_residual_wm2` y `boundary_clipped`;
   - una solución pegada a un límite ya no se marca falsamente como convergente.

3. **Validación de globo metrológicamente explícita**
   - nuevas columnas `globe_diameter_m` y `globe_emissivity`;
   - la conversión Tg→Tmrt usa los valores reales cuando están presentes;
   - si faltan, se registra que se usaron 0.15 m / 0.97 por defecto.

4. **Datos auxiliares de campaña**
   - `surface_temp_c`;
   - `surface_type`;
   - `soil_water_fraction`.

5. **Registro metodológico central** (`core/model_registry.py`)
   - release v16;
   - versiones de Tmrt/superficies/sombra/incertidumbre;
   - etiquetas de fuentes radiativas.

6. **Auditoría científica integrada**
   - menú `Análisis → Auditoría científica / preparación para validación…`;
   - chequeos de dependencias, geometría, materiales, solver, especies, proyecto, trazabilidad y validación;
   - exportación JSON/TXT.

7. **Trazabilidad ampliada**
   - proyecto, snapshots, Excel e informe registran release/esquema metodológico;
   - el informe puede incorporar el último resultado de auditoría.

8. **Dependencias corregidas**
   - `requirements.txt` contiene las dependencias núcleo realmente importadas (`matplotlib`, `Pillow`, `fpdf2` incluidos);
   - `requirements-full.txt` y `requirements-optional.txt` separan pvlib/pythermalcomfort como extensiones científicas.

9. **Documentación final**
   - `AUDITORIA_INTEGRAL_v16.md`;
   - `PROTOCOLO_VALIDACION_CAMPO_v16.md`;
   - `MEMORIA_METODOLOGICA_v16.md`;
   - `CHECKLIST_VALIDACION_v16.md`;
   - `PLAN_TRABAJO_CIENTIFICO_v16.md`;
   - plantilla de instrumentos.

## Validación automática

- 128 tests aprobados.
- 5 tests omitidos por pvlib no disponible en el entorno de ejecución.
- Compilación Python completa sin errores.

## Estado científico

La v16 queda **lista para validación experimental**. Esto no equivale a afirmar que el modelo esté validado externamente. El único bloque que requiere trabajo fuera del software es la campaña de campo y el análisis de sus mediciones independientes.
