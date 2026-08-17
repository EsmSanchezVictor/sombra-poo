# Cambios aplicados — guía de integración (v3, con fixes de física y limpieza)

## 0. Qué se hizo en esta vuelta (v3)

### Física — geometría solar corregida y unificada

El ángulo horario solar estaba mal en TODOS los módulos, con tres
formulaciones distintas conviviendo:

| Módulo | Antes | Después |
|---|---|---|
| `modelo_con_excel.py` | `H = 15·(t−12) + longitud` | `H = 15·(t−12) + (longitud − meridiano_estándar) + EoT` |
| `shadow_temp.py` | `H = 15·(t−12)` (ignoraba longitud) | idem, con `tz_offset_hours` (huso real o heurística `round(lon/15)`) |
| `diseño.py` | `H = 15·(t−12) + longitud/15` (bug original) | delega en `modelo_con_excel` |

Derivación: `hora_solar = UTC + longitud/15 + EoT` y el reloj local vale
`UTC + meridiano/15`, así que `H = 15·(t_local − 12) + (L − M) + EoT`.
Se agregó la **ecuación del tiempo** (aprox. Spencer, ±4°) en ambos
módulos. Verificado contra pvlib: antes Buenos Aires se desviaba ~27° en
H; ahora el fallback coincide con pvlib dentro de ±0.5° de elevación
(hay tests que lo fijan, ver abajo).

`SolarEngine` le pasa ahora el huso real de su `tz` al fallback
(`_tz_offset_hours`), así el camino pvlib y el camino interno usan la
misma física.

### Física — `diseño.py` dejó de tener su propia física (con bugs)

`diseño.py` (vista de edición) tenía copias propias de todo: ángulo
solar con `(lon/15)`, ciclo diurno sin desfase térmico
(`sin(π·h/24)` con mínimo a medianoche), convección por categoría fija
(5/15/25), sombras circulares sin elongación, paredes con bounding box,
lookup de materiales que fallaba con mayúsculas y `alpha=1e-7` para
composites. Ahora importa `Arbol`, `Estructura`, `Material`,
`materiales` y todas las funciones físicas de `modelo_con_excel.py` —
una sola fuente de verdad, y la vista 2D/3D de edición y del modelo
dan exactamente el mismo resultado para los mismos datos.

### Seguridad — login con hash

`main_app.py` y `login_window.py` comparaban `user[2] == password` en
texto plano (además con índices del esquema viejo). Ahora usan
`db.authenticate()` (PBKDF2+SHA256, ya estaba en `database_manager.py`)
y `is_admin` se lee de la columna correcta (`user[4]`). También se
corrigió `login_window.recover_password()`, que le pasaba el username a
`update_password()` cuando espera el id.

### Tests — de 3 rotos a 25 verdes

- `test/test_physics.py` se reescribió: usa `SolarEngine` (no el
  `motor_solar.py` muerto), testea el meridiano estándar, la ecuación
  del tiempo, el mediodía solar local de Buenos Aires, transmitancia de
  sombra, radiación de cielo despejado, `calibrate_k_factor`, la
  consistencia entre `modelo_con_excel` y `shadow_temp`, valores golden
  de regresión y una comparación contra pvlib real (5 ubicaciones).
- Se agregó `asignar_materiales_grilla()` a `modelo_con_excel.py`
  (extraído del loop de `generar_grafico`, testable).
- Se borró el test que importaba `detector_sombras.py` (muerto).

### Limpieza

- Borrados: `image_processor copy.py`, `modelo_con_excel copy.py`,
  `services/borrar procesamiento_imagen.py`, `test/test/test/`, `ver`.
- `users.db`, `__pycache__/` y `proyectos/` salieron del control de
  versiones (`git rm --cached`) y quedaron en `.gitignore`.
- Validación de Kelvin extendida a T_min/T_max en `ui/app_ui.py`
  (`_validate_kelvin_input`).

### Cómo correr los tests

```
pip install -r requirements.txt pytest
python -m pytest test/ -v
```

## 1. Qué pasó entre la v1 y esta versión

En la primera pasada solo tenía los archivos sueltos de la raíz del
repo. Con `core/`, `services/` y `ui/` que subiste, quedó claro que:

- Hay una app **moderna y bien encaminada** (`ui/app_ui.py::SombraApp`
  + `core/` + `services/`) que ya resuelve gestión de proyectos,
  versionado de archivos y ubicaciones — mucho mejor de lo que
  sugerían los archivos sueltos.
