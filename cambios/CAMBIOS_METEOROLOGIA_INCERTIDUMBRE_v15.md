# v15 — Meteorología observada + incertidumbre científica

Esta versión integra los dos bloques finales del plan científico iniciado en v9.

## 1. Fuentes radiativas explícitas
La aplicación distingue cuatro procedencias:

- `clear_sky`: cielo despejado modelado. Usa pvlib/Ineichen si está habilitado y disponible; de lo contrario, el fallback analítico del proyecto.
- `manual_measured`: medición puntual ingresada por el usuario.
- `manual_scenario`: escenario radiativo hipotético/manual.
- `observed_series`: serie meteorológica CSV importada.

El modo predeterminado continúa siendo `clear_sky`, por lo que el flujo previo no se altera.

## 2. Series meteorológicas CSV
Nuevo módulo `core/meteorology.py` + `services/meteorology_service.py`.

Variables admitidas, con aliases en castellano e inglés:

- timestamp o fecha + hora;
- GHI;
- DNI;
- DHI;
- temperatura del aire (°C);
- humedad relativa (%);
- viento (m/s);
- nubosidad como fracción 0–1 o porcentaje 0–100.

Al importar una serie dentro de un proyecto se copia a `meteorologia/`, de modo que queda incluida al exportar el proyecto `.3es`.

### Política temporal
- dato exacto: `observed`;
- entre dos observaciones: interpolación lineal solo si el hueco es <= 90 min por defecto;
- no se extrapola fuera del período de la serie;
- un hueco mayor al permitido produce un error visible en vez de inventar valores.

## 3. DNI/DHI faltantes
Los valores observados no se reescriben silenciosamente.

- con dos componentes se deriva la tercera por `GHI = DNI*sin(elev) + DHI`;
- si solo existe GHI, DNI/DHI se estiman mediante descomposición Erbs;
- cada componente derivado queda marcado en `derived_components`;
- si GHI/DNI/DHI medidos no cierran, se conserva la medición y se genera una advertencia de trazabilidad.

## 4. Uso de meteorología observada
Al seleccionar `observed_series`:

- Tmrt usa GHI/DNI/DHI de la serie;
- si existe Ta observada, reemplaza la Ta manual de ese instante;
- Panel 4 usa Ta, RH, viento y nubosidad observados cuando están disponibles;
- la fuente y su calidad se guardan en snapshots, Excel, proyecto e informe.

## 5. Compatibilidad del Panel 4
Para no romper resultados históricos:

- con `clear_sky`, el Panel 4 conserva su flujo radiativo legacy;
- con `manual_measured`, `manual_scenario` u `observed_series`, el balance recibe GHI directo del instante mediante override explícito.

Esto permite comparar resultados nuevos con estudios previos sin cambiar el comportamiento por defecto.

## 6. Incertidumbre operativa Monte Carlo
Nuevo `core/uncertainty.py`.

Se calcula un intervalo P05–P95 para:

- Tmrt al sol;
- Tmrt bajo sombra;
- Delta Tmrt.

También se genera un ranking de sensibilidad por correlación entre entradas perturbadas y Tmrt bajo sombra.

### Importante
Este intervalo se denomina deliberadamente **intervalo operativo de sensibilidad**. No es un intervalo de confianza instrumental ni sustituye la caracterización metrológica de sensores.

Los supuestos usados quedan guardados junto con el resultado.

## 7. Reporte científico
El informe completo incorpora:

- fuente radiativa;
- GHI/DNI/DHI usados;
- calidad/procedencia;
- componentes derivados;
- intervalo operativo P05–P95 de Tmrt;
- resultados de validación Estándar / Estándar calibrado / Avanzado cuando existe una campaña cargada;
- RMSE, MAE, bias y R²;
- advertencias de trazabilidad.

## 8. Reproducibilidad
El Excel de escena guarda ahora también:

- `radiation_source_mode`;
- `radiation_source_label`;
- `radiation_quality`;
- `meteorology_csv`;
- GHI/DNI/DHI del último cálculo.

Los proyectos guardan la ruta relativa de la serie meteorológica y la restauran cuando vuelven a abrirse.

## 9. Validación
Suite v15:

- 123 tests aprobados;
- 5 omitidos porque requieren pvlib en el entorno de prueba.
