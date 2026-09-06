# Proyecto Sombra — v34

## Objetivo

Revisar funcionalmente los modos avanzados de **Modelo**, **Edición** y **Temperatura**, corregir opciones que estaban visibles pero no actuaban de forma consistente, ocultar parámetros avanzados cuando se trabaja en modo simple y agregar una acción administrativa para borrar el historial de sesiones/proyectos de usuarios.

La revisión se hizo sobre la base v33. No se rediseñó el modelo científico; sí se corrigieron rutas de entrada, persistencia y conexiones UI→cálculo que podían hacer que una opción seleccionada no llegara al cálculo correcto o siguiera actuando estando oculta.

---

## 1. Historial de usuarios: borrar historial

En **Historial de sesiones** se agregó el botón **Borrar historial**.

Comportamiento:
- requiere confirmación explícita;
- elimina registros históricos de sesiones y sus períodos de trabajo en proyectos;
- **no elimina cuentas de usuario**;
- conserva la sesión administrativa que está actualmente conectada, para no dejar inconsistente la sesión en curso;
- los registros hijos de `session_projects` se eliminan por la relación `ON DELETE CASCADE`.

Se añadió `DatabaseManager.delete_session_history(exclude_session_id=...)` para centralizar la operación.

---

## 2. Auditoría del modo Modelo

### Presets estacionales y meteorológicos

Se revisaron y corrigieron los cuatro accesos rápidos:
- **Verano**;
- **Invierno**;
- **Soleado**;
- **Nublado**.

Correcciones:
- en Modelo todos los presets actúan sobre `vars_modelo` y ya no sobre variables de Edición;
- se reincorpora **Invierno** en Modelo;
- Verano/Invierno ajustan el día del año según el hemisferio definido por la latitud;
- la fecha ISO interna se sincroniza con el día estacional para evitar que una fecha anterior tenga prioridad sobre el preset;
- Soleado/Nublado modifican tanto la radiación base como la categoría de nubosidad.

Referencias estacionales usadas por el preset:
- hemisferio sur: verano ≈ 21 de diciembre, invierno ≈ 21 de junio;
- hemisferio norte: inverso.

### Viento

El campo de viento avanzado admite:
- `nulo` ≈ 0,5 m/s;
- `moderado` ≈ 4 m/s;
- `fuerte` ≈ 10 m/s;
- una velocidad numérica escrita directamente, por ejemplo `3.2` o `3,2` m/s.

Se corrigió un error por el cual una velocidad numérica procedente de una serie meteorológica podía terminar interpretándose con el valor de fallback de 2 m/s.

### Nubosidad

Se añadió/normalizó el control avanzado:
- Despejado;
- Parcial;
- Nublado.

La nubosidad participa en los balances avanzados y en el escenario de radiación modelada. En modo estándar se conserva el comportamiento histórico.

### Modelo térmico de superficie

El selector avanzado permite:
- Estándar;
- Avanzado seco;
- Vegetación + ET.

Corrección importante: si el usuario vuelve a **modo Simple**, una selección avanzada anterior ya no continúa actuando de forma invisible. En Simple se fuerza el camino estándar.

### Meteorología y radiación

Se auditó la conexión de las fuentes radiativas:
- cielo despejado modelado;
- medición puntual;
- escenario radiativo manual;
- serie meteorológica CSV.

Correcciones relevantes:
- `pvlib/Ineichen` seleccionado en cielo despejado ahora alimenta realmente el gráfico de Modelo avanzado;
- la nubosidad se aplica al cielo despejado modelado sin volver a atenuar una medición observada/manual;
- si una serie meteorológica contiene Ta observada, esa temperatura del instante llega al modelo detallado como override real; antes se guardaba en un campo que el ciclo Tmin/Tmax no utilizaba;
- RH, viento, GHI y fracción de nubosidad observados se incorporan cuando están disponibles.

---

## 3. Auditoría del modo Edición

