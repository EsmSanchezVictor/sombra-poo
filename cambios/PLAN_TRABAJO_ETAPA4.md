# Plan de trabajo — Etapa 4 (base v35.6-etapa3.2)

Principios: cambios pequeños y acumulativos; sin tocar resultados existentes sin versionar el modelo; cada fase con prueba y criterio de cierre; no declarar validado nada que no se haya medido.

| Fase | Trabajo | Prioridad | Esfuerzo | Riesgo | Cierre cuando… |
|---|---|---|---|---|---|
| F0 | Línea base: ejecutar la suite completa en Windows (pytest, Tk, VTK, pvlib) y registrar resultados en `CONTROL_WINDOWS_ETAPA3_2.md` | Alta | 0.5 d | Bajo | Tabla de control completa con evidencia |
| F1 | **f_p dependiente de la elevación** — HECHO | Alta | — | Bajo | 7 pruebas nuevas verdes |
| F1b | **`elevation` como predeterminado = `advanced_radiative_v2`** — HECHO (fórmula de Jendritzky et al. 1990). Falta: decidir versión/manifiesto de la release y exponer el modo en la UI | Alta | 0.5 d | Medio | Release nueva + manifiesto SHA256 |
| F2 | Higiene del repo: `scripts/limpiar_repo.ps1`. **Decisión: dejar de rastrear `users.db`** (la app la regenera: `needs_initial_admin` / `create_initial_admin`); no reescribir historial salvo que la cuenta use una contraseña reutilizada, en cuyo caso cambiarla | Alta | 0.5 d | Bajo | `git status` limpio de db/log/zip/pyc |
| F1c | Onda larga realista: pasar temperaturas de suelo (`surface_energy`) y emisividad de cielo (Brutsaert) a `calculate_radiative_tmrt`; separar transmitancia directa/difusa/reflejada (SVF/LAI) | Media | 2–3 d | Medio | Comparación contra F6 con menor sesgo |
| F3 | Desacoplar `core/` de Tkinter (`core/app_state.py` importa `tkinter`/`messagebox`): mover diálogos a `ui/` | Media | 1–2 d | Medio | `import core.*` sin Tk; las pruebas de física se ejecutan sin entorno gráfico |
| F4 | Semántica de detección de sombra: renombrar `shadow_quality`→cobertura; distinguir sombra de objetos oscuros (copa, asfalto, agua); casos con imágenes de `test/imagen` | Media | 2 d | Medio | Pruebas con imágenes reales; documentación del límite |
| F5 | Documentación: README raíz, `CHANGELOG.md` único, etiquetas git; archivar `cambios/` históricos | Media | 0.5 d | Bajo | README con instalación, uso y estado de validación |
| F6 | Validación de campo: globo negro (`globo_negro_a_tmrt`), plantillas `data/plantilla_validacion_termica.csv`; comparar modelo vs medición | Alta (científica) | Campaña | — | Sesgo/RMSE reportados por modelo |
| F7 | Refactor incremental de `ui/app_ui.py` (4984 líneas), `dialogs.py`, `scene3d.py`, `modelo_con_excel.py` | Baja | Continuo | Alto | Módulos <1000 líneas sin cambiar flujos ni pruebas |

Orden recomendado: F0 → F1b → F2 → F3 → F5 → F4 → F6 (en paralelo desde que haya instrumentos) → F7.

## Decisiones tomadas
1. f_p por elevación = modelo avanzado predeterminado (v2). Hecho.
2. `users.db`: no se versiona (se deja de rastrear, se conserva en tu disco). Sin purga de historial por defecto.
3. Subir a GitHub la versión del zip: pendiente de tu commit.
