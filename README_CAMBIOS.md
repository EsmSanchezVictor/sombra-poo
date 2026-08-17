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

### 5.2 Fix posterior (v3.1.2) — la banda "Escena" del ribbon rompía el toggle

Reportado tras el fix anterior: los íconos laterales funcionaban, pero
los botones de la banda "Escena" del ribbon (Temp. / Sombra / Edición /
Modelo) desincronizaban el estado de los paneles. Causa: en
`setup_ribbon()` los botones de Escena llamaban `self.open_panel(i)`
directo en vez de `toggle_panel(i)` — con un panel ya abierto, abrían
el nuevo encima sin cerrar el viejo (dos paneles mapeados a la vez y
`active_panel` apuntando al último). Corregido: ahora llaman a
`toggle_panel(i)`, exactamente el mismo camino que los íconos
laterales (como prometía el docstring del método).

### 5.3 Fix posterior (v3.1.3) — widgets de los paneles ajustados al contenedor

Reportado tras el fix anterior: los elementos dentro de los paneles
desplegables no se ajustaban al ancho del contenedor (quedaban cortos
con espacio vacío a la derecha, o desbordaban el panel — que no tiene
scroll horizontal). Cambios en `ui/app_ui.py`:

- **Panel 1**: labels, entries y el botón "Calcular..." pasan a
  `pack(fill="x")` — se estiran al ancho del panel (antes quedaban a su
  tamaño natural).
- **Panel 2**: todos los botones, checkbox y el combobox de matriz a
  `fill="x"`; el listbox del historial perdió el `width=32` fijo
  (~250px, más ancho que el panel de 227px) y ahora llena el frame.
- **Panel 3**: botones de "Acciones" pasan de `sticky="w"` a
  `sticky="ew"` (la columna ya tenía peso) — ancho completo.
- **Panel 4**: `acciones_frame` ganó `grid_columnconfigure(0, weight=1)`
  y sus botones se estiran; combos del modo simple/avanzado sin `width`
  fijo; entry de temperatura a `sticky="ew"`; el `wraplength` del
  mensaje de error de ubicaciones era fijo (260px, desbordaba) y ahora
  se re-envuelve dinámicamente al ancho del frame.
- **`crear_control`** (controles avanzados de los paneles 3 y 4): el
  label y el entry con anchos fijos (20 y 15 chars) pedían ~250px y
  desbordaban el panel; se redujeron (18 y 12) y la columna del control
  ganó peso para que entry/scale se estiren.

Verificado midiendo cada widget abierto: los 4 paneles con contenido
de 225px y 0 widgets que desborden; entries/botones/combos miden
185px (= ancho del panel − padding). `pytest test/ -q` sigue 25/25.

### 5.4 Fix posterior (v3.1.4) — fuera los botones "Exportar resultados" del Panel 2

