# Continuidad — Proyecto Sombra, 2026-10-04

Base estable preservada: v35.6 original. Etapa 1 preservada: v35.6-etapa1. Entrega actual: **v35.6-etapa2**, acumulativa. v35.7 descartada.

## Estado real

Etapa 1: seguridad/usuarios, migraciones de base y rutas estables, guardado JSON atómico y importación .3es protegida. Etapa 2: configuración efectiva de Tmrt y superficies, aislamiento Simple/Avanzado, año real, viento y alturas, dominios físicos/UTCI, diagnósticos de solver y procedencia capturada. Leer CAMBIOS_ETAPA2.md antes de modificar física.

Etapa 1 con opcionales instalados: 290 tests aprobados. Etapa 2: 377 aprobados; fallback simulado: 371 aprobados/6 omitidos. 87 casos nuevos. Código y ZIP revisados con manifiesto SHA256. No se ejecutaron GUI real, Windows ni campo.

## Próximo bloque

Etapa 3 por subbloques cortos: coordinación y recuperación Excel/JSON/SQLite, hashes de entradas/resultados, logging rotativo, versiones/migradores, refactor incremental de app_ui.py/scene3d.py, dependencias/CI y distribución. Corregir y verificar los horarios locales ambiguos/inexistentes de DST antes de afirmar cobertura horaria mundial completa. El ranking histórico de árboles permanece como estimación empírica; revisar si se incorpora al modelo efectivo avanzado. Hacer smoke visual en Windows con Tk/VTK y control de memoria.

Campo sigue separado: comparación con mediciones de Tmrt, Ta local bajo sombra y vegetación, errores y calibración. No puede cerrarse únicamente por código.

Mantener versiones y datos originales; no prometer una versión final distribuible antes de las verificaciones pendientes. Entregar fuentes completas, reemplazo, instrucciones, resultados, contexto y SHA256 después de cada bloque.

---
## Contexto anterior conservado

# Estado actualizado — 2026-10-04

Base original e inalterada: v35.6. Nueva entrega: **v35.6-etapa1**, implementada desde esa base y con 285 tests aprobados/5 omitidos. v35.7 queda descartada.

Etapa 1 de código cerrada en este entorno; la prueba gráfica y Windows queda pendiente. No afirmar versión final distribuible ni validación de campo. Los avisos sobre trabajo parcial en el documento histórico inferior describen la conversación anterior, no esta nueva entrega.

Siguiente bloque autorizado: Etapa 2, coherencia científica. Leer la documentación de esta entrega antes de tocar física. Cerrar subbloques con pruebas, y mantener el código original v35.6 para comparación.

## Evidencia nueva

- Baseline recibido reproducido: 224 aprobadas/5 omitidas, sin cambios.
- Entrega Etapa 1: 285 aprobadas/5 omitidas, sin fallos ni warnings en ejecución estricta. pvlib no instalado.
- Nuevos tests: 61 casos de autenticación e integridad.
- No se ejecutó GUI ni Windows. No hay mediciones reales nuevas.
- ZIP completo sin base privada de usuarios; ZIP de reemplazo con todos los módulos nuevos/modificados. Instrucciones para conservar cuentas e historial.
- Migración automática desde users.db junto a main.py hacia ruta estable. Bases históricas en otra ubicación requieren --legacy-db antes de inicializar la base estable.
- JSON atómico por archivo; coordinación Excel/JSON/SQLite sigue pendiente (Etapa 3).
- No se cambiaron fórmulas; ver VALIDACION_ETAPA1.md y MANIFIESTO_FUENTES_SHA256.json.

## Pendientes que se conservan

Etapa 2: año real de escenario, configuración efectiva central, aislamiento Simple/Avanzado, parser de viento, dominio UTCI y globo/Tmrt, balance superficial (convergencia/clipping/residual/iteraciones), clear-sky y procedencia meteorológica.
Etapa 3: coordinación y recuperación multiartefacto, SHA256 de inputs/resultados, logging rotativo, esquemas/migradores, refactor incremental de controladores/renderers, dependencias reproducibles/CI/SBOM, distribución y pruebas reales de GUI/Windows/memoria.
Campo: comparar Tmrt, Ta local y vegetación con mediciones para cuantificar errores y calibrar; no puede cerrarse solo con código.

---
# Documento histórico recibido (se conserva para continuidad)

# CONTEXTO MAESTRO — PROYECTO SOMBRA
## Documento de continuidad para una nueva conversación
Fecha: 2026-10-04

## 1. Qué es el proyecto
Proyecto Sombra es una aplicación científica de escritorio en Python/Tkinter para análisis de sombra, radiación, temperatura superficial, Tmrt, confort térmico y microclima en espacios verdes. Incluye edición de escenas, árboles, estructuras, análisis de imágenes, visualización 2D/3D con VTK, animación diurna, persistencia de proyectos, Excel, SQLite, usuarios, reportes, confort, incertidumbre y validación.

