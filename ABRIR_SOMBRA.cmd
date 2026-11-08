@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno .venv de esta carpeta. Ejecuta PREPARAR_SOMBRA.cmd.
  exit /b 1
)
".venv\Scripts\python.exe" main.py
set "rc=%errorlevel%"
if not "%rc%"=="0" echo Si falta una dependencia, ejecuta PREPARAR_SOMBRA.cmd.
exit /b %rc%
