"""Prueba de componentes reales Tk/VTK, aislable en un proceso desechable."""
from datetime import datetime, timezone
import platform
import time


def run_desktop_check(*, render_vtk=False, require_windows=False):
    from core.app_version import APP_RELEASE
    checks = []
    result = dict(schema_version=1, app_release=APP_RELEASE,
        timestamp_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
        windows_native_execution=platform.system() == 'Windows',
        human_visual_review=False, full_app_workflow_tested=False,
        field_validation=False, requested_vtk=render_vtk, checks=checks)
    root = None
    callback_errors = []

    def check(name, operation):
        started = time.perf_counter()
        try:
            detail = operation()
            checks.append(dict(name=name, status='passed', detail=detail,
                               seconds=round(time.perf_counter()-started, 3)))
            return True
        except Exception as exc:
            checks.append(dict(name=name, status='failed', error=f'{type(exc).__name__}: {exc}'))
            return False

    try:
        if require_windows and not result['windows_native_execution']:
            raise RuntimeError('Esta ejecución no es Windows nativo.')
        import tkinter as tk
        from tkinter import ttk
        import numpy as np
        root = tk.Tk()
        root.title('Sombra — comprobación temporal de escritorio')
        root.geometry('680x620')
        root.report_callback_exception = lambda kind, error, tb: callback_errors.append(f'{kind.__name__}: {error}')
        checks.append(dict(name='tk_window', status='passed', detail=str(root.tk.call('info', 'patchlevel'))))

        def wait_for_idle(milliseconds=250):
            done = tk.BooleanVar(root, value=False)
            root.after(milliseconds, lambda: done.set(True))
            root.wait_variable(done)
            root.update_idletasks()

        def editor_flow():
            from ui.photo_exclusion_editor import PhotoExclusionEditor
            from types import SimpleNamespace
            applied = []
            area = np.full((8, 8), 180.)
            valid = np.ones((8, 8), dtype=bool)
            editor = PhotoExclusionEditor(root, area, valid, np.zeros_like(valid), applied.append)
            try:
                wait_for_idle()
                width, height = editor.size
                editor.start(SimpleNamespace(x=0, y=0))
                editor.finish(SimpleNamespace(x=width//2, y=height//2))
                if editor.mask.sum() != 16:
                    raise ValueError('La selección gráfica no corresponde a la rejilla.')
                editor.undo()
                if editor.mask.any():
                    raise ValueError('Deshacer no restauró la selección.')
                editor.start(SimpleNamespace(x=0, y=0))
                editor.finish(SimpleNamespace(x=width//2, y=height//2))
                editor.apply()
                if len(applied) != 1 or applied[0].sum() != 16:
                    raise ValueError('Aplicar no entregó la máscara esperada.')
            finally:
                if editor.top.winfo_exists():
                    editor.close()
            return 'Widgets Tk reales: dibujo, selección, deshacer, aplicación y cierre.'

        check('photo_editor', editor_flow)

        frame = ttk.Frame(root)
        frame.pack(fill='both', expand=True)
        wait_for_idle()
        axis = np.linspace(0., 10., 12)
        x, y = np.meshgrid(axis, axis)
        scene = dict(X=x, Y=y, T=300.+x/2, arboles=[], estructuras=[],
                     _render_solar_altitude_deg=45., _render_solar_azimuth_deg=180.)

        def fallback_flow():
            from ui.scene3d_fallback import render_matplotlib_fallback
            from ui.scene3d import _clear_frame
            from core.scene3d_data import scene_data_from_vars
            try:
                render_matplotlib_fallback(frame, scene_data_from_vars(scene, 'Control temporal'), None)
                wait_for_idle()
                if not frame.winfo_children():
                    raise ValueError('El fallback no creó widgets.')
            finally:
                _clear_frame(frame)
            return 'Matplotlib 3D embebido en Tk y liberación del frame.'

        check('matplotlib_tk', fallback_flow)
        if render_vtk:
            def vtk_flow():
                from ui.scene3d import render_scene_3d, _clear_frame
                try:
                    backend = render_scene_3d(scene, frame, title='Control temporal VTK')
                    wait_for_idle(500)
                    controller = getattr(frame, '_sombra_scene3d_controller', None)
                    if backend != 'VTK' or controller is None or controller._photo is None:
                        raise ValueError('VTK no produjo una imagen; fallback no acredita VTK.')
                    controller.view_top()
                    controller.view_isometric()
                    controller._zoom(1.1)
                    controller.update_animation_frame(dict(T_display=301.+x/2, shadow=np.ones_like(x),
                        solar_altitude_deg=40., solar_azimuth_deg=190.))
                    wait_for_idle()
                    if controller._photo is None:
                        raise ValueError('La actualización perdió la imagen VTK.')
                finally:
                    _clear_frame(frame)
                return 'Render VTK real, cámaras, zoom, actualización y liberación.'
            check('vtk_tk', vtk_flow)
        else:
            checks.append(dict(name='vtk_tk', status='not_run', detail='Use --vtk para comprobar el controlador gráfico.'))
    except Exception as exc:
        checks.append(dict(name='desktop_setup', status='failed', error=f'{type(exc).__name__}: {exc}'))
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception as exc:
                callback_errors.append(f'Cierre: {exc}')
    if callback_errors:
        checks.append(dict(name='tk_callbacks', status='failed', errors=callback_errors))
    result['status'] = 'failed' if any(c['status'] == 'failed' for c in checks) else 'passed'
    return result
