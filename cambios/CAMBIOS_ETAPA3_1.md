# Corrección de guardado Windows — v35.6-etapa3.1

Corrige el aviso «No se pudo completar el guardado: [Errno 9] Bad file descriptor» mostrado por la Etapa 3 en Windows. La versión anterior y sus fuentes se conservan como antecedente.

## Causa y corrección

Dos llamadas a os.fsync abrían el archivo con `rb`: la publicación atómica de Excel/NPZ/ZIP/copias y la sincronización del backup SQLite preparado. En Linux ese descriptor permite sincronizar; en Windows el backend necesita acceso de escritura. La captura del usuario coincide con este fallo y cuatro regresiones reproducen el mismo EBADF al simular ese requisito.

- `core/safe_io.py`: helper `fsync_file` abre el archivo existente con `r+b`, sin crearlo ni truncarlo, sincroniza y cierra el descriptor. `atomic_output` lo utiliza antes del reemplazo.
- `services/project_storage.py`: la copia SQLite se cierra y se sincroniza mediante el mismo helper. La base de origen conserva su conexión de sólo lectura y sus bytes.
- `core/app_version.py`: identifica la corrección como v35.6-etapa3.1.
- Se agregan seis regresiones de guardado y se actualiza la expectativa de la etiqueta de aplicación de una prueba anterior. No se cambian ecuaciones, estructura del proyecto ni versiones de sus esquemas. El release científico sigue siendo v35.6-etapa2.

Los errores reales de sincronización siguen propagándose: una preparación fallida impide publicar el estado nuevo. La corrección no consiste en ignorar EBADF ni en desactivar fsync.

## Fuentes técnicas

- Python, os.fsync (backend `_commit` en Windows): https://docs.python.org/3.12/library/os.html#os.fsync
- Microsoft, FlushFileBuffers (acceso GENERIC_WRITE): https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers

## Evidencia y límite

453 pruebas aprobadas en Linux/Python 3.12.14, sin advertencias finales; 447 aprobadas y 6 omitidas en la ruta sin pvlib/pythermalcomfort simulada. Las pruebas nuevas ejercitan el requisito de descriptor escribible, Excel real, backup SQLite, Guardar con respaldo, reapertura y copia, y fallos de disco que preservan el estado anterior. No se ejecutó Windows/Tk/VTK real: debe comprobarse Guardar en la máquina del usuario tras aplicar el parche.
