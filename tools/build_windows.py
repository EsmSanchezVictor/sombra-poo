"""Empaquetar etapa4.3.6 en Windows x64 usando el entorno Python comprobado."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from windows_build.build_support import prepare_stage, sha256


def compiler_path(explicit=None):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise ValueError(f'No existe el compilador indicado: {path}')
        return path
    detected = shutil.which('ISCC.exe')
    if detected:
        return Path(detected)
    for variable in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        base = os.environ.get(variable)
        if not base:
            continue
        for folder in ('Inno Setup 7', 'Inno Setup 6', 'Programs/Inno Setup 7', 'Programs/Inno Setup 6'):
            candidate = Path(base)/folder/'ISCC.exe'
            if candidate.is_file():
                return candidate
    raise ValueError('No se encontró Inno Setup. Instálelo o indique --iscc "ruta\\ISCC.exe".')


def validate_host():
    if sys.platform != 'win32':
        raise ValueError('El ejecutable Windows se genera en Windows, no en Linux/macOS.')
    if sys.version_info[:2] != (3, 12) or struct.calcsize('P') != 8:
        raise ValueError('Use el entorno .venv con Python 3.12 de 64 bits.')
    if importlib.util.find_spec('PyInstaller') is None:
        raise ValueError('Falta PyInstaller: .venv\\Scripts\\python.exe -m pip install -r windows_build\\requirements-build.txt')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', action='store_true', help='Generar además el instalador con Inno Setup')
    parser.add_argument('--iscc', help='Ruta de ISCC.exe si no se encuentra automáticamente')
    parser.add_argument('--console', action='store_true', help='Mostrar consola para diagnosticar el ejecutable')
    parser.add_argument('--verify-desktop', action='store_true', help='Comprobar Tk/VTK reales del .exe')
    args = parser.parse_args()
    try:
        release_dir = ROOT/'release'
        release_dir.mkdir(exist_ok=True)
        report_path = release_dir/'build_windows.json'
        report = dict(status='building', platform=platform.platform(), python=sys.version,
                      windows_executable_tested=False, windows_desktop_components_tested=False,
                      human_visual_review=False, installer_generated=False, field_validation=False)
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        validate_host()
        compiler = compiler_path(args.iscc) if args.installer else None
        build_root = ROOT/'build'/'windows-packaging'/uuid.uuid4().hex
        def command(argv, **kwargs):
            print('Ejecutando:', subprocess.list2cmdline([str(a) for a in argv]), flush=True)
            subprocess.run([str(a) for a in argv], check=True, cwd=ROOT, **kwargs)
        # Captures the actual Windows environment, rather than applying the Linux QA lock.
        freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
        (release_dir/'entorno_compilacion.txt').write_text(freeze, encoding='utf-8')
        report['stage'] = prepare_stage(ROOT, build_root/'stage')
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        from services.installation_check import run_installation_check
        preflight = run_installation_check(require_full=True)
        (release_dir/'autocomprobacion_fuente.json').write_text(json.dumps(preflight, indent=2), encoding='utf-8')
        if preflight['status'] != 'passed':
            raise ValueError('La autocomprobación del código fuente falló; revise release/autocomprobacion_fuente.json.')
        env = dict(os.environ, SOMBRA_BUILD_STAGE=str(build_root/'stage'),
                   SOMBRA_BUILD_CONSOLE='1' if args.console else '0')
        command([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                 '--distpath', ROOT/'dist', '--workpath', build_root/'pyinstaller',
                 ROOT/'windows_build'/'ProyectoSombra.spec'], env=env)
        executable = ROOT/'dist'/'ProyectoSombra'/'ProyectoSombra.exe'
        if not executable.is_file():
            raise ValueError('No se generó ProyectoSombra.exe.')
        report['exe_sha256'] = sha256(executable)
        for mode, filename in [('--self-check', 'autocomprobacion_exe.json')] + (
                [('--desktop-check', 'escritorio_exe.json')] if args.verify_desktop else []):
            path = release_dir/filename
            # Remove only an old diagnostic with this exact reserved name, so it cannot
            # be mistaken for a successful report from this new executable.
            path.unlink(missing_ok=True)
            command([executable, mode, '--report', path], timeout=180)
            output = json.loads(path.read_text(encoding='utf-8'))
            if output.get('status') != 'passed':
                raise ValueError(f'Falló el ejecutable: revise {path}')
            if mode == '--self-check':
                report['windows_executable_tested'] = True
            else:
                report['windows_desktop_components_tested'] = True
        if args.installer:
            command([compiler, '/DProjectRoot='+str(ROOT), ROOT/'windows_build'/'ProyectoSombra.iss'])
            setup = release_dir/'ProyectoSombra_Setup_35.6_etapa4.3.6_x64.exe'
            if not setup.is_file():
                raise ValueError('Inno Setup no generó el archivo esperado.')
            report['installer_generated'] = True
            report['installer_sha256'] = sha256(setup)
        report['status'] = 'passed'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Ejecutable:', executable)
        if args.installer:
            print('Instalador:', setup)
        print('Revise el programa completo y pruebe el instalador antes de distribuirlo.')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        if 'report_path' in locals() and 'report' in locals():
            report.update(status='failed', error=str(exc))
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
