# Validación de la corrección v35.6-etapa3.1

2026-10-04. Linux x86_64, Python 3.12.14. Se reutiliza el entorno limpio y el lock de QA ya comprobados en Etapa 3; no hay dependencias nuevas.

- Antes de corregir: cuatro casos con el requisito de Windows simulado fallan con Errno 9. Dos pruebas ajenas a esa reproducción se excluyeron. REGRESION_ANTES_ETAPA3_1.txt contiene la evidencia.
- Después: 453 aprobadas, cero fallos y cero omitidas, sin advertencias finales. Son las 447 pruebas de Etapa 3 más seis regresiones nuevas.
- Fallback simulado sin pvlib/pythermalcomfort: 447 aprobadas, seis omitidas por esas dependencias opcionales.
- Comando: `python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider`.

Los seis casos están en test/test_stage3_1_windows_sync.py: publicación binaria, escritura/lectura Excel, backup SQLite, Guardar con respaldo + reabrir + copiar bajo el rechazo de lectura simulado; fallo real simulado de fsync antes de reemplazar un binario; fallo de sincronización del backup que no publica otro estado del proyecto.

La simulación intercepta los descriptores de archivos abiertos por Python y rechaza sincronizar los de sólo lectura. No simula todo Windows, su sistema de archivos, el CRT completo o la interfaz. El test de Windows real sigue pendiente.

Se comprueba sintaxis de todos los Python, SHA256 de fuentes, conservación de las fuentes de Etapa 3 y que sólo cambian sus dos módulos de guardado, etiqueta de aplicación y pruebas/documentación. Cada ZIP se verifica con testzip. El parche sobre Etapa 3 y el reemplazo sobre v35.6 reconstruyen byte a byte todos los archivos suministrados por el completo. No se borran archivos privados ni se incluyen bases de usuarios.

No se modifican los cálculos físicos ni se cierran los pendientes de GUI/Windows, DST, ranking empírico o validación de campo de Etapa 3.
