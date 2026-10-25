# Cambios — v35.6-etapa1

Se parte exclusivamente de la v35.6. No se reutiliza la v35.7 descartada.

## Usuarios y autenticación

- Eliminada la creación automática de admin/admin. Una instalación nueva exige crear un administrador humano; cerrar el formulario cancela el arranque.
- Cuenta técnica __sombra_internal__: oculta, inactiva, sin privilegios de administrador y con secreto aleatorio. No inicia sesión ni puede editarse, borrarse, activarse o cambiar su clave mediante APIs normales.
- La cuenta interna no cuenta para proteger al último administrador humano.
- La contraseña histórica admin/admin se detecta al abrir la base. No admite sesión ordinaria: requiere verificar la contraseña actual y sustituirla antes de ingresar.
- Contraseñas nuevas y restablecidas: mínimo 12 caracteres, máximo 1024 y no solo espacios. Las claves históricas distintas de admin/admin siguen siendo compatibles hasta que se cambien.
- Política compartida backend/formularios y restablecimiento desde gestión de administrador autenticado. Retirada la recuperación que cambiaba claves sin verificar identidad.
- Demora persistente por cuenta: desde el tercer fallo, 1, 2, 4… segundos, hasta 60; no se duerme ni bloquea el hilo Tk.

## Base y migración

- users.db estable en %APPDATA%/ProyectoSombra/users.db (Windows) o XDG_DATA_HOME/ProyectoSombra/users.db / ~/.local/share/ProyectoSombra/users.db (Linux).
- Primer arranque migra automáticamente la base junto a main.py si no existe la base estable. Las rutas explícitas siguen disponibles para pruebas y migración manual.
- Conversión transaccional de texto plano; conserva IDs, datos e historial. Recupera usuarios de users_old y corrige la FK histórica de sesiones si apuntaba a esa tabla.
- Elimina tablas residuales con claves en claro; secure_delete, checkpoint y VACUUM. El respaldo conocido users.db.backup se sanea conservando sus usuarios. No se promete borrado forense de copias externas, snapshots del sistema o respaldos desconocidos.
- La publicación de la base migrada no sobrescribe una base creada por otro arranque.

## Rutas e importación

- Nombres y analysis_id validados antes de crear carpetas. Rechazo de traversal, rutas absolutas/drive, separadores y nombres reservados Windows; containment mediante realpath/commonpath, incluyendo enlaces que escapan del proyecto.
- Referencias relativas portables. Las referencias externas en proyectos locales viejos quedan sin cargar; no se leen ni se mueven archivos externos a partir de esas referencias.
- .3es: preflight de rutas, colisiones en Windows, enlaces/archivos especiales y cifrado. Máximo 10.000 entradas, 256 MiB por archivo, 1 GiB total y ratio de compresión 200; JSON de estado máximo 8 MiB.
- Extracción con conteo efectivo en carpeta temporal, sin extractall. Validación del estado y de referencias en SQLite antes de publicar el proyecto. Una importación rechazada no deja carpeta final.
- Compatibilidad con paquetes planos y paquetes legacy dentro de una carpeta envolvente.

## Escrituras y temporales

- JSON: temporal en mismo directorio, flush/fsync y os.replace; limpieza ante errores, manteniendo la versión anterior.
- Se aplica a estado/copia de proyecto, inventarios, preferencias, especies propias, auditoría y máscaras VIA.
- PDF reemplaza mktemp por TemporaryDirectory.
- Se corrigió también la llamada incompleta a AddUserWindow en el panel de login alternativo.

Las ecuaciones científicas, los motores 2D/3D y las formas de copa se conservan. Ver VALIDACION_ETAPA1.md para alcance y limitaciones.