Se eliminó la sección "Exportar resultados:" del Panel 2 (el label y los
botones "Exportar matriz a excel" y "Exportar a informe PDF", y sus
referencias de habilitación/deshabilitación en el flujo de
procesamiento). Las funciones `exportar_a_excel` y `exportar_a_pdf`
**no se purgaron**: siguen en uso desde el menú "Exportar…" (Ctrl+E y
Ctrl+P), el menú Modelo ("Exportar matriz a PDF" / "Exportar matriz del
modelo") y el ribbon — los botones del panel eran solo un acceso más.

**Estudio de código muerto** (referencias en todo el repo, sin contar
la línea `def`): funciones sin ningún uso:

| Función | Ubicación | Qué es |
|---|---|---|
| `_copy_image_to_project` | `ui/app_ui.py:826` | Delegado de `save_loaded_image_to_project` (que sí se usa) — nunca llamado |
| `_setup_hover_tmrt_map` | `ui/app_ui.py:3022` | Hover del mapa Tmrt — superado por `_setup_hover_shadow_percent_photo` |
| `actualizar_fecha` | `diseño.py:67` | Asistente de fecha — nunca llamada |
| `aplicar_estilo_base` | `plot_style.py:43` | Aplicación de estilo matplotlib — nunca llamada (los módulos importan solo las constantes) |
| `reset` (y todo `reset_value.py`) | `reset_value.py` | Archivo huérfano: nadie importa `reset_value` (clase con `btn_exportar` y demás del esquema viejo) |

Resto verificado: las ~120 funciones de módulo de `core/`, `services/`,
`ui/` y la raíz tienen al menos una referencia; los métodos de
`SombraApp` no listados arriba se usan (directo, vía menú/ribbon/binds
o desde otros módulos con `getattr`).

**Los 5 candidatos se ELIMINARON** (confirmado por el usuario):
`_copy_image_to_project` y `_setup_hover_tmrt_map` (con sus atributos
`_tmrt_hover_*` que quedaban huérfanos) de `ui/app_ui.py`;
`actualizar_fecha` de `diseño.py` (además, estaba rota: referenciaba
`vars`/`actualizar_grafico` inexistentes — habría dado NameError);
`aplicar_estilo_base` de `plot_style.py` (eran 4 rcParams triviales de
re-agregar si alguna vez se quiere tipografía global); y el archivo
`reset_value.py` completo (huérfano del esquema viejo). De paso se
sacaron los imports que quedaron sin uso: `datetime` de `diseño.py` y
`matplotlib.pyplot` de `plot_style.py`. `pytest test/ -q` sigue 25/25.

### 5.5 Herramientas nuevas (v3.2) — confort, calibración y validación

Implementación del paquete de herramientas propuesto por el agente y
aprobado por el usuario (comenzando por el asistente de calibración de
`k_factor`). Todos los cálculos reutilizan el motor existente
(`Temperatura`, `calcular_sombra_arboles`) — no duplican física.

**Módulos nuevos en `core/`:**

| Módulo | Contenido |
|---|---|
| `thermal_comfort.py` | `globo_negro_a_tmrt` (ISO 7726, globo 150 mm), `indice_calor` (Heat Index NWS/Rothfusz 1990 con los 2 ajustes), `temperatura_aparente` (Steadman 1984, versión BoM), `presion_vapor` (Magnus), `categoria_estres` (bandas NWS), `grados_hora` (integral trapecio) |
| `climate_profile.py` | `velocidad_viento` (perfil logarítmico Stull 1988), `z0_superficie` (rugosidad de Wieringa), `atenuacion_copa`, `viento_categoria_a_ms` (nulo 0.5 / moderado 4.0 / fuerte 10 — coincide con McAdams), `descomponer_radiacion` (GHI→directa/difusa/reflejada, fracción difusa por nubosidad rango Reindl 1990) |
| `scenario.py` | `temperatura_diurna` (senoidal, mín 6 h / máx 15 h), `escenario_horario` (Tmrt, Heat Index y T. aparente en sol/sombra hora por hora), `resumen_escenario` (picos, grados-hora, categorías), `comparar_escenarios` (A/B), `ranking_arboles` (área de sombra y ΔTmrt promedio por árbol, directo del mapa de transmitancia), `mapa_estres` (clasificación de mapa 2D, % de área por banda) |
| `validation.py` | `leer_csv_mediciones` (tg/tmrt, ta, rad, v, hora; convierte globo→Tmrt), `metricas` (RMSE, MAE, bias, R²), `k_factor_desde_mediciones` (mínimos cuadrados forzado por el origen) |
| `species.py` | `ESPECIES` (9 entradas con rho_copa, transmitancia, caducidad, albedo, alturas y referencia bibliográfica), `propiedades_especie`, `nombres_especies` |

**Integración en la interfaz:**

- `k_factor` ahora se persiste en `data/settings.json` (default 0.04,
  clave nueva en `SettingsManager.default_settings`) y se aplica a las
  3 instancias de `Temperatura` de `ui/app_ui.py`. El Panel 4 tiene un
  campo "Humedad relativa (%)" y una sección "Herramientas" con 5
  botones.
- Diálogos nuevos (patrón de los existentes, con gráficos matplotlib
  embebidos donde aportan): **Calibrar k_factor** (lista de mediciones
  de globo + ajuste por mínimos cuadrados con R²/RMSE + "Aplicar y
  guardar"), **Confort térmico** (HI y AT en sol/sombra + bandas de
  estrés + mapa si el modelo ya se ejecutó), **Escenario A/B** (barrido
  horario con 2 % de sombra, curvas de Heat Index y resumen de
  grados-hora y ΔTmrt), **Validar CSV** (scatter observado vs. modelo,
  RMSE/MAE/bias/R², k_factor sugerido aplicable), **Especies**
  (biblioteca con propiedades y referencias).
- Menú Análisis: 5 entradas nuevas. Ribbon Análisis: botones
  "Calibrar" y "Confort" con íconos nuevos en `icon_factory.py`
  (`calibrar` = medidor, `confort` = termómetro).
- El item de "geometría 3D de copa" de la propuesta ya estaba cubierto:
  `calcular_sombra_arboles` modela la copa como elipse elongada según
  la elevación solar (verificado por tests) — no se reimplementó.

**Limitación documentada (integridad científica):** el UTCI completo
(polinomio de ~40 términos de Bröde et al. 2012, calibrado sobre el
modelo fisiológico de Fiala) NO se implementó de memoria — requiere el
modelo termorregulatorio o la librería `pythermalcomfort`. Los índices
operativos usados (Heat Index NWS, T. aparente Steadman, ISO 7726) son
los estándar de planeamiento urbano; si se reporta UTCI oficial se
agrega la dependencia y se delega. Índice de confort fisiología (PET)
también queda como trabajo futuro (requiere MEMI).

**Tests:** `test/test_herramientas.py` (28 casos): fórmulas verificadas
contra valores publicados (ej. Heat Index 90°F/60%RH ≈ 100°F del NWS),
conservación de energía en la descomposición radiativa, perfil de
viento, ranking de árboles (el grande gana), mapa de estrés, mínimos
cuadrados que recuperan k exacto, lectura de CSV con errores
controlados. Suite total: 57/57 verdes.

### 5.6 Ronda 2 — especies en el editor, ranking en UI, incertidumbre y UTCI oficial

Completar las opciones pendientes de la propuesta (aprobadas por el
usuario) y el refactor de `ui/app_ui.py` (§6, primera etapa).

**Especies aplicables en el editor de diseño** (`diseño.py`):

- `_combo_especie`: dropdown con las 9 especies de `core/species.py` en
  los diálogos de crear y editar árboles; al elegir una especie se
  autocompletan Altura, Densidad de copa y Radio con los valores
  típicos de la biblioteca.
- El árbol guarda `especie` (atributo dinámico, no rompe serialización
  existente); la exportación a Excel incluye la columna `Especie` y la
  importación la restaura.

**Ranking de árboles en la interfaz** (`ui/app_ui.py`,
`ui/icon_factory.py`, `ui/menu_bar.py`):

- `_dialogo_ranking_arboles`: ranking por ΔTmrt promedio sobre la
  escena (barh matplotlib) + lista con área de sombra, cobertura y
  ΔTmrt por árbol, incluyendo la especie; deduplica la escena
  compartida (vars["arboles"] + vars_modelo["arboles"]).
- Botón "Ranking" en Panel 4, entrada "Efectividad de árboles
  (ranking)…" en menú Análisis y botón de ribbon con ícono `arbol`
  nuevo (árbol + sombra).

**Incertidumbre de calibración** (`_dialogo_escenario_ab`):

- Banda `fill_between` de ±20% de `k_factor` (k_lo/k_hi) alrededor de
  la curva del escenario B, más línea de resumen con el ancho de banda
  en el pico y, si el k_factor fue calibrado, la fecha de calibración.

**UTCI oficial** (`core/thermal_comfort.py`, `core/scenario.py`):

- Delegación a `pythermalcomfort` (Bröde et al. 2012, modelo Fiala):
  `utci()` y `categoria_utci()` con import perezoso
  (`UTCI_DISPONIBLE`); si la librería falta, la app lo informa en vez
  de fallar.
- `escenario_horario` ahora reporta `utci_sol`/`utci_sombra` y
  `resumen_escenario` los picos con su categoría; se muestran en el
  diálogo Confort y en el resumen de Escenario A/B.
- Instalación: `pip install --no-deps pythermalcomfort` (v4.4: pide
  `numpy<2.3`, pero funciona con numpy 2.4.2; la build de 2.2.6 desde
  fuente falla en Python 3.14). `requirements.txt`: `numpy>=1.26,<3`
  y `pythermalcomfort>=4.4` con la nota del `--no-deps`.
- Se reemplazó la limitación documentada en §5.5: el UTCI ya no se
  simula, se delega.

**Refactor de `ui/app_ui.py` — primera etapa (§6, ítems 1-2 parciales):**

- `ui/panels.py`: funciones de módulo con `app` explícito para
  construir Panel 1 y Panel 4 (`setup_panel_1`, `setup_panel_4`),
  `crear_control` y los helpers de modo/ciudad (`_toggle_modelo_mode`,
  `_toggle_edicion_mode`, `_toggle_panel2_advanced`,
  `_update_city_options`, `_filter_city_options`, `_apply_location`,
  `_build_controles`). De paso se corrigió un bug latente: el binding
  `<Return>` de `crear_control` llamaba a un `actualizar_dia` global
  inexistente (NameError al presionar Enter); ahora llama al método
  real de la app.
- `ui/dialogs.py`: clase `HerramientasDialogs(app)` con los 6 diálogos
  de herramientas (calibrador, confort, escenario A/B, validación CSV,
  especies, ranking) + sus 6 helpers internos.
- `SombraApp` conserva la API pública: los 6 `_dialogo_*` quedan como
  bound methods (binding en `__init__` desde `HerramientasDialogs`) y
  los helpers de panel como delegados de un renglón — los módulos
  externos (`core/settings_manager.py`, `core/app_state.py`) y los
  call sites internos no cambian.
- `SombraApp` quedó en ~2300 líneas de solo orquestación UI. La lógica
  de negocio (Tmrt, escenarios) ya vive en `core/`; el paso 3 del plan
  (migrar el resto de paneles, ej. `setup_panel_3`) queda como trabajo
  futuro del mismo patrón.

**Tests:** 2 casos nuevos en `test/test_herramientas.py` (UTCI delega e
informa "Estrés de calor fuerte" con 30<v<45; sombra nunca supera al
sol en UTCI horario) y correcciones de API (ta→tdb, DataFrame→objeto
UTCI). Suite total: 59/59 verdes.

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
