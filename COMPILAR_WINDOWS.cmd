@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno .venv de Python 3.12. Consulte COMPILAR_WINDOWS.md.
  exit /b 1
)
".venv\Scripts\python.exe" "tools\build_windows.py" %*
exit /b %errorlevel%
