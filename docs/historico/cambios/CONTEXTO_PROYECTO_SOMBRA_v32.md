# CONTEXTO DE CONTINUIDAD — PROYECTO SOMBRA

**Estado de referencia:** v31  
**Fecha de continuidad:** 2026-09-05  
**Objetivo de este archivo:** permitir continuar el desarrollo en un chat nuevo sin perder el conocimiento técnico, decisiones, arquitectura, correcciones, criterios científicos y pendientes construidos durante la conversación larga.

---

## 1. Regla de continuidad

Tomar **v30 como base actual** salvo que el usuario indique que realizó cambios locales posteriores.

Antes de modificar código en una nueva conversación:
1. localizar este archivo de contexto;
2. localizar el ZIP `proyecto_sombra_integrado_v31.zip` o el ZIP de reemplazo correspondiente;
3. inspeccionar el código real antes de afirmar cambios;
4. mantener compatibilidad con los proyectos guardados y con `users.db` existente;
5. entregar, cuando corresponda, un ZIP integrado y otro de archivos de reemplazo;
6. no afirmar tests o validaciones que no se hayan ejecutado realmente.

El usuario prefiere implementación directa y versiones sucesivas utilizables, no solo propuestas conceptuales.

---

# 2. Finalidad del software

Aplicación de escritorio en Python/Tkinter para análisis microclimático y térmico de sombra y espacios verdes, con:
- geometría solar;
- radiación solar;
- análisis fotográfico de sombra;
- Tmrt;
- temperatura del aire local estimada;
- confort térmico (UTCI, Heat Index, temperatura aparente);
- superficies y materiales;
- vegetación y evapotranspiración;
- escenarios/edición/modelo;
- persistencia por proyecto;
- base de datos de análisis por árbol/imagen;
- reportes, exportaciones y validación científica;
- gestión de usuarios y trazabilidad de sesiones/proyectos.

---

# 3. Correcciones científicas y conceptuales consolidadas

## 3.1 Zona horaria y geometría solar
Se detectó que el fallback `round(lon/15)` asignaba a Buenos Aires UTC-4 en vez de UTC-3, con errores de elevación solar de hasta ~9°. Se corrigió y luego se unificó la geometría solar en un único kernel compartido.

## 3.2 Temperatura diaria
Había dos modelos diarios inconsistentes. `scenario.py` tenía una discontinuidad alrededor de las 18:00. Se unificó el modelo térmico diario.

## 3.3 Sombra y transmitancia
El sistema original producía una transmitancia incorrecta incluso con 0 % de sombra. Se consolidó:

`tau_eff = (1-S) + S*tau_full = 1 - S*(1-tau_full)`

Por lo tanto, con `S = 0`, `tau_eff = 1`.

## 3.4 Sombra fotográfica
Se separaron dos conceptos que originalmente estaban mezclados:
- **cobertura de sombra**: fracción del área clasificada como sombra;
- **atenuación/intensidad de sombra**: reducción relativa de luminosidad/radiación dentro de las zonas sombreadas.

El análisis guarda ambos valores y genera mapas locales de transmitancia/atenuación.

## 3.5 Índices de confort
Se corrigió el uso erróneo de Tmrt como si fuera temperatura del aire en Heat Index y temperatura aparente.
- Heat Index y temperatura aparente usan **Ta**.
- UTCI incorpora el efecto radiativo mediante Tmrt.

## 3.6 Tmrt
Se mantienen dos enfoques:

### Modelo estándar
Modelo lineal histórico, conservado por compatibilidad.
Ejemplo con Ta=25 °C, GHI=883 W/m², k=0.04:
`Tmrt_sun = 25 + 0.04*883 = 60.32 °C`

Con 45 % de sombra arbórea y `tau_full=0.15`:
`tau_eff = 1 - 0.45*(1-0.15) = 0.6175`
`Tmrt_shade ≈ 46.81 °C`

### Modelo avanzado radiativo v1
Incluye radiación directa, difusa y reflejada, absorptividad humana, emisividad de onda larga y factores geométricos.

No debe presentarse automáticamente como “más verdadero”: necesita validación externa.

## 3.7 Temperatura del aire local estimada bajo sombra
Modelo empírico y calibrable, separado de Tmrt.
Valores por defecto históricos:
- árbol: coeficiente 0.0025, enfriamiento máximo 2.5 °C;
- estructura: coeficiente 0.0012, enfriamiento máximo 1.2 °C.

Debe seguir tratándose como estimación empírica, no como CFD.

## 3.8 Balance térmico de superficies
Se incorporaron tres modos:
- estándar;
- avanzado seco v1;
- avanzado vegetación + ET v2.

