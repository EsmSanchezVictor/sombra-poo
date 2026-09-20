# CONTEXTO PROYECTO SOMBRA — v35.4

## Base
v35.4 deriva de v35.3, que corrigió el cierre de conexiones SQLite y dejó la suite en 212+ pruebas.

## Cambio principal
Los árboles incorporan `forma_copa`:
`Esférica`, `Cónica`, `Columnar`, `Piramidal`, `Extendida`, `Irregular`, `Llora`.

La propiedad se selecciona al añadir árbol en Edición, puede editarse después y se representa consistentemente en:
- Edición 2D
- Edición 3D
- Modelo 2D
- Modelo 3D
- animación diurna 2D/3D
- fallback Matplotlib 3D

## Persistencia
- Excel formato v3: nueva columna `Forma_copa`.
- Excel antiguo: default `Esférica`.
- Proyecto JSON: conserva forma y especie.
- `ArbolEscena`: conserva `rho_copa`, `especie`, `forma_copa`.

## Decisión metodológica
La forma de copa es visual/geométrica en v35.4. No altera todavía las ecuaciones de sombra, radiación, T superficial, Tmrt o confort. Cualquier extensión física por forma debe implementarse con una parametrización explícita y validación de campo.

## Validación v35.4
- 218 passed, 5 skipped.
- 0 ResourceWarning en modo estricto.
- smoke Tk del diálogo Nuevo Árbol: OK.
- smoke VTK con las siete formas simultáneas: OK.

## Próximo punto recomendable
Si se desea que forma de copa altere también la sombra física, crear factores/calibraciones documentadas por forma y validar contra fotografía/irradiancia de campo antes de activar el cambio en producción.
