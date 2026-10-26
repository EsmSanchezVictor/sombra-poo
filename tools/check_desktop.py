"""Abre ventanas temporales; separa un fallo nativo VTK del proceso de informe."""
from pathlib import Path
import argparse
import json
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.safe_io import atomic_write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--vtk', action='store_true')
    parser.add_argument('--require-windows', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        from services.desktop_check import run_desktop_check
        report = run_desktop_check(render_vtk=args.vtk, require_windows=args.require_windows)
        atomic_write_json(args.report, report)
        return 0 if report['status'] == 'passed' else 1
    with tempfile.TemporaryDirectory(prefix='sombra-desktop-') as folder:
        child_report = Path(folder)/'desktop.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--report', str(child_report)]
        if args.vtk:
            command.append('--vtk')
        if args.require_windows:
            command.append('--require-windows')
        try:
            child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            report = json.loads(child_report.read_text(encoding='utf-8')) if child_report.exists() else None
            if report is None or (child.returncode and report.get('status') == 'passed'):
                raise RuntimeError(f'El proceso gráfico terminó sin un informe válido. Código: {child.returncode}.')
        except (subprocess.TimeoutExpired, RuntimeError, ValueError, OSError) as exc:
            from core.app_version import APP_RELEASE
            report = dict(schema_version=1, app_release=APP_RELEASE, status='failed',
                platform=platform.platform(), windows_native_execution=platform.system() == 'Windows',
                human_visual_review=False, full_app_workflow_tested=False,
                checks=[dict(name='desktop_process', status='failed', error=str(exc))])
    atomic_write_json(args.report, report)
    print(f'{report["status"]}: {args.report}. La revisión visual humana se registra por separado.')
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