El balance avanzado considera radiación de onda corta, onda larga, convección, conducción y, en v2, calor latente.

## 3.9 Materiales
Se incorporaron propiedades:
- absorptancia solar;
- reflectancia;
- transmitancia;
- emisividad LW;
- conductividad térmica;
- profundidad térmica efectiva;
- capacidad calorífica volumétrica.

En estructuras transmisivas se controla/interpreta `alpha + rho + tau = 1`.

## 3.10 Vegetación y evapotranspiración
Modo avanzado vegetación+ET v2:
- fracción de suelo vegetado;
- disponibilidad hídrica del suelo;
- disponibilidad hídrica del dosel;
- FAO-56 Penman–Monteith aproximado horario;
- LAI;
- Kc;
- transmitancia sin hojas;
- fenología de caducifolias por fecha y hemisferio.

La transpiración del dosel se calcula como diagnóstico separado para evitar doble contabilización.

## 3.11 Meteorología y radiación
Se distinguen fuentes:
- cielo despejado modelado (pvlib/fallback);
- medición puntual;
- escenario radiativo manual;
- CSV meteorológico observado.

Se conserva procedencia por variable. Si solo hay GHI, DNI/DHI pueden derivarse y deben marcarse como derivados.

Interpolación solo para huecos cortos (por defecto hasta 90 min), sin extrapolar fuera del período observado.

## 3.12 Incertidumbre
Existe módulo Monte Carlo operativo para incertidumbre/sensibilidad, no presentado como error instrumental ni intervalo de confianza formal.

Entrega P05/P50/P95 y ranking de sensibilidad.

## 3.13 Validación científica
Existe flujo para calibración/validación con RMSE, MAE, bias, R² y n.
Se separan conjuntos de calibración y validación cuando están disponibles.
Pendiente científicamente: validación de campo independiente real.

---

# 4. Estado científico pendiente

El software está desarrollado metodológicamente, pero aún requiere validación experimental real para cerrar el ciclo científico.

Pendientes principales:
- validación externa de Tmrt;
- validación de Ta local estimada;
- validación de temperatura superficial;
- validación del análisis fotográfico de sombra;
- calibración de `k` del modelo estándar;
- calibración del modelo local de Ta;
- parámetros específicos de especies (LAI/Kc/transmitancia) con trazabilidad bibliográfica o medición;
- validación de ET;
- incertidumbre específica de sensores.

No agregar complejidad física sustancial sin evidencia experimental que lo justifique.

---

# 5. Evolución técnica por versiones

## v5
Correcciones amplias de física y consistencia.

## v6
Hover interactivo en curvas de nivel; escala exacta Tmrt min/max; pin por clic.

## v7
Excel reproducible; `core/excel_scene.py`; hojas vacías con esquema; parámetros y geometría unificados.

## v8
Temperatura de aire local estimada y hover simplificado.

## v9
Modelo dual de Tmrt: estándar + avanzado radiativo.

## v10
Calibración/validación científica; métricas; CSV enriquecido; aplicación explícita de parámetros calibrados.

## v11
Separación cobertura de sombra / atenuación; máscaras y mapas locales.

## v12
Balance térmico avanzado y materiales.

## v13
Vegetación, ET, fenología, LAI/Kc.

## v15
Meteorología observada, procedencia y Monte Carlo de incertidumbre.

## v16
Auditoría integral, consolidación científica, kernel solar único, corrección de solver avanzado, documentación metodológica y protocolo de validación.

## v17
Rediseño del carrusel y base SQLite por análisis/árbol.

## v18
Optimización RAM y ciclo de vida de imágenes/Matplotlib.

## v19
Reorganización completa de carpetas del proyecto, autosave y backups.

## v20
Confort vectorizado y resolución configurable de matrices.

## v21
Interfaz de paneles: scroll, ancho común, eliminación de nombres de miniaturas.

## v22
Corrección de geometría principal de `frame1` para evitar compresión/recorte.

## v23
Compactación visual inicial (luego corregida porque el usuario pedía reducción horizontal).

## v24
Reducción horizontal real de paneles/controles; frame lateral más angosto.

## v25
Intento de corregir Panel 2 distribuyendo contenido vertical; luego revertido conceptualmente.

## v26
Corrección correcta del contenedor del Panel 2: `frame1` debía abarcar también la fila del carrusel (`rowspan=4`), de modo que el lateral llegue al mismo borde inferior.

## v27
Trazabilidad de sesiones y proyectos por usuario.

## v28
Rediseño de Gestión de Usuarios, corrigiendo desalineación grave de campos y mejorando seguridad/operación.

