# Proyecto Sombra — cierre de la versión v35.6-etapa4.3.1

**Decisión: cerrar y congelar las fuentes de la etapa4.3.1 para uso técnico y piloto.** Esta revisión deja una entrega instalable desde Python y un perfil para generar el instalador en Windows. La validez científica de los resultados y la aceptación final de los binarios requieren evidencia adicional.

Fecha de revisión: **8 de noviembre de 2026**. Base: `sombra-poo(1).zip` (etapa4.3 reorganizada). SHA-256 de la base: `6816e0d103ccd2b95e523a07a0355fab3c6944f87a952275596ff4761a6b9b9d`.

## Qué se revisó y qué quedó resuelto

| Área | Qué quedó comprobado o resuelto | Límite de esta entrega |
|---|---|---|
| Arranque y dependencias | `PREPARAR_SOMBRA.cmd` instala la lista completa con Python 3.12 x64 en `.venv`; `ABRIR_SOMBRA.cmd` usa ese mismo intérprete. La versión y la ayuda local están visibles. Se corrigieron rutas de iconos que dependían de la carpeta de inicio. | La preparación requiere Python instalado y acceso a los paquetes. Se documenta cómo seleccionar el entorno en VS Code. |
| Cuentas y sesiones | El arranque de `app.py` ahora pasa por el flujo de autenticación de `main.py`. Se conserva la creación del administrador inicial y la ubicación de cuentas. La regresión incluye migración y gestión de usuarios. | El ZIP limpio excluye bases y copias de cuentas. Las cuentas del perfil existente no se sustituyen. |
| Proyectos y exportación | Pruebas y autocomprobación de JSON, SQLite, Excel, reapertura, copia, importación/exportación .3es y recuperación. Se conservan el guardado atómico, las comprobaciones de rutas y el esquema de estado 3. | La aceptación manual debe comprobar una copia de un proyecto real y los informes PDF/Excel desde la interfaz. |
| Fotografía y carrusel | Pruebas de máscaras, exclusiones manuales, persistencia, restauración y métricas con controles sintéticos. | Los materiales oscuros pueden confundirse con sombra. Faltan fotografías anotadas de forma independiente; no hay un clasificador automático de materiales. |
| Escenas, VTK y animación | Se mantienen los modos 2D/3D, el motor VTK, su alternativa Matplotlib y la animación. La etapa4.3 cuenta con informes automáticos de Windows aprobados para componentes reales de escritorio. | Los informes del 25/10 corresponden a la 4.3. El recorrido manual de esta revisión y la prueba del binario no están acreditados. |
| Modelos y meteorología | Se mantienen `advanced_radiative_v2`, modos estándar/avanzados, viento, UTCI, escenarios, meteorología y cálculo de incertidumbre. Paridad exacta con el ZIP recibido en los casos comparados. | No se conoce todavía el error respecto de mediciones en las condiciones de uso. |
| Arquitectura y entrega | Se mantiene el refactor incremental y se integró el perfil de compilación con las rutas reorganizadas. El código original del ZIP queda disponible como respaldo. | No se necesita un nuevo refactor para congelar esta revisión. La estructura restante es deuda de mantenimiento. |

## Evidencia verificable

- **ZIP recibido:** 615 pruebas aprobadas, reejecutadas sobre esta base.
- **Versión de cierre:** 619 pruebas aprobadas con Python 3.12.14 en Linux; se agregaron cuatro controles de arranque, ayuda y empaquetado.
- **Autocomprobación completa:** dependencias, recursos, cálculo y persistencia aprobados.
- **Paridad numérica:** coincidencia exacta en nueve casos de superficie, ocho de Tmrt radiativa y el caso de incertidumbre con semilla fija. Los archivos de ecuaciones se conservaron.
- **Windows anterior:** 14 controles de instalación y 4 de escritorio aprobados para la **etapa4.3**, Windows 10 build 19045. Los JSON aportados se conservan en `validacion/windows/2026-10-25_etapa4.3/`. El registro manual de esa entrega está sin completar.
- **Paquete:** perfil PyInstaller/Inno Setup, comprobación local de recursos y ausencia de datos privados en la copia de compilación. Los binarios Windows todavía no se generaron ni se probaron como parte de esta revisión.

Los resultados nuevos están en `validacion/qa_linux/etapa4.3.1/` y el estado consolidado en `validacion/estado_actual.json`. La evidencia automática informa si el software ejecuta los casos previstos; no mide la exactitud del modelo frente a la realidad.

## Qué queda y en qué orden

1. **Aceptar el escritorio en Windows.** Abrir esta revisión con `PREPARAR_SOMBRA.cmd` y `ABRIR_SOMBRA.cmd`. Completar [el recorrido manual](../validacion/windows/recorrido_cierre.md). Si se va a distribuir el instalador, generarlo con el perfil incluido y probar instalación, arranque y conservación de datos en una cuenta de prueba o en otro equipo.
2. **Validar la detección fotográfica.** Reunir fotos reales con anotaciones de sombra independientes, superficie comparable y material documentado. Evaluar F1, IoU y error de cobertura en puntos porcentuales, separando casos con y sin exclusiones. El banco incluido es sintético.
3. **Validar térmicamente en campo.** Preparar un piloto y reservar campañas independientes para validar después del ajuste. Definir condiciones, instrumentos, criterios y métricas antes de comparar. Informar Tmrt, aire y superficie por separado; no generalizar fuera de las condiciones medidas. Usar la [guía de campaña](VALIDACION_CAMPO.md).

**Alcance de uso:** esta versión puede congelarse para análisis exploratorio y piloto. Para distribución general del ejecutable falta la aceptación del paquete en Windows; para atribuir precisión a las estimaciones, falta la evidencia de campo. Los resultados de esa campaña se incorporarán a una revisión posterior, sin reabrir el desarrollo de esta versión por anticipado.
