# v19 — Organización integral y guardado automático del proyecto

## Objetivo

La v19 reorganiza la persistencia para que cada dato generado tenga un destino único, estable y relativo a la carpeta raíz del proyecto. Se elimina el uso de nombres versionados para resultados vivos y se reserva el versionado únicamente para entradas externas realmente diferentes y para respaldos explícitos.

## Estructura canónica

```text
<Proyecto>/
├── <Proyecto>.sombra
├── config/
│   ├── project.json
│   ├── estructura.json
│   └── inventario.json
├── entradas/
│   ├── imagenes/
│   ├── meteorologia/
│   └── validacion/
├── escena/
│   ├── edicion.xlsx
│   └── modelo.xlsx
├── analisis/
│   ├── analisis.sqlite3
│   ├── elementos/
│   │   └── <analysis_id>/
│   │       ├── areas/
│   │       ├── sombra/
│   │       └── termico/
│   └── dataset/
├── resultados/
│   ├── proyecto/
│   ├── validacion/
│   └── informes/
├── respaldos/
└── _legacy_v18/        # solo si hubo migración de contenido antiguo
```

### Por análisis

Cada árbol/imagen analizada conserva un `analysis_id` único. Su carpeta contiene:

- `areas/matriz_calculo.xlsx`
- `areas/matriz_referencia.xlsx`
- `areas/calculo.npz`
- `areas/referencia.npz`
- `areas/mascara_seleccion.png`
- `sombra/analisis_fotografico.npz`
- `sombra/histograma.png`
- `sombra/clasificacion_sombra.png`
- `termico/datos_tmrt.npz`
- `termico/curva_tmrt.png`
- `termico/resumen_tmrt.png`

La base `analisis/analisis.sqlite3` es la fuente primaria para el carrusel y enlaza estos artefactos con cada análisis.

## Guardado automático

El proyecto vivo se guarda automáticamente sin pedir rutas:

- el estado principal se actualiza en `<Proyecto>.sombra`;
- `config/project.json` se mantiene como copia secundaria compatible;
- Edición se actualiza en `escena/edicion.xlsx`;
- Modelo se actualiza en `escena/modelo.xlsx`;
- los análisis se guardan en su carpeta por `analysis_id`;
- los resultados globales tienen nombres estables;
- se actualiza `config/inventario.json`.

Los cambios en variables editables disparan autosave con debounce. Durante la apertura/migración se suspende ese seguimiento para que restaurar datos no sea interpretado como una edición del usuario.

## Semántica de Guardar

- **Autosave:** actualiza silenciosamente el proyecto vivo.
- **Guardar respaldo / Ctrl+S:** fuerza la consolidación y crea un `.3es` timestampado dentro de `respaldos/`. No pregunta ubicación.
- **Respaldar Excel / PDF / Dataset / análisis:** escriben directamente en la carpeta canónica correspondiente. No preguntan ubicación.
- **Guardar como…:** es la única acción de guardado que pregunta un destino y crea una nueva carpeta de proyecto.
- **Exportar .3es…:** sigue preguntando ubicación porque es una exportación externa, no el guardado ordinario.

Se conservan como máximo los 10 respaldos `.3es` más recientes del proyecto. Los respaldos no se incluyen dentro de otros respaldos ni de `Guardar como`.

## Inventario

`config/inventario.json` enumera los archivos vivos del proyecto con tamaño y fecha de modificación. Excluye deliberadamente `respaldos/` y `_legacy_v18/` para no confundir histórico con estado vigente.

## Migración

Al abrir un proyecto v18/v17 o anterior:

- `imagenes/` pasa a `entradas/imagenes/`;
- `meteorologia/` pasa a `entradas/meteorologia/`;
- `datos/analisis.sqlite3` pasa a `analisis/analisis.sqlite3`;
- los artefactos del carrusel se reubican según su `analysis_id`;
- Edición y Modelo se consolidan como `escena/edicion.xlsx` y `escena/modelo.xlsx`;
- resultados conocidos se clasifican por proyecto, validación o informes;
- contenido antiguo que no puede reasignarse de forma inequívoca se conserva en `_legacy_v18/`, nunca se elimina silenciosamente.

La migración se persiste inmediatamente en las rutas v19.

## Correcciones adicionales de consolidación

- `Project.from_config_path()` normaliza cualquier `.sombra` o JSON legacy a `config/project.json` como ruta secundaria canónica.
- Se corrigió un doble llamado accidental que generaba dos respaldos por cada `Guardar`.
- Duplicar proyecto y Guardar como ya no copian el historial de respaldos del proyecto fuente.
- Los resultados vivos se sobrescriben en nombres estables; ya no proliferan `_v2`, `_v3`, etc.