## v29
Vista 3D VTK integrada dentro del mismo contenedor de la vista 2D mediante pestañas. Se usa VTK estándar off-screen + presentación en Tk, sin depender de vtkRenderingTk; fallback Matplotlib embebido. No se modifican cálculos científicos.

## v30
Edición y Modelo pasan a usar todo el bloque central equivalente a `frame2 + frame3 + frame4 + frame5`. `frame7` y `frame11` abarcan filas 1-2 y columnas 1-2 (`rowspan=2`, `columnspan=2`), y dentro de cada host las pestañas 2D/3D ocupan el 100 % del área. VTK pasa a ser dependencia principal. Se mejora el render VTK con supersampling limitado, mayor resolución de mallas, copas multilobuladas, iluminación de tres puntos y cámara ajustada al contenido. No se modifican cálculos científicos.

## v31 — BASE ACTUAL
Compatibilidad VTK/Windows: MSAA desactivado en el primer render de Windows, primer render diferido hasta `after_idle`, fallback real si falla el contexto y diagnóstico visible con versión/excepción. Se agrega `DIAGNOSTICO_VTK_WINDOWS.py`. No se modifican cálculos científicos.

---

# 6. Carrusel y persistencia por análisis

Desde v17, cada miniatura representa un **registro de análisis único** con `analysis_id` estable.

Principio central:
- seleccionar miniatura = recuperar/restaurar;
- recalcular/modificar = actualizar el mismo `analysis_id`;
- cargar imagen nueva = crear nuevo `analysis_id`.

La selección NO debe recalcular ni agregar una miniatura nueva.

Cada registro puede recuperar:
- foto original del árbol;
- curvas Tmrt;
- máscaras de cálculo/referencia;
- geometrías superpuestas;
- matrices;
- áreas;
- grises medios;
- cobertura de sombra;
- atenuación;
- transmitancia;
- umbral fotográfico;
- mapas de sombra/sol;
- mapas de transmitancia/atenuación local;
- datos de curva;
- Tmrt sol/sombra/delta;
- modelo térmico;
- procedencia radiativa;
- resolución de análisis.

Las máscaras exactas se guardan comprimidas con valores + máscara válida + máscara completa, para no perder polígonos/círculos.

---

# 7. Resolución de cálculo

Desde v20:
- rango seleccionable: **64×64 a 640×640**;
- pasos de 32;
- predeterminado: **128×128**;
- modo normal: 128×128;
- modo avanzado: permite elegir resolución;
- cada árbol/análisis conserva su propia resolución histórica.

El mapa de Confort usa la matriz seleccionada.

---

# 8. Confort térmico y rendimiento

Problema histórico: UTCI se calculaba píxel por píxel, produciendo cientos de miles de llamadas y congelando Tkinter.

Desde v20:
- UTCI espacial vectorizado cuando la librería lo permite;
- clasificación por categorías con NumPy;
- ventana de Confort aparece primero;
- cálculo espacial corre en worker separado;
- Tkinter solo se actualiza desde el hilo principal;
- mapas en `float32` para reducir RAM.

No volver a un bucle Python por píxel.

---

# 9. Optimización RAM

Desde v18:
- conservar una sola copia RGB de la foto;
- `cv2.cvtColor` para gris, evitando temporales float64 enormes;
- mapas Tmrt/hover en float32;
- malla reducida solo para render de `contourf`;
- cálculo/almacenamiento/hover mantiene resolución elegida;
- cierre explícito de figuras/canvas Matplotlib;
- liberar PIL y referencias al cambiar de árbol;
- evitar registro innecesario de figuras en pyplot global.

Debug opcional:
`$env:SOMBRA_MEMORY_DEBUG="1"`

Debe vigilarse que RAM llegue a una meseta, no que crezca indefinidamente con cada análisis.

---

# 10. Organización de carpetas y guardado

Desde v19 el proyecto es la fuente única de verdad.

Estructura objetivo:

PROYECTO/
- PROYECTO.sombra
- config/
  - project.json
  - estructura.json
  - inventario.json
- entradas/
  - imagenes/
  - meteorologia/
  - validacion/
- escena/
  - edicion.xlsx
  - modelo.xlsx
- analisis/
  - analisis.sqlite3
  - elementos/<analysis_id>/...
  - dataset/
- resultados/
  - proyecto/
  - validacion/
  - informes/
- respaldos/
- _legacy_v18/ (solo si hace falta)