Prioridades permanentes: consistencia científica, compatibilidad Windows, estabilidad/RAM, aislamiento real entre modos Simple y Avanzado, interfaz limpia, trazabilidad/reproducibilidad y no afirmar validación de campo sin mediciones reales.

## 2. Forma de trabajo acordada
El usuario espera implementación real: inspeccionar código, modificar archivos, ejecutar pruebas y entregar artefactos. Para versiones importantes: ZIP completo, ZIP de reemplazo, contexto actualizado, cambios, instrucciones y SHA256. No afirmar pruebas no ejecutadas. Evitar reescrituras gigantes y física nueva sin justificación. Trabajar por etapas y subbloques cortos para evitar timeouts.

## 3. Última versión estable
La última versión estable consolidada es **v35.6**.

Validación informada de v35.6: **224 tests aprobados, 5 omitidos, 0 errores, 0 ResourceWarning**.

La fase posterior de seguridad/integridad fue iniciada, pero **NO debe considerarse cerrada ni estable** hasta volver a inspeccionar el código real, ejecutar baseline y validar todos los cambios.

## 4. Historial relevante
- v17: carrusel + DB por `analysis_id`; restaurar sin recalcular/duplicar.
- v18: optimización RAM.
- v19: organización de carpetas, autosave y backups.
- v20: confort vectorizado, resolución 64–640 (default 128).
- v21–v26: mejoras de layout/paneles.
- v27: trazabilidad usuario/sesión/proyecto.
- v28: gestión de usuarios.
- v29: rediseño 3D VTK.
- v30: viewport mayor, copas multilobuladas, iluminación, render HQ.
- v31: compatibilidad Windows/VTK, MSAA 0, diagnóstico.
- v32: compatibilidad VTK 9.7 (`AddViewProp`).
- v33: capa térmica 3D, isotermas, árboles/estructuras visibles, fallback Matplotlib.
- v34: presets, Verano/Invierno, Soleado/Nublado, viento, superficie, temperatura avanzada, aislamiento parcial simple/avanzado, pvlib/Ineichen avanzado.
- v35: indicador solar 2D y Sol 3D.
- v35.1: animación diurna Fase 1.
- v35.2: animación 3D persistente, cámara fija, colorbars 2D estables.
- v35.3: conexiones SQLite cerradas correctamente.
- v35.4: formas de copa 2D/3D y persistencia.
- v35.4.1: formulario de forma de copa; se detectó problema de codificación ZIP con `diseño.py`.
- v35.4.2: módulo interno cambiado a `diseno.py`; `core/crown_shapes.py` incluido; reemplazo autosuficiente.
- v35.5: doble ventana Árbol/Estructura corregida; materiales depurados.
- v35.6: homogeneización global de Toplevel con `ui/modal_style.py`.

## 5. Formas de copa
Opciones actuales: Esférica, Cónica, Columnar, Piramidal, Extendida, Irregular y Llora.

Reglas: Esférica por defecto en proyectos antiguos; forma persistida; representada en 2D/3D y animación. Por ahora la forma es geométrica/visual. **No modificar las ecuaciones físicas de sombra/radiación según forma de copa sin validación específica.**

## 6. Animación diurna
- Instantánea o animación diurna.
- Primero calcula la secuencia; después reproduce sin recalcular cada frame.
- 2D: sombra + temperatura.
- 3D: un único viewport VTK persistente.
- Sol, sombra y temperatura se actualizan.
- Cámara y escala térmica deben permanecer estables.
- Interpretación científica: secuencia cuasi-estacionaria, no modelo térmico transitorio con inercia entre frames.

## 7. Materiales
Catálogo depurado a 43 materiales visibles únicos. Se eliminó duplicación de `Concreto Translúcido`/`concreto translucido`, manteniendo compatibilidad. `Policarbonato` y `Policarbonato (paneles)` permanecen separados como variantes.

## 8. Base científica que no debe regresionar
- geometría solar y zonas horarias;
- modelo diario de temperatura;
- transmitancia efectiva `tau_eff = (1-S) + S*tau_full`;
- cobertura de sombra separada de atenuación;
- Heat Index / temperatura aparente con Ta;
- UTCI con Tmrt;
- Tmrt estándar empírico/calibrable y avanzado radiativo;
- Ta local bajo sombra empírica/calibrable;
- balance de superficie;
- materiales alpha/rho/tau;
- vegetación/ET, FAO-56 aproximado, LAI, Kc, fenología;
- meteorología e interpolación de huecos cortos;
- Monte Carlo;
- validación RMSE/MAE/bias/R²/n.

Limitación principal: validación externa con mediciones de campo.

