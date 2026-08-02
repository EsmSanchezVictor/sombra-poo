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
