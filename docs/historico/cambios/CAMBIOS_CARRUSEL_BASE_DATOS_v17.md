# v17 — Carrusel persistente por análisis

## Objetivo

El carrusel inferior del Panel 2 deja de funcionar como historial de acciones y pasa a funcionar como **selector de análisis persistidos**. Cada miniatura representa un árbol/imagen con un `analysis_id` estable y con todos los datos necesarios para reconstruir su estado sin recalcular.

## Bug corregido

En v16 `_carrusel_seleccionar()` llamaba a `cargar_snapshot(index)` y luego a `mostrar_curvas_nivel()`. Esta segunda llamada generaba otro histograma y `_registrar_histograma_en_carrusel()` hacía `append`, por lo que un simple clic podía duplicar la imagen.

En v17 el clic es de solo lectura:

1. localiza el registro seleccionado;
2. restaura sus artefactos y valores;
3. marca la miniatura activa;
4. **no ejecuta ninguna física ni vuelve a registrar el elemento**.

## Base de datos

Se agregó `services/analysis_record_store.py` con SQLite estándar de Python.

La base vive dentro del proyecto:

`datos/analisis.sqlite3`

Por estar dentro de la carpeta del proyecto, se copia al duplicar y se incluye al exportar `.3es`.

La tabla `analysis_records` usa `analysis_id` como clave primaria. Guardar o recalcular un árbol existente hace `UPSERT`; no genera un segundo registro.

El JSON `.sombra` mantiene `snapshots` como cache compatible para reportes y proyectos anteriores, pero SQLite es la fuente primaria del carrusel.

## Datos asociados a cada miniatura

Cada registro conserva:

- foto original del árbol;
- curva de nivel Tmrt;
- matriz del área de cálculo;
- máscara válida del área de cálculo;
- máscara full-size del área de cálculo;
- matriz del área de referencia;
- máscara válida del área de referencia;
- máscara full-size del área de referencia;
- geometría dibujada de ambas áreas;
- histograma;
- máscara de clasificación sombra/sol si fue generada;
- matrices del mapa Tmrt necesarias para recuperar el hover sin recalcular;
- mapas fotográficos de sombra/transmitancia/atenuación;
- valor/leyenda de área de cálculo;
- valor/leyenda de área de referencia;
- cantidad de píxeles válidos de cada área;
- promedio gris de referencia;
- cobertura de sombra;
- atenuación en sombra;
- transmitancia de sombra;
- transmitancia efectiva;
- umbral fotográfico;
- Tmrt sol/sombra/delta cuando existen;
- modelo y procedencia radiativa.

## Restauración al hacer clic

Al seleccionar una miniatura se restaura exactamente:

1. foto original;
2. área/máscara de cálculo;
3. área/máscara de referencia;
4. los overlays azul/rojo;
5. los textos de áreas;
6. promedio gris;
7. cobertura de sombra;
8. atenuación en sombra;
9. transmitancia efectiva;
10. curva de nivel desde matrices guardadas;
11. datos locales del hover Tmrt cuando existen;
12. resultados escalares Tmrt cuando fueron calculados.

No se llama a `mostrar_curvas_nivel()` durante la selección.

## Máscaras

Los snapshots antiguos guardaban principalmente las matrices Excel y, al restaurar, asumían una máscara de `True` para toda la matriz. Eso perdía la forma exacta de polígonos/círculos.

v17 guarda bundles NPZ comprimidos con:

- `values`;
- `valid_mask`;
- `full_mask`.

Esto preserva exactamente los píxeles incluidos/excluidos.

## Foto del árbol

v16 guardaba como imagen del snapshot un `fig.savefig()`, que podía contener ejes y overlays. v17 referencia la **foto original copiada dentro del proyecto**. Los overlays se reconstruyen desde las geometrías/máscaras asociadas.

## Compatibilidad

Al abrir un proyecto <= v16:

- los snapshots formales del JSON se migran automáticamente a SQLite;
- las entradas `provisional=True` no se muestran porque no contienen un análisis completo;
- el patrón conocido de duplicado v16 (`elementoN` con las mismas ROIs y métricas que el registro anterior) se colapsa conservadoramente;
- si faltan NPZ nuevos, se usan los Excel y artefactos legacy como fallback.

## Pruebas

Suite v17 en el entorno de desarrollo:

- **135 tests aprobados**;
- **5 omitidos** por las pruebas opcionales que requieren pvlib.

Se agregaron pruebas de:

- UPSERT sin duplicados;
- migración idempotente;
- exclusión de provisionales;
- limpieza del patrón de duplicación v16;
- ubicación portable de SQLite;
- clic de carrusel de solo lectura;
- persistencia completa de foto, áreas, métricas y mapas.
