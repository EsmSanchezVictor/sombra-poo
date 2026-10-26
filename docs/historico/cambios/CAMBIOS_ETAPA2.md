# Cambios — Proyecto Sombra v35.6-etapa2

Entrega acumulativa sobre v35.6-etapa1. La v35.6 original y la Etapa 1 se conservan; v35.7 sigue descartada.

## Configuración y coherencia

- `core/effective_scenario.py`: configuración efectiva inmutable, validada y serializable para Tmrt. Punto, mapa fotográfico, sensibilidad, confort, incertidumbre e informe emplean la misma política Simple/Avanzado, fecha, huso y radiación. El barrido horario resuelve cada instante y conserva su configuración.
- Simple fuerza Tmrt estándar y cielo claro analítico, y no interpreta campos manuales avanzados ocultos. Un selector avanzado o una serie sin cargar no modifica esos cálculos. La incertidumbre emplea el modelo efectivo del resultado, no el selector oculto.
- `services/scenario_service.py`: resolución común de Edición/Modelo. La radiación y la geometría solar provienen del mismo instante y motor. Los valores observados de Ta/RH/viento alimentan el cálculo sin sobrescribir los controles compartidos; volver a Simple limpia los overrides anteriores.
- El esquema rápido de radiación del Panel 4 Simple se conserva (I_sol_base · sin(elevación)); Tmrt y temperatura superficial siguen siendo variables distintas.
- En superficies Avanzado, seleccionar cielo claro usa siempre SolarEngine: pvlib si está habilitado y disponible, o fallback analítico. Antes, con pvlib deshabilitado, podía utilizarse la radiación histórica del panel. Este cambio puede modificar los resultados avanzados anteriores; para prescribir GHI debe seleccionarse escenario manual.

## Fecha y viento

- Eliminado el año 2026 por defecto en offsets solares. Se usa el año calendario del escenario, incluido horario estacional, días bisiestos y Excel. El día visible prevalece sobre una fecha ISO desactualizada. Día 366 en año no bisiesto se rechaza. Hora 24 se registra como 00:00 del día siguiente.
- El cambio de fecha actualiza el año antes de notificar al control del día, evitando que observadores muestren el año anterior.
- Un parser de viento para convección, vegetación y confort: nulo=0.5, moderado=4 y fuerte=10 m/s; texto numérico con punto/coma se interpreta igual en todos los consumidores. Un nombre histórico desconocido conserva el fallback común de 4 m/s. NaN, infinito y viento negativo se rechazan.
- Viento meteorológico interpretado como referencia a 10 m; ET usa una conversión operativa a 2 m mediante perfil logarítmico neutro con z0=0.03 m. Se registra esta convención. La convección conserva la aproximación histórica con viento de referencia: no representa viento local bajo copa ni CFD. Las series sin altura explícita requieren confirmar en campo la altura de referencia.

## Dominios y diagnóstico

- UTCI devuelve NaN fuera de su dominio operativo y lo clasifica/presenta como **Fuera de dominio UTCI**, nunca como calor extremo. Ausencia de pythermalcomfort sigue siendo **UTCI no disponible**.
- Los mapas cuentan los píxeles fuera del dominio en el denominador y muestran su porcentaje; no descartan silenciosamente esa área. Un mapa completamente fuera del dominio devuelve 100% fuera de dominio. Los resúmenes horarios separan valores válidos y horas fuera de dominio.
- Conversión de globo negro: entradas finitas, Kelvin positivo, viento/diámetro/emisividad físicos y radicando positivo/finito. Se rechazan resultados complejos o imposibles.
- El solver superficial rechaza entradas no finitas o físicamente fuera de rango. Se conserva su balance energético. Se exponen convergencia, límites alcanzados, residuo máximo e iteraciones en metadatos, animación, diagnóstico de la figura, estadísticas e informe. Se ajustó únicamente la tolerancia relativa al detectar límites del solver.
- El fallback de cielo claro está centralizado; Temperatura delega en SolarEngine. Los componentes radiativos conservan GHI=DNI·sin(elevación)+DHI, también cerca del horizonte. Los instantes timezone-aware del fallback se convierten a la zona del motor.
- Se corrige RH=0% que antes podía sustituirse por 50% en el modelo avanzado.

## Trazabilidad y compatibilidad

- Excel de escena conserva año y fecha exactos. Exportaciones de elementos incluyen configuración JSON del punto y del mapa por separado y metadatos del último resultado superficial.
- Snapshots guardan contexto científico de cada cálculo y lo restauran sin recalcular. Los modelos/fuentes de los valores escalares se toman del punto capturado; el mapa conserva su propio contexto. Los resultados históricos sin estos campos se siguen leyendo, sin inventar una procedencia que no se guardó.
- Release científico v35.6-etapa2, esquema sombra-science/1.1; formato de proyecto existente compatible.
- Se mantienen los cambios de seguridad, usuarios, JSON atómico y .3es de Etapa 1.

## Lo que queda abierto

Etapa 3: recuperación multiartefacto, hashes de entradas/resultados, logging, migradores, refactor de módulos grandes, dependencias reproducibles/CI y distribución. Revisión visual Tk/VTK y Windows pendiente. El ranking de árboles conserva su estimación empírica histórica independiente; no debe interpretarse como una predicción validada del balance avanzado. La calibración de Tmrt, Ta local y vegetación con mediciones de campo sigue pendiente.