- Varios archivos de la raíz (`detector_sombras.py`, `motor_solar.py`,
  `services/procesamiento_imagen.py`) son **código muerto**: nadie los
  importa desde la app real. Mis fixes anteriores sobre
  `detector_sombras.py` y `motor_solar.py` apuntaban a archivos que no
  se usan — los saqué de esta entrega. Ver `ARCHIVOS_A_ELIMINAR.md`.
- El modelo científico real de la app es `shadow_temp.py::Temperatura`
  (cálculo de Tmrt), no lo había revisado antes.

## 2. Archivos corregidos en esta entrega

| Archivo | Reemplaza a | Qué se corrigió |
|---|---|---|
| `shadow_temp.py` | raíz `shadow_temp.py` | `print` → `logging`; se agrega `solar_azimuth()`; se agrega `radiation_override` para no depender de dos modelos de radiación distintos; se agrega `calibrate_k_factor()` para dejar de tener el 0.04 como número mágico sin respaldo |
| `solar_engine.py` | `services/solar_engine.py` | El azimut de respaldo (sin pvlib) usa ahora `Temperatura.solar_azimuth()` en vez de la aproximación lineal `(180+(hora-12)*15)%360` |
| `project.py` | `core/project.py` | Corrige `resultados/histograma` → `resultados/histogramas`, alineado con `services/snapshot_service.py` |
| `menu_bar.py` | `ui/menu_bar.py` | "Abrir Panel 4" ya no abre el Panel 3 (bug de copy-paste); URLs de ayuda quedan como constantes `TODO` al inicio del archivo |
| `database_manager.py` | raíz `database_manager.py` | Hash PBKDF2+salt en vez de contraseñas en texto plano — **confirmá primero si este flujo de login sigue en uso** (ver `ARCHIVOS_A_ELIMINAR.md`) |
| `migrate_db.py` | nuevo | Migra `users.db` existente al nuevo esquema con hash, con backup automático |
| `image_processor.py` | raíz `image_processor.py` | Se usa desde `ui/app_ui.py::confirmar_seleccion()` — se corrige división por cero y se agrega `clip` a [0,100] |

## 3. Orden de aplicación

1. Reemplazá `shadow_temp.py`, `solar_engine.py` (va en `services/`),
   `project.py` (va en `core/`), `menu_bar.py` (va en `ui/`) por los
   nuevos — son compatibles con las firmas que ya usa `ui/app_ui.py`,
   no deberían romper nada.
2. Confirmá si `database_manager.py` sigue en uso (ver punto 4 de
   `ARCHIVOS_A_ELIMINAR.md`). Si sí:
   - Reemplazá `database_manager.py`.
   - Corré `migrate_db.py` una sola vez (hace backup automático).
   - Reemplazá las comparaciones manuales de contraseña por
     `db.authenticate(usuario, password)`.
3. Reemplazá `image_processor.py`.
4. Borrá los archivos listados en `ARCHIVOS_A_ELIMINAR.md`.

## 4. Lo más importante de todo: calibrar `k_factor`

El resultado final que ve el usuario (`Tmrt_sol`, `Tmrt_sombra`,
`ΔTmrt`) depende enteramente de `k_factor = 0.04` en `shadow_temp.py`,
que no tiene ningún respaldo documentado en el código. Usá
`calibrate_k_factor()` con al menos un par de mediciones de campo
reales (termómetro de globo negro + temperatura de aire + radiación
conocida) antes de confiar en los números que produce el modelo para
uso profesional. Sin esa calibración, el ΔTmrt que muestra la app es
una estimación relativa razonable, pero no un valor validado.

## 5. Fix posterior (v3.1) — controles del Panel 4 "ocultos" y cambio de paneles

Reportado tras la integración: al abrir el Panel 4 (Modelo) se veían el
título y los radiobuttons Simple/Avanzado, pero los botones y el resto
de los controles no aparecían. Y los íconos de la barra lateral no
manejaban bien el cambio entre paneles. Causas y correcciones en
`ui/app_ui.py`:

