# Instalación y recuperación — v35.6-etapa3

Entrega acumulativa sobre v35.6, compatible como actualización de Etapa 1 o Etapa 2. Conservá la versión anterior y una copia completa de tus proyectos antes de actualizar.

## Instalar en carpeta nueva

1. Extraé `proyecto_sombra_v35_6_etapa3_completo.zip` en una carpeta nueva cuya raíz contenga `main.py`.
2. Prepará un entorno Python y ejecutá `python -m pip install -r requirements.txt`. Para pvlib y UTCI instalá también `requirements-optional.txt`, o directamente `requirements-full.txt`.
3. Ejecutá `python main.py`. Las cuentas continúan en la ubicación estable de usuarios; no copies ni sustituyas esa base con otra vacía.
4. Si venís directamente de v35.6, seguí INSTRUCCIONES_ETAPA1.md para la base histórica junto a main.py o `--legacy-db`. Una instalación sin cuentas solicita un administrador humano; la clave histórica admin/admin debe sustituirse.
5. Abrí una **copia** de un proyecto existente. El primer guardado añade esquema de estado 2, inventario de hashes y generaciones recuperables, conservando los campos históricos.

## Aplicar el reemplazo

1. Cerrá la aplicación y copiá la instalación actual y los proyectos.
2. Extraé `proyecto_sombra_v35_6_etapa3_reemplazo.zip` en la raíz de esa copia, junto a `main.py`, aceptando reemplazar los archivos incluidos.
3. El ZIP contiene todos los archivos nuevos/cambiados acumulados desde v35.6. No borra bases, proyectos ni archivos privados de la carpeta. No contiene `users.db`.
4. Instalá dependencias que falten y ejecutá `main.py`.

## Cómo se recupera un proyecto

- Un guardado interrumpido después de preparar el conjunto se completa al abrir mediante su journal. Si los archivos centrales no coinciden con la generación confirmada, se conserva la diferencia y se recupera el conjunto íntegro.
- La advertencia de recuperación indica la carpeta con las copias preservadas cuando corresponde. La cuarentena vive dentro de `.sombra-recovery/quarantine/`; conservála hasta revisar los datos. Puede contener una base SQLite con análisis más recientes que el conjunto recuperado.
- No edites ni borres journals/generaciones para forzar una apertura. Si no hay generación íntegra o aparece un esquema futuro, mantené una copia de la carpeta y usá la versión compatible o importá el último `.3es` conocido como **proyecto nuevo**.
- Una advertencia de integridad de fotos, CSV o mapas indica que sus bytes cambiaron o faltan. Revisá el recurso y los resultados asociados; guardarlo nuevamente acepta el inventario actual y conserva el incidente, no restaura ni valida científicamente ese archivo.
- Ctrl+S/Guardar consolida y crea un respaldo completo en `respaldos/`. Exportar `.3es` crea una copia portable sin journals, locks ni respaldos recursivos. Conservá respaldos completos para recuperar versiones anteriores de fotografías y resultados.
- Mantener dos generaciones centrales aumenta el uso de disco, especialmente con una base de análisis grande. La cuarentena no se limpia sola. Los errores de guardado quedan visibles y en el registro local; no se anuncia guardado si falló la preparación del conjunto.

## Comprobación en la máquina de uso

1. Login/usuarios; abrir un proyecto anterior; guardar y reabrir; confirmar dos escenas, carrusel y valores capturados.
2. Guardar como, Duplicar y exportar/importar `.3es` en una carpeta nueva; confirmar fotos, matrices y máscaras.
3. Probar Edición/Modelo 2D/3D, cambio de panel, animación, cierre/reapertura y uso prolongado. La validación visual Windows/Tk/VTK sigue pendiente.
4. Verificar fecha de otro año, modos Simple/Avanzado y avisos científicos conforme a INSTRUCCIONES_ETAPA2.md.

Los registros están junto a los datos locales de usuarios, en `ProyectoSombra/logs/sombra.log` y sus rotaciones; en Windows, bajo `%APPDATA%`, y en Linux, bajo `XDG_DATA_HOME` o el directorio local de datos del usuario.

## Repetir la QA comprobada en Linux/Python 3.12

Desde la raíz del proyecto:

```bash
python3.12 -m venv .venv-qa
.venv-qa/bin/python -m pip install -r requirements-qa-linux-py312.lock
.venv-qa/bin/python -m pip check
.venv-qa/bin/python -m pytest -q -ra -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning -p no:cacheprovider
.venv-qa/bin/python test/run_optional_fallback.py
```

Este perfil usa OpenCV headless para pruebas sin pantalla. No lo combines con `requirements.txt` en el mismo entorno: para escritorio usá el perfil habitual. El flujo CI incluido está preparado para un repositorio GitHub, pero aún no se ejecutó remotamente y no publica ni despliega la aplicación.
