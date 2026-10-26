# Memoria metodológica del modelo térmico — v16

## Alcance

El software estima y compara el efecto de sombra, radiación, materiales y vegetación sobre variables microclimáticas en espacios verdes.

La aplicación ofrece un nivel **Estándar**, deliberadamente simple y predeterminado, y niveles **Avanzados** con mayor explicitación física. Un modelo más complejo no se interpreta automáticamente como más exacto: su desempeño debe demostrarse mediante validación.

## 1. Tmrt Estándar

Se conserva la formulación empírica:

`Tmrt = Ta + k · GHI · τ`

con:

- `Ta`: temperatura del aire;
- `GHI`: irradiancia global horizontal;
- `τ`: transmitancia efectiva de la condición de sombra;
- `k`: coeficiente calibrable, 0,04 por defecto.

La transmitancia efectiva de una cobertura de sombra `S` es:

`τeff = (1-S) + S·τsombra`

Por lo tanto 0 % de sombra implica `τeff = 1`.

## 2. Tmrt Avanzada

El modo avanzado utiliza componentes radiativos explícitos:

`K = τ [fp·DNI + fa·DHI + fa·ρg·GHI]`

La onda corta absorbida se transforma a flujo radiativo equivalente mediante la relación entre absorptividad solar humana y emisividad de onda larga.

La onda larga se representa mediante contribuciones de cielo y suelo. En v16 sigue siendo una aproximación simplificada; no sustituye un modelo radiativo 3D tipo SOLWEIG.

## 3. Sombra fotográfica

Se separan dos conceptos:

### Cobertura

Fracción de píxeles válidos clasificados como sombra.

### Atenuación

Reducción fotométrica relativa dentro de la zona sombreada respecto de una referencia iluminada.

El cálculo térmico espacial usa una transmitancia local; la oscuridad ya no se interpreta directamente como porcentaje geométrico de superficie sombreada.

## 4. Temperatura del aire local estimada

Es una variable empírica independiente de Tmrt:

`ΔTa_local = min(ΔTa_max, c_air · (GHI - GHIefectiva))`

Su objetivo es representar que el aire suele cambiar menos que la carga radiativa. Debe calibrarse con mediciones locales antes de usarse como predicción absoluta.

## 5. Balance de superficies Estándar

Se mantiene el balance linealizado histórico para compatibilidad y rapidez.

## 6. Balance avanzado de superficies

El modo avanzado resuelve numéricamente:

`αK↓ + εL↓ - εσTs⁴ - hc(Ts-Ta) - hg(Ts-Tsub) - LE = 0`

El solver exige simultáneamente convergencia térmica y cierre energético. Si una solución queda limitada por el rango numérico, se informa `boundary_clipped` y no se declara convergencia falsa.

## 7. Materiales

Los materiales avanzados distinguen:

- absorptancia solar `α`;
- reflectancia `ρ`;
- transmitancia `τ`;
- emisividad de onda larga;
- conductividad;
- profundidad térmica efectiva;
- capacidad térmica volumétrica.

Para materiales transmisivos se exige:

`α + ρ + τ = 1`

Los valores actuales son representativos y deben reemplazarse por datos certificados cuando se busque predicción absoluta de un producto específico.

## 8. Vegetación y evapotranspiración

El modo `advanced_vegetation` agrega un término latente `LE` basado en una aproximación horaria de Penman–Monteith FAO-56, modificado por:

- fracción de suelo vegetado;
- disponibilidad hídrica;
- Kc;
- LAI/actividad foliar;
- fenología.

La transpiración de copa se mantiene como diagnóstico separado para no restar al suelo energía que pertenece al balance de las hojas.

## 9. Meteorología

Fuentes disponibles:

1. cielo despejado modelado;
2. medición puntual;
3. escenario manual;
4. serie meteorológica observada.

Los datos derivados e interpolados quedan marcados. No se extrapolan series observadas fuera del intervalo disponible.

## 10. Confort térmico

Heat Index y Temperatura Aparente usan temperatura del aire, no Tmrt.

La comparación sol/sombra se realiza mediante Tmrt y, cuando `pythermalcomfort` está disponible, UTCI.

## 11. Incertidumbre

Se utiliza Monte Carlo como **intervalo operativo de sensibilidad**, no como intervalo de confianza metrológico.

El análisis informa P05, P50 y P95 y sensibilidad a los parámetros perturbados.

Cuando existan especificaciones reales de sensores, los supuestos genéricos deben reemplazarse por incertidumbres instrumentales documentadas.

## 12. Calibración y validación

La herramienta separa calibración y validación y calcula:

- MAE;
- RMSE;
- Bias;
- R²;
- n.

El `k_factor` calibrado nunca se aplica automáticamente.

## 13. Trazabilidad

La v16 registra:

- release científico;
- esquema metodológico;
- modelo Tmrt;
- modelo de superficie;
- fuente radiativa;
- calidad meteorológica;
- algoritmo de sombra;
- incertidumbre;
- parámetros de escena.

## 14. Limitaciones actuales

Persisten como refinamientos de investigación:

- SVF espacial 3D;
- onda larga direccional completa;
- separación óptica directa/difusa bajo copa mediante LAI/SVF;
- polígonos de vegetación/suelo húmedo en lugar de fracción global;
- parámetros LAI/Kc específicos para cada especie;
- importación EPW/NetCDF;
- validación experimental externa aún no aportada.

## 15. Interpretación adecuada

La v16 es una plataforma **internamente consistente y preparada para validación**. La precisión científica final no se define por la cantidad de ecuaciones implementadas, sino por el error demostrado frente a observaciones independientes.
