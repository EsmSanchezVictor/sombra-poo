# Continuidad — Proyecto Sombra, 2026-10-04

**Entrega actual: v35.6-etapa3**, acumulativa sobre v35.6. Base original y Etapas 1/2 preservadas. v35.7 descartada. Los textos antiguos incluidos son históricos; este documento y CAMBIOS_ETAPA3.md prevalecen como estado actual.

## Estado real

- Etapa 1: usuarios humanos/administrador inicial, cuenta técnica interna, retirada de admin/admin, rutas y migraciones de base, JSON atómico e importación .3es protegida.
- Etapa 2: configuración efectiva científica compartida, aislamiento Simple/Avanzado, año real, viento/alturas, dominios UTCI/físicos, diagnóstico superficial y procedencia de resultados.
- Etapa 3: conjunto central recuperable de estado/Excel/SQLite, hashes de entradas y resultados con historial de incidentes, copias/importación/exportación preparadas, escrituras atómicas NPZ/Excel/copias, versiones y migradores, rechazo de esquemas futuros, bloqueo entre procesos, logs rotativos, refactor incremental y perfil reproducible de QA Linux. CI Linux/Windows preparado; no ejecutado remotamente.

Pruebas finales en instalación limpia Linux/Python 3.12.14: **447 aprobadas**. Ruta sin pvlib/pythermalcomfort simulada: **441 aprobadas, 6 omitidas**. **70 casos nuevos** de esta etapa. Etapa 2 al iniciar: 377 aprobadas. SHA256 de las fuentes previas confirma conservación; las ecuaciones y el controlador VTK se mantienen. El release científico sigue siendo v35.6-etapa2; el release de aplicación es v35.6-etapa3.

## Precauciones concretas de continuidad

El autosave retiene dos generaciones de JSON/escenas/SQLite. No hace una copia histórica de todas las fotografías y mapas. El inventario detecta cambios/faltantes; los respaldos .3es preservan el proyecto completo. Las diferencias centrales se guardan en cuarentena antes de recuperar; registros SQLite posteriores no se fusionan automáticamente. Leer INSTRUCCIONES_ETAPA3.md antes de manipular un journal o una cuarentena.

El refactor es incremental: app_ui.py aún tiene 4985 líneas. No reescribir módulos completos sin una necesidad concreta y comprobación de resultados. Mantener configuración efectiva y procedencia de punto/mapa/superficie separadas de los selectores ocultos.

## Próximo trabajo útil

1. Ejecutar una revisión visual y funcional en la máquina Windows real: usuarios, proyecto previo, carrusel, guardar/copiar/importar, Tk/VTK 2D/3D, animación y estabilidad prolongada. Registrar entorno y resultado; CI preparado no equivale a este smoke visual. Preparar instalador sólo después de comprobar ese entorno.
2. Resolver explícitamente horas locales ambiguas/inexistentes por DST antes de afirmar cobertura horaria mundial completa. El ranking de árboles conserva su estimación empírica y debe seguir identificado como tal, o abordarse en un bloque científico específico.
3. Medir Tmrt, Ta local bajo sombra, condiciones meteorológicas/altura del viento y vegetación; comparar errores y calibrar con datos reales independientes. Las pruebas sintéticas existentes no cierran esta validación.

No prometer distribución final ni precisión local calibrada mientras esas verificaciones estén abiertas. Mantener originales y datos, entregar ZIP completo/reemplazo, cambios, instrucciones, evidencia, contexto y SHA256 después de cada bloque. No crear etapas nuevas para retoques triviales: agruparlos en un cierre verificable y mantener el alcance concreto.

## Antecedente histórico

Ver CONTEXTO_MAESTRO_ETAPA2.md y CONTEXTO_MAESTRO_ETAPA1.md conservados dentro de los ZIP. Su referencia a Etapa 3 como pendiente quedó superada por esta entrega; sus límites científicos y de campo siguen vigentes cuando no se indica una corrección aquí.