Reglas:
- autosave para información generada;
- campos editables con debounce ~900 ms;
- “Guardar” no pregunta ubicación;
- Ctrl+S consolida y crea backup timestamped `.3es` en `respaldos/`;
- “Guardar como” sí pregunta y crea un proyecto nuevo completo;
- conservar hasta ~10 backups recientes;
- `config/inventario.json` indexa archivos vivos del proyecto.

---

# 11. Interfaz lateral y paneles

Historial importante:
- se eliminó el texto/nombre debajo de miniaturas del carrusel;
- scroll vertical debe vivir en columna independiente y no superponerse a controles;
- el contenido de cada panel debe calcular su ancho después de conocer el ancho real del Canvas;
- se corrigió compresión de `frame1` mediante reserva real de ancho en la grilla;
- se redujo horizontalmente el lateral/controles en v24;
- Panel 2 debía extender el contenedor hasta la fila del carrusel, corregido con `rowspan=4` en v26.

No confundir “contenido más corto” con “contenedor físicamente más bajo”.

---

# 12. Gestión de usuarios — estado v28

Problema original:
La interfaz mostraba encabezados que no correspondían con los valores porque usaba `SELECT * FROM users` y volcaba también `password_hash` y `salt` en la tabla visible.

También había lógica por índices (`user[4:]`) que podía correr todos los campos al modificar.

## Solución v28
La gestión usa consultas explícitas y campos por nombre, no índices frágiles.

Interfaz recomendada/implementada con `ttk.Treeview`.

Columnas visibles:
- Usuario
- Nombre y apellido
- Rol
- DNI
- Email
- Teléfono
- Ciudad
- Estado
- Último ingreso

Nunca mostrar:
- password_hash
- salt

Funciones:
- búsqueda por usuario/nombre/DNI/email;
- filtro por rol;
- filtro por estado;
- selección de fila;
- doble clic para editar;
- Nuevo usuario;
- Editar;
- Restablecer contraseña;
- Activar/Desactivar;
- Eliminar.

Campos añadidos/compatibles:
- `is_active`
- `created_at`
- `updated_at`
- `last_login`

Protecciones:
- usuarios inactivos no ingresan;
- impedir eliminar/desactivar último administrador activo;
- impedir eliminar cuenta actualmente conectada;
- conservar historial de sesiones incluso si se elimina una cuenta.

No reemplazar `users.db` del usuario al actualizar. Debe migrarse automáticamente.

---

# 13. Sesiones de usuario y proyecto — v27+

El usuario pidió que la base registre:
- usuario conectado;
- sesión;
- proyecto trabajado en cada sesión.

Debe registrarse como historial, no como un único campo en `users`.

Por sesión:
- user_id (si sigue existiendo);
- `username_snapshot` para trazabilidad permanente;
- fecha/hora de inicio;
- fecha/hora de cierre;
- última actividad.

Por proyecto dentro de una sesión:
- nombre del proyecto;
- ruta;
- inicio de trabajo;
- fin de trabajo;
- acción/origen: creado, abierto, importado, duplicado, Guardar como, etc.

Si el usuario cambia de proyecto en una misma sesión:
- cerrar el tramo anterior;
- crear un nuevo tramo asociado a la misma sesión.

El historial debe sobrevivir a la eliminación futura de la cuenta.

Existe/está prevista una vista de administración “Historial de sesiones”.

---

# 14. Advertencia SQLite pendiente/revisar

Se observó:
`ResourceWarning: unclosed database ... gc.collect()`

La causa conceptual detectada fue el uso de conexiones SQLite abiertas que no se cerraban explícitamente. Un `with sqlite3.Connection` gestiona commit/rollback, pero no debe asumirse que cierra la conexión.

Patrón recomendado:

```python
from contextlib import contextmanager

@contextmanager
def _connection(self):
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

Revisar todas las conexiones SQLite y asegurar cierre al salir de la aplicación.

Este punto se señaló como problema real separado; verificar en la base v28 antes de declarar que está resuelto.

---

# 15. Vista 3D y área de visualización — estado v30

La integración VTK introducida en v29 se conserva, pero v30 corrige dos problemas de uso observados: el gráfico ocupaba solo una de las cuatro celdas centrales y, si VTK no estaba instalado, el fallback Matplotlib podía verse claramente inferior al render VTK de referencia.

Decisión v30:
- motor principal: **VTK estándar**;
- `vtk>=9.3,<10` pasa a `requirements.txt`;
- Matplotlib 3D queda como fallback de seguridad;
- no se incorpora Qt/pyvistaqt dentro de la aplicación Tkinter;
- VTK continúa en modo off-screen + imagen presentada en Tk.

Interfaz:
- `frame7` (Edición) ocupa filas 1-2 y columnas 1-2;
- `frame11` (Modelo) ocupa filas 1-2 y columnas 1-2;
- equivalen al área histórica conjunta de `frame2`, `frame3`, `frame4` y `frame5`;
- cada host contiene pestañas `Vista 2D` / `Vista 3D`;
- ambas pestañas llenan todo el host;
- los frames auxiliares 8-10 y 12-14 se conservan por compatibilidad pero quedan ocultos en Edición/Modelo.

Render v30:
- plano térmico desde `X`, `Y`, `T` ya calculados;
- supersampling estático 1.35x con límite de 2.6 Mpx para contener RAM;
- interacción de rotación en 1x y restauración de alta calidad al soltar;
- copas multilobuladas dentro del radio/altura existentes;
- mayor resolución de esfera/cilindro reutilizados;
- iluminación cálida principal + relleno frío + luz de recorte;
- cámara isométrica ajustada al contenido y mejor aprovechamiento del viewport;
- VTK probado visualmente en un viewport 1200×722, render interno 1620×975.

Regla científica:
La vista 3D sigue siendo exclusivamente una capa de render. No debe recalcular Tmrt, Ta, sombra, radiación, confort, balance de superficies ni ningún otro resultado científico. `core/` y `services/` no se modificaron en v30.

# 16. Preferencias del usuario para el desarrollo

- Quiere cambios aplicados directamente y archivos listos para reemplazar.
- Prefiere ZIP completo + ZIP de reemplazo cuando el cambio es importante.
- No quiere perder compatibilidad con proyectos guardados.
- Quiere trazabilidad científica y de datos.
- Le importa especialmente la RAM y el rendimiento.
- Cuando dice “memoria” en este proyecto normalmente se refiere a RAM, salvo aclaración.
- No quiere que se inventen tests ni resultados.
- Prefiere que se analice el código real antes de modificar.
- Para UI, valora interfaces compactas, limpias, sin recortes, con scroll correcto y sin superposición.
- El carrusel no debe duplicar entradas al seleccionar.
- “Guardar” no debe abrir diálogo; “Guardar como” sí.

---

# 17. Archivos clave a buscar en un chat nuevo

Base actual:
- `proyecto_sombra_integrado_v31.zip`
- `archivos_reemplazo_vista_completa_v30.zip`

Contexto de continuidad:
- `CONTEXTO_PROYECTO_SOMBRA_v31.md`

Documentación histórica relevante:
- `CAMBIOS_GESTION_USUARIOS_v28.md`
- `CAMBIOS_TRAZABILIDAD_SESIONES_v27.md`
- `CAMBIOS_PANEL2_CONTENEDOR_v26.md`
- `CAMBIOS_INTERFAZ_ANCHO_v24.md`
- `CAMBIOS_CONFORT_RESOLUCION_v20.md`
- `CAMBIOS_ORGANIZACION_GUARDADO_v19.md`
- `CAMBIOS_OPTIMIZACION_RAM_v18.md`
- `AUDITORIA_INTEGRAL_v16.md`
- `MEMORIA_METODOLOGICA_v16.md`
- `PROTOCOLO_VALIDACION_CAMPO_v16.md`

---

# 18. Frase sugerida para comenzar el próximo chat

> Continuemos el proyecto Sombra desde la v31. Buscá en mi Biblioteca el archivo `CONTEXTO_PROYECTO_SOMBRA_v31.md` y el ZIP `proyecto_sombra_integrado_v31.zip`. Leé primero el contexto completo y después inspeccioná el código real. Edición y Modelo ya usan todo el bloque central frame2..frame5 para las pestañas 2D/3D; VTK es el motor 3D principal y la mejora es solo de render/interfaz, sin cambios científicos.

Con esa instrucción, la conversación nueva debería poder reconstruir el estado del proyecto sin depender de este chat largo.

---

# ACTUALIZACIÓN v32 — COMPATIBILIDAD VTK 9.7

**Base actual:** v32.

En Windows con VTK 9.7.0 se confirmó que VTK sí se instalaba e inicializaba, pero la escena fallaba al crear la barra de temperatura por la eliminación de `vtkRenderer.AddActor2D()`.

Corrección consolidada:
- `renderer.AddActor2D(scalar_bar)` → `renderer.AddViewProp(scalar_bar)`;
- no bajar ni reinstalar VTK por este error;
- mantener VTK como motor principal y Matplotlib como fallback;
- no se modificaron cálculos científicos;
- validación local disponible: 192 passed, 5 skipped.

Si aparece un error VTK posterior, conservar el diagnóstico detallado incorporado en v31 y tratarlo como un problema distinto; no volver a atribuir este `AttributeError` a OpenGL o al driver.
