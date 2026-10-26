# v28 — Gestión de usuarios corregida y segura

## Problema confirmado

La pantalla anterior usaba 12 encabezados, pero recorría `SELECT * FROM users`, que devuelve también `password_hash` y `salt` (y en v27 además columnas administrativas nuevas). Por eso el hash aparecía bajo «Nombre» y el resto de los datos quedaba desplazado una o más columnas.

## Corrección de datos

- La interfaz ya no usa `SELECT *`.
- Se agregó `fetch_users_for_management()`, una proyección explícita que devuelve solamente los campos permitidos para administración.
- `password_hash` y `salt` nunca se entregan a la tabla de gestión.
- SQLite usa `sqlite3.Row`, por lo que el código nuevo accede a los campos por nombre y no por posiciones frágiles.
- Las bases existentes se migran automáticamente, sin borrar usuarios ni historial.

## Nueva interfaz

La tabla se reemplazó por `ttk.Treeview` con columnas:

- Usuario
- Nombre y apellido
- Rol
- DNI
- Email
- Teléfono
- Ciudad
- Estado
- Último ingreso

Incluye scrollbar vertical/horizontal, selección de fila, doble clic para editar, búsqueda y filtros por rol/estado.

## Operaciones

- Nuevo usuario
- Editar usuario seleccionado
- Restablecer contraseña
- Activar / desactivar
- Eliminar

Ya no se pide el ID manualmente.

## Seguridad y consistencia

- Nuevos usuarios: contraseña mínima de 8 caracteres y confirmación.
- El email se valida si se informa.
- No se permite un username duplicado.
- No se puede desactivar/eliminar al último administrador activo.
- No se puede eliminar ni desactivar desde la acción rápida la cuenta conectada.
- La eliminación de la cuenta no borra su historial de sesiones: se conserva `username_snapshot`.
- Se agregan/migran `is_active`, `created_at`, `updated_at` y `last_login`.
- Un usuario inactivo no puede autenticarse.

## Compatibilidad con v27

La trazabilidad usuario → sesión → proyecto de v27 se conserva sin cambios. No reemplazar `users.db`: la v28 migra la base existente automáticamente al iniciar.
