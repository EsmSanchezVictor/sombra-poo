# Cambios — v35.6-etapa3.2

Cierra por código dos pendientes científicos: política de horas locales y coherencia del ranking de árboles. Parte de la Etapa 3.1, incluyendo la corrección de fsync Windows. Versiones anteriores preservadas.

## Tiempo local

`core/local_time.py` valida por ida y vuelta UTC las posibles ocurrencias. Una hora sin offset que no existe se rechaza; una que corresponde a dos instantes también se rechaza hasta que exista una elección explícita. Nunca se desplaza hacia adelante ni se convierte automáticamente en NaT. Sirve también para cambios de media hora y días omitidos.

La interfaz muestra un mensaje para corregir fecha/hora. No incorpora un selector de fold: en los campos de hora de la UI hay que elegir una hora inequívoca. El CSV permite expresar ambas ocurrencias con offsets ISO explícitos; la API admite `fold=0` o `fold=1` al resolver una fecha naive. Una fecha aware expresa su instante mediante su offset. Fechas ZoneInfo construidas sobre horas inexistentes también se rechazan.

Motor pvlib y fallback, servicio meteorológico, configuración efectiva y Edición/Modelo usan la misma política. El día meteorológico se obtiene en la zona del motor, aunque la entrada llegue en UTC. 24 h se normaliza al día siguiente antes de buscar el offset; medianoche deja de confundirse con mediodía en validación de campo.

El CSV conserva dos mediciones a la misma hora de pared con offsets diferentes e interpola en tiempo transcurrido UTC. Rechaza mezclar filas con y sin offset y reporta el número de fila con conflicto DST. Una carga fallida no sustituye la serie anterior. Se mantiene el comportamiento previo de omitir fechas sintácticamente ilegibles; este cambio no es una auditoría integral de limpieza de CSV.

El escenario captura ISO local/UTC, offset, fold y política temporal. El calculador reproduce el offset capturado sin reinterpretar reglas IANA posteriores y verifica la coherencia de sus campos. Escenarios anteriores sin esa captura mantienen la resolución ordinaria cuando es inequívoca. `tzdata` pasa a ser dependencia explícita del núcleo para Windows.

## Ranking de árboles

La interfaz elige Edición o Modelo, sin fusionar sus árboles, y aplica el escenario efectivo de Temperatura: modo Simple/Avanzado, modelo Tmrt, Ta, GHI/DNI/DHI, posición solar, huso y procedencia. Los controles avanzados siguen aislados del modo Simple. Una GHI medida/manual igual a cero no se sustituye con cielo claro.

Cada árbol se compara individualmente contra el mismo dominio al sol usando `Temperatura.calculate_tmrt_map`. El avanzado ya no se etiqueta ni calcula mediante la fórmula empírica estándar. La API histórica sin escenario se conserva exclusivamente para estándar y se identifica como aproximación legacy; avanzado exige contexto efectivo.

Grilla por centros de celda, área física acotada a extent², resolución entre 2 y 640 y geometría validada. El orden usa la precisión calculada; el redondeo sólo aparece en pantalla. La identificación del árbol conserva su posición original aunque cambie el orden del ranking. JSON exportado mediante guardado atómico incluye escenario, método, dominio, escena, geometría, especie e indicadores. Tras un recálculo inválido se deshabilita la exportación del resultado anterior. Las figuras se liberan al cerrar.

El dominio visible es de 60×60 m centrado en (0, 0). Es potencial individual dentro de esa ventana, no aporte marginal con árboles superpuestos, edificios o enfriamiento por evapotranspiración. Tampoco es el mapa de temperatura superficial de Edición/Modelo ni el modelo de vegetación v2: compara Tmrt bajo el contexto del panel Temperatura. Árboles fuera de la ventana pueden aportar cero.

## Versiones y compatibilidad

Aplicación y release científico: v35.6-etapa3.2. Esquema científico: sombra-science/1.2; configuración efectiva: 2, con campos temporales aditivos. Las ecuaciones Tmrt, UTCI, balance superficial y vegetación conservan sus identificadores. Cambian selección temporal y método de ranking, por eso se registra un nuevo release científico. Esquemas de proyecto, usuarios, Excel y generaciones de recuperación se mantienen.

Se agregan 79 casos al conjunto anterior de 453. Se adapta un fixture horario anterior para actualizar también su captura temporal y se actualizan las expectativas de versiones. La reproducción independiente de seis fallos está en `test/repro_stage3_2.py`; no se cuenta doble en la suite principal.
