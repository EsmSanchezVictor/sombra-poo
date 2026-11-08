"""Entrada del ejecutable, con diagnóstico y comprobación gráfica aislada."""
from pathlib import Path
import argparse
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description='Proyecto Sombra')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--self-check', action='store_true')
    action.add_argument('--desktop-check', action='store_true')
    action.add_argument('--desktop-worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--report')
    args = parser.parse_args()
    checking = args.self_check or args.desktop_check or args.desktop_worker
    if checking and not args.report:
        parser.error('Indique --report con la ruta del JSON de salida.')
    # Preserve the caller's report destination before selecting a writable CWD.
    report_path = Path(args.report).resolve() if args.report else None
    from core.runtime_paths import writable_root
    user_root = writable_root()
    user_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('NUMBA_CACHE_DIR', str(user_root/'cache'/'numba'))
    logs = user_root/'logs'
    logs.mkdir(parents=True, exist_ok=True)
    for stream in ('stdout', 'stderr'):
        if getattr(sys, stream) is None:
            setattr(sys, stream, open(logs/'ejecutable.log', 'a', encoding='utf-8', buffering=1))
    if getattr(sys, 'frozen', False):
        os.chdir(user_root)
    from core.safe_io import atomic_write_json
    if args.self_check:
        from services.installation_check import run_installation_check
        report = run_installation_check(require_full=True)
        atomic_write_json(report_path, report)
        return 0 if report['status'] == 'passed' else 1
    if args.desktop_worker:
        from services.desktop_check import run_desktop_check
        report = run_desktop_check(render_vtk=True, require_windows=True)
        atomic_write_json(report_path, report)
        return 0 if report['status'] == 'passed' else 1
    if args.desktop_check:
        with tempfile.TemporaryDirectory(prefix='sombra-exe-check-') as folder:
            child_report = Path(folder)/'desktop.json'
            command = [sys.executable]
            if not getattr(sys, 'frozen', False):
                command.append(str(Path(__file__).resolve()))
            command += ['--desktop-worker', '--report', str(child_report)]
            try:
                child = subprocess.run(command, timeout=90)
                report = json.loads(child_report.read_text(encoding='utf-8'))
                if child.returncode and report.get('status') == 'passed':
                    raise RuntimeError(f'Proceso gráfico fallido: {child.returncode}')
            except (subprocess.TimeoutExpired, OSError, ValueError, RuntimeError) as exc:
                report = dict(status='failed', checks=[dict(name='desktop_process', status='failed', error=str(exc))],
                              human_visual_review=False, field_validation=False)
        atomic_write_json(report_path, report)
        return 0 if report['status'] == 'passed' else 1
    from main import main as start_app
    start_app()
    return 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    try:
        raise SystemExit(main())
    except Exception as exc:
        from core.app_logging import configure_logging
        configure_logging().exception('Fallo al iniciar el ejecutable')
        try:
            from tkinter import messagebox
            messagebox.showerror('Proyecto Sombra', f'No se pudo completar la operación:\n{exc}\n\nRevise los registros en APPDATA\\ProyectoSombra\\logs.')
        except Exception:
            pass
        raise SystemExit(1)