El modo avanzado de Edición se alinea con Modelo y dispone de:
- viento categórico o numérico;
- nubosidad;
- modelo térmico de superficie;
- presets Verano/Invierno/Soleado/Nublado;
- fecha, latitud, longitud y hora;
- humedad;
- radiación;
- Tmin/Tmax.

Al volver a modo Simple, las selecciones avanzadas de superficie dejan de intervenir de forma oculta.

---

## 4. Temperatura: Entrada simple / Entrada avanzada

Se incorporó un selector propio:
- **Entrada simple**;
- **Entrada avanzada**.

### Siempre visibles en modo simple
- temperatura del aire;
- hora;
- fecha;
- latitud;
- longitud;
- porcentaje de sombra manual.

### Solo visibles en Entrada avanzada
- fuente radiativa/meteorológica;
- cielo despejado, medición puntual, escenario manual o CSV observado;
- uso de `pvlib/Ineichen`;
- GHI manual;
- DNI manual;
- DHI manual;
- importación de serie meteorológica;
- estado/procedencia meteorológica;
- modelo Tmrt Estándar / Avanzado radiativo;
- estado del modelo Tmrt.

### Protección frente a opciones ocultas

Cuando Temperatura está en **Entrada simple**:
- se fuerza el modelo Tmrt estándar;
- se usa el camino simplificado de cielo despejado;
- no se reutilizan silenciosamente una fuente avanzada, `pvlib`, DNI/DHI manuales o CSV seleccionados con anterioridad.

Por lo tanto, ocultar un control avanzado también desactiva su efecto hasta volver a elegir Entrada avanzada.

---

## 5. Persistencia de configuración

Se corrigió la persistencia para conservar por separado los parámetros avanzados de Modelo y Edición.

Ahora el proyecto guarda/restaura, entre otros:
- `vars` de Edición;
- `vars_modelo` de Modelo;
- modo Modelo;
- modo Edición;
- modo Temperatura;
- modelo Tmrt;
- modelo térmico de superficie;
- fuente radiativa;
- uso de pvlib;
- GHI/DNI/DHI manuales.

Compatibilidad:
- los proyectos antiguos sin `vars_modelo` siguen cargando mediante el esquema anterior;
- una configuración antigua con una fuente radiativa avanzada puede abrir Temperatura en modo avanzado para no ocultar accidentalmente su procedencia.

---

## 6. Otros ajustes de coherencia

- En diálogos de confort y comparación A/B, el modo Modelo avanzado toma la humedad avanzada de `vars_modelo`; el modo simple continúa usando la humedad simplificada.
- Excel incorpora `nubosidad` como parámetro de escena y evita que el valor simple oculto sobreescriba la nubosidad avanzada.
- Los valores avanzados de Modelo dejan de compartir accidentalmente persistencia con Edición.

---

## 7. Validación realizada

Suite automática final de v34:

- **202 tests aprobados**;
- **5 tests omitidos** por dependencias/condiciones opcionales;
- `python -m compileall -q .` sin errores.

Se añadieron pruebas específicas para:
- presets estacionales por hemisferio y sincronización de fecha;
- Soleado/Nublado;
- viento categórico y numérico;
- aislamiento del modo de superficie avanzado al volver a Simple;
- borrado de historial preservando la sesión actual;
- cascada de períodos de proyecto;
- cableado de UI avanzada y persistencia;
- efecto medible de viento/nubosidad/humedad en balance avanzado;
- caminos Estándar / Avanzado / Vegetación + ET.

---

## Archivos modificados

- `database_manager.py`
- `main_app.py`
- `modelo_con_excel.py`
- `core/app_state.py`
- `core/climate_profile.py`
- `core/excel_scene.py`
- `ui/app_ui.py`
- `ui/dialogs.py`
- `ui/panels.py`

## Archivos agregados

- `test/test_v34_advanced_modes.py`
- `CAMBIOS_MODOS_AVANZADOS_HISTORIAL_v34.md`
- `CONTEXTO_PROYECTO_SOMBRA_v34.md`
- `INSTRUCCIONES_REEMPLAZO_v34.md`
