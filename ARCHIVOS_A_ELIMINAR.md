# Archivos a eliminar (código muerto / duplicado)

Confirmado revisando qué importa realmente `ui/app_ui.py` (el punto de
entrada real de la app moderna, en `core/services/ui`): estos archivos
no los usa nadie y solo generan confusión sobre cuál es la versión
vigente.

| Archivo | Por qué se puede borrar |
|---|---|
| `detector_sombras.py` (raíz) | Reemplazado por `services/shadow_detector.py`, que es el que realmente importa `ui/app_ui.py`. Nadie lo importa. |
| `services/procesamiento_imagen.py` (`ProcesadorSombras`) | Misma función que `services/shadow_detector.py` pero versión vieja. Nadie lo importa. |
| `motor_solar.py` (raíz) | Reemplazado por `services/solar_engine.py` + `shadow_temp.py::Temperatura`. Nadie lo importa. |
| `gui_copy.py` | Nombre "copy" — probablemente una versión vieja de `ui/app_ui.py` guardada a mano. Confirmar con el autor cuál es la vigente antes de borrar. |
| `shape_selection copy.py` | Mismo caso, versión "copy" de `shape_selection.py`. |
| `sombra-poo.zip`, `sombra-poo2.zip` | Snapshots manuales — el historial de git ya cumple esa función. |
| `debug.log` | Log de ejecución, no debería versionarse. |
| `users.db` | Base de datos con datos de usuarios reales — nunca debería estar en el repo (ver también el fix de `database_manager.py`). |
| `image_processor copy.py` | **ELIMINADO** (era un duplicado de `image_processor.py`, no lo importa nadie). |
| `modelo_con_excel copy.py` | **ELIMINADO** (duplicado de `modelo_con_excel.py`, con bugs que el original ya no tenía). |
| `services/borrar procesamiento_imagen.py` | **ELIMINADO** (versión vieja de `services/shadow_detector.py`, nadie lo importa). |
| `test/test/test/test_detector_sombras.py` | **ELIMINADO** (testeaba `detector_sombras.py`, código muerto que ya no existe). |
| `ver` | **ELIMINADO** (basura suelta: "123456789\n987654321"). |

## Ya aplicado

- `test/test/test_image_processor.py` y `test/test_physics.py` se movieron
  a `test/` (se aplanó el anidamiento `test/test/`).
- `users.db`, `__pycache__/` y `proyectos/` se sacaron del control de
  versiones (`git rm --cached`) y quedaron cubiertos por `.gitignore`.
  Los archivos siguen en disco donde la app los necesita; solo dejaron
  de versionarse. OJO: como ya estuvieron commiteados, siguen vivos en
  el historial de git — si querés purgarlos de verdad (users.db con
  contraseñas viejas), hay que reescribir el historial (BFG repo-cleaner
  o `git filter-branch`).

## Antes de borrar `database_manager.py`, `add_user_window.py`, `admin_panel.py`, `login_window.py`, `main.py`/`main_app.py`/`app.py`

Estos NO aparecen importados desde `core/services/ui` (el árbol que sí
está wireado a `ui/app_ui.py`), así que probablemente son un flujo de
login/administración **separado y más viejo** que convivía con la app
antes de la reestructuración a `core/services/ui`.

**Antes de tocarlos, confirmá esto**: ¿el punto de entrada real hoy es
`main.py` (el que arranca `ui/app_ui.py::SombraApp`) o alguno de los
otros (`main_app.py`, `app.py`) que arrancan el flujo de login viejo?
Si el login con `database_manager.py` sigue en uso, el fix de hash de
contraseñas que te dejo abajo sigue siendo necesario. Si no, ese flujo
entero también es candidato a borrado — pero eso lo tenés que confirmar
vos, porque no tengo forma de saber cuál corre en producción.

> NOTA: `main.py` SÍ arranca el flujo de login (`MainApp`) que abre
> `SombraApp` — así que el flujo de login está vivo, y `main_app.py` y
> `login_window.py` ya usan `db.authenticate()` (ver README_CAMBIOS).
