@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -c "import struct, sys; assert sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8, 'Se requiere Python 3.12 de 64 bits'"
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements-full.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto :error
echo Listo. Ejecuta ABRIR_SOMBRA.cmd.
exit /b 0
:error
echo No se pudo preparar .venv. Revisa el primer error de arriba.
exit /b 1