| Problema | Antes | Después |
|---|---|---|
| Canvas anidado en `setup_panel_4()` | Se creaba un SEGUNDO canvas scrolleable (`_build_scrollable_content`) dentro del frame que ya vive en un canvas con scrollbar; quedaba con altura chica (solo título+radios) y sin rueda del mouse | Los widgets se empacan directo sobre el frame de contenido (igual que Paneles 1/2), con scroll + rueda ya funcionando |
| `panel_width` calculado antes de mapear | `min(1/6 pantalla, frame1.winfo_width())` → `winfo_width()` devuelve 1 sin dibujar → ancho de animación inválido | `min(1/6 pantalla, 400)` → 227px en pantallas 1366px |
| Superposición del panel sobre la escena | El panel crecía al ancho de su contenido (~400px) y `frame1` no se agrandaba (grid ignora `config(width)`); quedaba tapando el área de escena | `place()` lleva `width=` explícito en cada paso (panel = exactamente `panel_width`); `frame1` se ajusta al ancho del panel antes de animar |
| Salto del panel al cambiar de ícono | `close_panel` volteaba los íconos a vertical en cada cambio (y el panel saltaba de y=30 a y=120) | Solo se vuelve a vertical cuando se cierra el ÚLTIMO panel; el alto de botones se mide con `winfo_reqheight()` (estable) |
| Animaciones que se cortaban solas (bug latente profundo) | Cada paso se encolaba con `widget.after(10, callable, ...)`; tkinter registra el callable con un nombre basado en `id()`, que se recicla por GC y se auto-borra al dispararse → con cadenas de ~23 pasos, dos timers compartían nombre y la animación moría en un paso al azar (panel congelado a medio abrir o cambio que nunca llegaba). Invisible antes porque `panel_width=1` hacía las animaciones de 2 pasos | Un ÚNICO comando Tcl persistente (`_panel_anim_step`, registrado una vez en `__init__`) maneja todos los pasos; se encola con `tk.call("after", ...)` sobre ese nombre estable — sin re-registros ni colisiones; los tokens siguen abortando cadenas viejas |

Verificado: panel 4 abre con contenido completo (542px) y todos los
controles mapeados; secuencias completas de cambio de paneles
(0→2→3→1→cerrar→reabrir) finalizan siempre en el panel correcto, sin
cuelgues; `pytest test/ -q` sigue 25/25 verde.

### 5.1 Fix posterior (v3.1.1) — el toggle de los íconos "no respondía"

Reportado tras el fix anterior: al tocar un ícono no pasaba nada (ni
abría, ni cambiaba, ni avisaba). Diagnóstico en dos capas:

| Problema | Antes | Después |
|---|---|---|
| Botones deshabilitados sin proyecto | `show_startup_screen()` llama `set_project_ui_enabled(False)` y los 4 íconos quedan `state="disabled"` — un clic sobre un botón deshabilitado se ignora en silencio (ni siquiera llega al `require_project` que mostraría el aviso) | Comportamiento de diseño (los paneles requieren proyecto); se re-habilitan en `on_project_loaded()`. No se tocó la lógica: el síntoma real era el bug de abajo |
| Cambio de panel encadenado reabría el MISMO panel | El paso final de la cadena de cierre hacía `self.open_panel(index)` — con el index del panel que se cerró, ignorando el `on_complete` recibido por `close_panel` (el callback se perdía en el refactor a `_panel_anim_step`, que recibe args vía Tcl y no puede llevar callables). Resultado: clic en ícono B → se cerraba y REABRÍA el panel A → parecía que el clic no hacía nada, y el primer clic (sin panel abierto) sí funcionaba | `animate_panel_close` guarda el callback en `self._close_callbacks[index]`; el paso final del cierre lo invoca (`callback()` en vez de `open_panel(index)`). El dict se limpia junto con `_open_after_close` |

Verificado con clics reales (`button.invoke()`) sobre los 4 íconos,
con proyecto cargado: abrir 0 → cambiar a 2 → cerrar 2 → abrir 3 →
cambiar a 1 → cerrar 1; cada paso termina en el estado correcto
(active, panel mapeado, íconos HOR/VERT); `pytest test/ -q` sigue
25/25 verde.

## 6. Pendiente — la refactorización grande

`ui/app_ui.py` es una sola clase (`SombraApp`) de 2251 líneas y ~100
métodos: mezcla construcción de UI, lógica de negocio (cálculo de
Tmrt), I/O de proyecto y animaciones de panel. No la reescribí entera
porque el riesgo de romper algo sin poder correr la app y probarla es
alto — pero el patrón de refactor recomendado es:

1. Sacar toda la lógica que no toca widgets a "controladores" en
   `core/` o `services/` (ej: un `ThermalController` que envuelva
   `calculate_temperature_in_shade()`, reciba los valores ya
   parseados y devuelva el resultado — sin conocer tkinter).
2. `SombraApp` pasa a ser solo orquestación: crea los controladores,
   conecta widgets a callbacks, y les pasa los datos.
3. Migrar panel por panel (empezar por el que cambia menos seguido)
   en vez de todo junto.

Si querés, en la próxima vuelta armamos el primer controlador
extraído (por ejemplo el de Tmrt) como ejemplo concreto del patrón.
