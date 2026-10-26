# Proyecto Sombra v35.4 — Formas de copa 2D/3D

Base: **v35.3**.

## Nueva propiedad de árbol
Se agrega `forma_copa` con las opciones:
- Esférica
- Cónica
- Columnar
- Piramidal
- Extendida
- Irregular
- Llora

La forma predeterminada es **Esférica** para conservar compatibilidad visual con proyectos antiguos.

## Interfaz
En **Edición > Añadir árbol** se agregó el campo **Forma de copa** como lista cerrada.
También puede modificarse posteriormente al editar el árbol. En Modelo, el editor de árbol permite modificar la misma propiedad.

## Representación 2D
Edición, Modelo y el reproductor diurno 2D usan ahora una geometría de planta de copa en unidades reales del gráfico, en lugar de un `scatter` genérico.
Cada forma posee simbología propia:
- Esférica: copa circular.
- Cónica: planta circular con lectura concéntrica/radial.
- Columnar: copa estrecha y alargada.
- Piramidal: símbolo romboidal/piramidal.
- Extendida: copa ancha y aplanada.
- Irregular: contorno asimétrico.
- Llora: copa lobulada/pendular.

## Representación 3D
El renderer VTK compartido por Edición y Modelo representa perfiles diferenciados:
- Esférica: volumen multilobulado redondeado.
- Cónica: cono de revolución.
- Columnar: elipsoide vertical estrecho.
- Piramidal: pirámide de base cuadrada.
- Extendida: volumen bajo y extendido lateralmente.
- Irregular: combinación asimétrica de volúmenes.
- Llora: núcleo superior con lóbulos colgantes.

El fallback Matplotlib 3D reproduce las mismas siete categorías.
La animación diurna 3D hereda las formas porque reutiliza el mismo renderer de escena.

## Persistencia
- Excel: `Árboles` incorpora la columna `Forma_copa`.
- `FORMAT_VERSION` de Excel pasa de 2 a 3.
- Los Excel antiguos sin esa columna se cargan automáticamente como `Esférica`.
- El JSON del proyecto conserva `forma_copa` y también `especie` en los objetos de árbol.
- `ArbolEscena` conserva forma, especie y densidad de copa.

## Alcance científico
La forma de copa en v35.4 es un atributo **geométrico de representación**.
No modifica todavía el kernel de sombra/radiación. Esto evita introducir una nueva parametrización física no validada. El cálculo de sombra sigue usando el modelo previo; la arquitectura queda preparada para una futura calibración por forma de copa.

## Validación
- `python -m compileall -q .`: OK.
- Suite completa: **218 passed, 5 skipped**.
- Suite con `ResourceWarning` convertido en error: **218 passed, 5 skipped**.
- Smoke test del diálogo `Nuevo Árbol`: las siete opciones están disponibles.
- Smoke test VTK real: las siete formas se renderizan simultáneamente sin excepción.
