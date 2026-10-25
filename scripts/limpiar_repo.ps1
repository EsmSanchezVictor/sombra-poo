<#
 Limpieza de archivos que no deberían estar versionados en git (Etapa 4 · F2).

 - Por defecto es SIMULACIÓN (no cambia nada). Para aplicar:  .\scripts\limpiar_repo.ps1 -Aplicar
 - Usa `git rm --cached`: saca los archivos del repositorio pero NO los borra de tu disco.
 - Los patrones ya están en .gitignore; esto solo deja de rastrear lo que se subió antes.
 - NO reescribe el historial. users.db seguirá en commits antiguos; ver PLAN_TRABAJO_ETAPA4.md (F2).
 - Antes de aplicar, revisá que nada importe gui_copy.py ni "shape_selection copy.py".
#>
param([switch]$Aplicar)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path .git)) { throw 'Ejecutalo desde la raíz del repositorio (donde está la carpeta .git).' }

$archivos = @(
  'users.db', 'users.db.backup', 'debug.log',
  'sombra-poo.zip', 'sombra-poo2.zip',
  'gui_copy.py', 'shape_selection copy.py'
)
$carpetas = @('__pycache__', 'core/__pycache__', 'services/__pycache__', 'ui/__pycache__', 'test/__pycache__')

$flag = if ($Aplicar) { @() } else { @('--dry-run') }
Write-Host ($(if ($Aplicar) { 'APLICANDO' } else { 'SIMULACIÓN (agregá -Aplicar para ejecutar)' }))

foreach ($a in $archivos)  { git rm --cached --ignore-unmatch @flag -- $a }
foreach ($c in $carpetas)  { git rm -r --cached --ignore-unmatch @flag -- $c }

if ($Aplicar) {
  Write-Host "`nListo. Revisá con 'git status' y confirmá con:"
  Write-Host "  git commit -m `"chore: dejar de versionar db, logs, zips, pyc y copias`""
}