## 9. Auditoría pendiente — Seguridad e integridad
### Usuarios/autenticación
- eliminar definitivamente `admin/admin`;
- primer administrador humano obligatorio en primera ejecución;
- mantener usuario técnico interno oculto, propuesto `__sombra_internal__`;
- ese usuario no debe iniciar sesión normal, aparecer en gestión, contar como último admin humano ni poder eliminarse/desactivarse desde UI normal;
- política de contraseña humana coherente backend/UI, mínimo recomendado 12 caracteres;
- detectar `admin/admin` histórico y forzar sustitución;
- espera progresiva ante intentos fallidos;
- retirar recuperación insegura antigua.

### Base de usuarios
- `users.db` no debe depender del CWD;
- ruta estable, p.ej. `%APPDATA%\\ProyectoSombra\\users.db`;
- migrar DB antigua automáticamente;
- permitir rutas temporales inyectables en tests.

### Migraciones
- convertir contraseñas antiguas en texto plano transaccionalmente;
- no dejar backups/tablas residuales con contraseñas en claro.

### Rutas/proyectos
- rechazar `..`, rutas absolutas, `/`, `\\`, nombres reservados Windows;
- comprobar containment con `commonpath`;
- validar `analysis_id` antes de usarlo como ruta.

### `.3es`
- no usar `extractall()` sin controles;
- limitar número de miembros, tamaño individual/total, ratio de compresión;
- impedir Zip Slip/ZIP bombs;
- confinar rutas importadas al proyecto.

### Persistencia básica
- JSON atómico: temp en mismo directorio + flush/fsync + `os.replace`;
- eliminar `tempfile.mktemp`.

## 10. Auditoría pendiente — Coherencia científica
- eliminar año hardcodeado 2026 en geometría solar y usar año real del escenario;
- crear configuración efectiva central (`EffectiveScenarioConfig` o equivalente) para cálculo puntual, mapa, animación, confort, incertidumbre, reporte y exportación;
- impedir que ajustes avanzados ocultos afecten modo Simple;
- unificar parser de viento (`core.climate_profile` y `core.vegetation`);
- exponer `converged`, `boundary_clipped`, residual e iterations del balance superficial;
- unificar clear-sky/procedencia meteorológica;
- validar dominio de globo negro → Tmrt para evitar resultados complejos;
- validar dominio de UTCI y marcar “fuera de dominio UTCI”.

## 11. Arquitectura/robustez pendiente
- refactor incremental de `ui/app_ui.py` y `ui/scene3d.py`;
- dirección: EffectiveScenarioConfig, CalculationService, ProjectRepository, AuthService, renderers, ReportService, ExportService, controladores por panel;
- logging rotativo sin contraseñas/PII innecesaria;
- versionado separado de esquema/layout/metodología;
- migradores;
- guardado coordinado Excel/JSON/SQLite con `generation_id` y recuperación;
- inventario SHA256 de inputs/resultados;
- dependencias reproducibles, CI, SBOM y auditoría de dependencias;
- enlaces de ayuda reales o deshabilitados.

## 12. Plan de cierre en tres etapas
### ETAPA 1 — Seguridad, usuarios e integridad
Incluye admin seguro, primer admin humano, usuario técnico interno, contraseñas, login backoff, users.db estable, migraciones, rutas de proyectos, `.3es`, `analysis_id`, JSON atómico y temporales seguros.

**Estado: INICIADA, NO CERRADA.** Se habían comenzado cambios sobre v35.6, pero no deben darse por terminados ni productivos sin revalidar todo.

### ETAPA 2 — Coherencia científica
Año real, configuración efectiva central, aislamiento Simple/Avanzado, viento, Tmrt, UTCI, balance superficial, procedencia meteorológica.

### ETAPA 3 — Robustez, arquitectura y distribución
Guardado coordinado/recuperación, SHA256, logging, versiones/migradores, refactor incremental, dependencias/CI y cierre de distribución.

## 13. Estado exacto al cambiar de chat
- Base estable: **v35.6**.
- Trabajo en curso: **Etapa 1 — Seguridad, usuarios e integridad**.
- No asumir que cambios parciales posteriores a v35.6 están cerrados.
- En el nuevo chat: inspeccionar base real, ejecutar baseline, continuar por subbloques cortos y testear cada subbloque antes del siguiente.
- Al cerrar Etapa 1: ZIP completo, ZIP de reemplazo, contexto, cambios, instrucciones, SHA256, pruebas ejecutadas y pendientes para Etapa 2.

## 14. Reglas de continuidad
- No empezar desde cero.
- No perder v35.6.
- No mezclar Etapa 1 con Etapa 2 antes de cerrar pruebas.
- No introducir física nueva de formas de copa sin validación.
- No ocultar warnings: corregir la causa.
- No afirmar validación no ejecutada.
- No sobrescribir una versión estable con un parche no probado.
- En Windows, preferir nombres internos ASCII cuando eviten problemas (`diseno.py`).
- Mantener compatibilidad hacia atrás.
