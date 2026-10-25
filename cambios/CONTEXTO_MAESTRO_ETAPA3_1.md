# Continuidad actual — v35.6-etapa3.1

Esta entrega corrige un fallo de la Etapa 3 observado en Windows: [Errno 9] Bad file descriptor al guardar.

Causa detectada y reproducida con simulación: `atomic_output` y `backup_sqlite` llamaban a fsync sobre un archivo abierto rb. Ahora utilizan `core.safe_io.fsync_file`, que abre r+b sin truncar y cierra siempre. No ignorar los errores ni eliminar la sincronización como alternativa.

Aplicación v35.6-etapa3.1; release científico v35.6-etapa2. Esquemas sin cambios. Etapa 3 original preservada.

Resultado final en Linux/Python 3.12.14: 453 aprobadas. Sin opcionales (simulado): 447 aprobadas / 6 omitidas. Seis casos nuevos; cuatro casos reprodujeron EBADF antes de corregir. No se ejecutó Windows real. El próximo control inmediato es aplicar el parche en la instalación del usuario, Guardar con respaldo y reabrir el proyecto; registrar cualquier error restante desde sombra.log.

Leer CAMBIOS_ETAPA3_1.md, INSTRUCCIONES_ETAPA3_1.md y VALIDACION_ETAPA3_1.md. Después consultar CONTEXTO_MAESTRO_ETAPA3.md para arquitectura, recuperación, límites y próximos pasos. Sus 447 pruebas y release v35.6-etapa3 corresponden a la entrega anterior; esta corrección prevalece.

Las generaciones automáticas cubren JSON/Excel/SQLite; fotos y mapas se controlan por hash y sus versiones anteriores requieren .3es. Los cambios que nunca llegaron a guardarse y sólo estaban en memoria no se recuperan instalando el parche. No borrar journals ni cuarentenas.

Pendientes generales: revisión real Windows/Tk/VTK y uso prolongado; política DST ambigua/inexistente, ranking empírico y calibración Tmrt/Ta local/vegetación con mediciones de campo. No presentar el candidato como distribución final validada en Windows ni modelo calibrado.
