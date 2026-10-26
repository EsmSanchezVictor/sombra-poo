# Validación

Aquí vive toda la evidencia de que el software funciona (instalación, ventanas, regresión) y de que sus resultados se parecen a la realidad (campo). Son cosas distintas: lo primero se puede automatizar; lo segundo exige mediciones.

## Qué está acreditado y qué no

| Aspecto | Estado | Evidencia |
|---|---|---|
| Instalación y cálculos en Windows | Aprobado (Windows 10 build 19045, Python 3.12.10, etapa 4.3) | `windows/2026-10-25_etapa4.3/autocomprobacion_windows.json` |
| Componentes Tk, editor de fotos, Matplotlib 3D y VTK en Windows | Aprobado (automático) | `windows/2026-10-25_etapa4.3/escritorio_windows.json` |
| Recorrido manual de la aplicación completa en Windows | **Pendiente** | `windows/2026-10-25_etapa4.3/recorrido_manual.md` |
| Regresión sin pantalla (Linux) | 615 pruebas aprobadas según `docs/VALIDACION_ACTUAL.md` (no re-ejecutadas aquí) | `qa_linux/etapa4.3/` |
| Fotografías reales anotadas | **Pendiente** (el banco actual es sintético) | `fotos/` |
| Validación de campo (Tmrt, aire local, superficie) | **Pendiente** | `campo/campanias/` |

Los dos JSON de Windows declaran `human_visual_review: false`, `full_app_workflow_tested: false` y `field_validation: false`: un `passed` acredita esos componentes, no la revisión visual de toda la aplicación ni la exactitud científica.

## Carpetas

- `estado_actual.json`: estado vigente en formato máquina. Se actualiza en cada entrega.
- `windows/<AAAA-MM-DD>_<etapa>/`: los dos JSON de `tools/check_installation.py` y `tools/check_desktop.py` más el recorrido manual completado.
- `qa_linux/<etapa>/`: regresión, `pip check` y evidencia sin pantalla.
- `campo/plantillas/`: CSV de mediciones, instrumentos y meteorología observada.
- `campo/campanias/`: una carpeta por campaña (ver su README).
- `fotos/`: manifiesto de fotografías reales anotadas (`tools/evaluate_shadows.py --require-real`).

## Comandos

```bat
.venv\Scripts\python tools\check_installation.py --require-full --report autocomprobacion_windows.json
.venv\Scripts\python tools\check_desktop.py --vtk --require-windows --report escritorio_windows.json
.venv\Scripts\python tools\validate_field_campaign.py validacion\campo\campanias\<campania>\mediciones.csv --report validacion\campo\campanias\<campania>\informe.json
```

Después de cada comprobación en Windows, mueva los JSON a `windows/<fecha>_<etapa>/`.
