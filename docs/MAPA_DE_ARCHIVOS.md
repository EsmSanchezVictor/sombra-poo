# Mapa de archivos

Regla general: **un archivo vive donde se busca por su función, no por la etapa en que se creó.** La raíz queda solo para lo que las herramientas esperan encontrar ahí.

```
sombra-poo/
├─ main.py, app.py              entrada de la aplicación
├─ README.md, CHANGELOG.md      puerta de entrada y registro vigente de cambios
├─ requirements*.txt, *.lock    dependencias (convención: raíz)
├─ core/        física, modelos, validación, estado (sin Tk ni ui)
├─ services/    casos de uso: análisis, informes, almacenamiento, campaña
├─ ui/          ventanas y componentes Tk/VTK
├─ tools/       comandos de línea: comprobaciones, evaluación, campaña, reorganización
├─ test/        pruebas y fixtures
├─ data/        datos de ejecución: settings.json, locations_*.csv, species_db.json
├─ docs/
│   ├─ *.md                     documentación vigente (arquitectura, detección, validación…)
│   ├─ releases/<etapa>/        instrucciones propias de cada entrega
│   ├─ imagenes/                capturas y vistas previas
│   └─ historico/               solo lectura: cambios/, etapas/, manifiestos/
├─ validacion/
│   ├─ estado_actual.json       estado vigente de validación (lo que está y no está acreditado)
│   ├─ windows/<fecha>_<etapa>/ evidencia de escritorio + recorrido manual
│   ├─ qa_linux/<etapa>/        regresión y evidencia sin pantalla
│   ├─ campo/plantillas/        CSV de campaña e instrumentos
│   ├─ campo/campanias/         una carpeta por campaña medida
│   └─ fotos/                   manifiesto de fotografías reales anotadas
└─ respaldos/                   local, fuera de git (bundles, copias)
```

## Dónde pongo…

| Archivo nuevo | Va en |
|---|---|
| Un informe `autocomprobacion*.json` o `escritorio*.json` | `validacion/windows/<AAAA-MM-DD>_<etapa>/` |
| Salida de la regresión o pip check de una etapa | `validacion/qa_linux/<etapa>/` |
| Mediciones de una campaña | `validacion/campo/campanias/<AAAA-MM-DD>_<lugar>/` |
| Instrucciones de una entrega | `docs/releases/<etapa>/INSTRUCCIONES.md` |
| Una nota que ya no rige | `docs/historico/` |
| Un comando nuevo de consola | `tools/` |
| Un módulo nuevo de cálculo / de interfaz | `core/` o `services/` / `ui/` |
| Cuentas, logs, `.bundle`, zips | no se versionan (ver `.gitignore`) |

## Rutas anteriores y nuevas

| Antes | Ahora |
|---|---|
| `autocomprobacion_windows.json`, `escritorio_windows.json` | `validacion/windows/2026-10-25_etapa4.3/` |
| `evidencia_4_3/`, `evidencia_4_2/`, `evidencia_actual/` | `validacion/qa_linux/etapa4.3/`, `etapa4.2/`, `base_recibida/` |
| `VALIDACION_ACTUAL.json` | `validacion/estado_actual.json` |
| `data/plantilla_*.csv` | `validacion/campo/plantillas/` |
| `data/validacion_fotos/manifest.plantilla.json` | `validacion/fotos/manifest.plantilla.json` |
| `INSTRUCCIONES_ACTUAL.md` | `docs/releases/etapa4.3/INSTRUCCIONES.md` |
| `preview_formas_copa_v35_4.png`, `smoke_anim3d_v35_2.png` | `docs/imagenes/` |
| `cambios/` | `docs/historico/cambios/` |
| `PRUEBAS_*`, `REGRESION_*`, `PROMPT_CONTINUIDAD_*`, `VERIFICACION_*`, `INSTALACION_QA_*`, `DEPENDENCIAS_*` | `docs/historico/etapas/` |
| `MANIFIESTO_ETAPA*`, `MANIFIESTO_FUENTES_*`, `AUDITORIA_AUTOMATICA_v16.*` | `docs/historico/manifiestos/` |
| `historial_git/Sombra_actual.bundle` | `respaldos/Sombra_actual.bundle` |

No se movieron: el código, `data/settings.json`, `data/locations_*.csv`, `data/species_db.json`, `users.db`, `requirements*.txt` ni `.gitignore`/`.gitattributes`. Las entradas antiguas de `CHANGELOG.md` y las notas de `docs/historico/` conservan las rutas de su época.

## Pendiente de orden (requiere cambios de código)

Los módulos que siguen en la raíz (`image_processor.py`, `modelo_con_excel.py`, `shadow_temp.py`, `database_manager.py`, `diseno.py`, etc.) los importan código y pruebas por nombre. Moverlos a `core/`, `services/` o `ui/` es una fase aparte, con archivos puente que conserven los nombres actuales y con la regresión completa en cada paso.
