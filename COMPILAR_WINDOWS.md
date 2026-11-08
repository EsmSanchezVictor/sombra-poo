# Compilar Proyecto Sombra v35.6-etapa4.3.5

El perfil de compilación ya está dentro de esta entrega. Usá Windows de 64 bits y el entorno local `.venv` con Python 3.12 de 64 bits. Si todavía falta, ejecutá `PREPARAR_SOMBRA.cmd` desde CMD en la raíz de la aplicación.

Para instalar el empaquetador:

```bat
.venv\Scripts\python.exe -m pip install -r windows_build\requirements-build.txt
```

Para generar y comprobar el ejecutable:

```bat
COMPILAR_WINDOWS.cmd --verify-desktop
```

Para generar ambos archivos en una sola ejecución, instalá primero Inno Setup 6 o 7 desde https://jrsoftware.org/isdl.php y ejecutá:

```bat
COMPILAR_WINDOWS.cmd --installer --verify-desktop
```

El resultado es `dist\ProyectoSombra\ProyectoSombra.exe` y, con `--installer`, `release\ProyectoSombra_Setup_35.6_etapa4.3.5_x64.exe`. Si usás la versión portable, mantené unida toda la carpeta `dist\ProyectoSombra`, incluido `_internal`. Si no se detecta Inno Setup, usá `--iscc "ruta\ISCC.exe"`.

El perfil selecciona los archivos necesarios, genera una copia temporal y prueba el código y el ejecutable. Con `--verify-desktop` prueba también Tk/Matplotlib/VTK del ejecutable. Revisá `release\build_windows.json`, `release\autocomprobacion_exe.json` y `release\escritorio_exe.json`. Si falla, conservá el primer error y ese informe. Para diagnóstico se puede usar `--console`.

El instalador, que se genera sin firma digital, coloca el programa por usuario en `%LOCALAPPDATA%\Programs\ProyectoSombra`. Los datos persistentes se guardan fuera de la carpeta del programa, en `%APPDATA%\ProyectoSombra`. La copia de compilación no incorpora cuentas ni proyectos de la máquina de desarrollo.

Antes de distribuir el instalador, probá instalación, arranque, guardado, reapertura, actualización y desinstalación en una cuenta de prueba o en otra computadora. Esta entrega incluye el perfil y sus pruebas locales, no un binario generado ni validado en Windows.
