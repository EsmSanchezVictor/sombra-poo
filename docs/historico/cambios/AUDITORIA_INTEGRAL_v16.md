# Auditoría integral del proyecto — v16

## Objetivo

La v16 no agrega un nuevo modelo físico principal. Su función es consolidar y auditar todo lo incorporado entre v5 y v15 antes de pasar a validación experimental de campo.

La auditoría se realizó sobre cuatro ejes:

1. consistencia matemática y numérica;
2. consistencia entre módulos y rutas de la interfaz;
3. trazabilidad de parámetros, modelos y fuentes de datos;
4. preparación para validación externa.

## Correcciones de consolidación aplicadas

### 1. Geometría solar única

Se creó `core/solar_math.py` como núcleo analítico compartido.

Antes existían implementaciones paralelas en `shadow_temp.py` y `modelo_con_excel.py`. Eran similares, pero podían divergir en futuras correcciones. Ahora:

- `shadow_temp.Temperatura` delega en el mismo núcleo;
- `modelo_con_excel` conserva sus funciones públicas por compatibilidad, pero delega en el núcleo;
- `SolarEngine` usa el mismo núcleo cuando pvlib no está disponible.

Esto evita que Panel 1/2, Panel 4 y el fallback solar produzcan posiciones solares distintas para el mismo instante.

### 2. Solver de superficies: convergencia real

Se corrigió un caso numérico importante en `core/surface_energy.py`.

Antes, si Newton proponía una temperatura fuera de los límites y el resultado quedaba recortado en `min_surface_k` o `max_surface_k`, el cambio de temperatura podía ser cero y el solver podía interpretar eso como convergencia aunque el balance energético siguiera abierto.

Ahora se exigen simultáneamente:

- convergencia en temperatura;
- residual energético menor que `residual_tolerance_wm2`.

Además se informan:

- `max_abs_residual_wm2`;
- `boundary_clipped`;
- `converged`.

Un caso saturado en un límite ya no puede declararse falsamente convergente.

### 3. Validación con globo: geometría instrumental explícita

El CSV de validación acepta ahora:

- `globe_diameter_m`;
- `globe_emissivity`.

Si se suministran, la conversión Tg → Tmrt utiliza las propiedades reales del instrumento. Si faltan, se conservan los valores estándar del proyecto:

- diámetro = 0,15 m;
- emisividad = 0,97.

La salida marca `globe_geometry_default` y genera una advertencia cuando esos valores fueron asumidos.

### 4. Variables de campaña adicionales

La plantilla de validación admite además:

- temperatura superficial observada;
- tipo de superficie;
- fracción/disponibilidad hídrica del suelo.

Estas variables no se fuerzan dentro de la calibración Tmrt actual; se preservan para validar de manera separada el balance de superficies y la vegetación.

### 5. Registro metodológico único

Se creó `core/model_registry.py`, que centraliza:

- release científico;
- esquema metodológico;
- versiones de modelos Tmrt;
- versiones de modelos de superficie;
- fuentes radiativas;
- algoritmo fotográfico;
- método de incertidumbre.

El proyecto, Excel y snapshots registran esta información para evitar resultados sin versión metodológica identificable.

### 6. Auditoría científica dentro de la aplicación

Se agregó:

**Análisis → Auditoría científica / preparación para validación…**

La herramienta comprueba automáticamente:

- dependencias requeridas;
- dependencias opcionales;
- base de zonas horarias;
- geometría solar;
- invariantes de sombra;
- cierre óptico de materiales;
- propiedades genéricas de especies;
- cierre del balance energético;
- diagnóstico de saturación numérica;
- estructura del proyecto;
- modos metodológicos;
- trazabilidad de snapshots;
- existencia o ausencia de validación experimental.

La auditoría puede exportarse a JSON o TXT.

## Resultado de la auditoría en el entorno de desarrollo

Estado interno:

**APTO CON ADVERTENCIAS: listo para campaña, no para afirmar validación externa.**

No se detectaron fallas internas en los chequeos automáticos de la v16.

Advertencias esperadas del entorno de prueba:

- `pvlib` no está instalado;
- `pythermalcomfort` no está instalado;
- las propiedades avanzadas de materiales son valores representativos;
- LAI/Kc siguen siendo genéricos para la biblioteca actual de especies;
- no existe una campaña experimental real cargada en este entorno.

## Suite de pruebas

Resultado v16:

- **128 tests aprobados**;
- **5 omitidos** porque requieren pvlib en el entorno de prueba.

Los tests nuevos verifican específicamente:

- equivalencia entre las rutas solares históricas y el núcleo compartido;
- que un solver recortado no declare convergencia falsa;
- que la auditoría no detecte fallas internas;
- uso real de diámetro y emisividad de globo proporcionados por campaña;
- identificación explícita de geometría de globo asumida.

## Qué NO puede cerrar el software por sí solo

La siguiente evidencia requiere trabajo experimental y no debe simularse mediante código:

1. validación independiente de Tmrt;
2. calibración del `k_factor` con datos locales;
3. validación de temperatura del aire local bajo sombra;
4. validación de cobertura fotográfica de sombra;
5. validación de temperatura superficial;
6. calibración específica de LAI/Kc/transmitancia por especie;
7. caracterización metrológica real de los sensores.

Por eso, la v16 debe considerarse una versión **lista para validación**, no una versión “científicamente validada” sin campaña de campo.
