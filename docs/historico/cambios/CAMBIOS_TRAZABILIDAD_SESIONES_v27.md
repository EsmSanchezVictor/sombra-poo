# v27 — Trazabilidad de sesiones y proyectos

## Objetivo

Registrar en la base de usuarios quién se conecta y en qué proyecto trabaja durante cada sesión de la aplicación.

## Nuevas tablas

### `user_sessions`

Una fila por autenticación correcta:

- `id`: identificador de sesión.
- `user_id`: usuario asociado mientras la cuenta exista.
- `username_snapshot`: nombre de usuario conservado históricamente.
- `login_at`: inicio de sesión en UTC ISO-8601.
- `logout_at`: cierre normal de sesión.
- `last_activity_at`: última actividad registrada.

### `session_projects`

Una fila por período continuo de trabajo en un proyecto:

- `session_id`: sesión a la que pertenece.
- `project_name`: nombre del proyecto.
- `project_root`: carpeta raíz del proyecto.
- `project_state_path`: archivo `.sombra` canónico.
- `action`: `created`, `opened`, `save_as`, `duplicated` o `imported`.
- `started_at`: comienzo del período.
- `ended_at`: fin del período.
- `last_activity_at`: última actividad del período.

Una misma sesión puede contener varios proyectos. Al cambiar de proyecto, el período anterior se cierra y se crea uno nuevo.

## Integración con la aplicación

- Login correcto → crea `user_sessions`.
- Crear proyecto → registra período `created`.
- Abrir proyecto → registra período `opened`.
- Guardar como → registra período `save_as` para el nuevo proyecto.
- Abrir una copia duplicada → `duplicated`.
- Abrir un proyecto importado → `imported`.
- Autosave/guardado → actualiza `last_activity_at`.
- Cambiar de proyecto → cierra el período anterior.
- Salir/X de la aplicación → cierra proyecto activo y sesión.

## Historial para administradores

El menú de administrador incorpora **Historial de sesiones**, con una tabla desplazable que muestra:

- sesión;
- usuario;
- ingreso/salida;
- proyecto;
- tipo de apertura;
- inicio/fin del trabajo en el proyecto;
- ruta del proyecto.

Las sesiones en las que no se abrió ningún proyecto también quedan registradas.

## Conservación histórica

`session_projects` depende de la sesión. `user_sessions.user_id` usa `ON DELETE SET NULL` y además conserva `username_snapshot`. Por lo tanto, si una cuenta se elimina posteriormente, su historial de sesiones y proyectos no se pierde.

## Migración

No hay que reemplazar `users.db`. Al iniciar v27 sobre una base existente, `DatabaseManager` crea automáticamente las nuevas tablas e índices con `CREATE TABLE IF NOT EXISTS`, sin modificar los usuarios existentes.
