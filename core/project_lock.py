"""Bloqueo de proyecto reentrante; el SO libera el bloqueo tras un cierre abrupto."""
from contextlib import contextmanager
import os
import threading
from core.safe_paths import contained_path

_registry = {}
_registry_guard = threading.Lock()

class ProjectBusyError(OSError):
    pass

@contextmanager
def project_lock(root):
    root = os.path.realpath(os.path.abspath(root))
    with _registry_guard:
        state = _registry.setdefault(root, {'lock': threading.RLock(), 'depth': 0})
    if not state['lock'].acquire(blocking=False):
        raise ProjectBusyError('El proyecto está siendo guardado por otra operación')
    handle = None
    try:
        if state['depth'] == 0:
            filename = contained_path(root, 'config/save.lock', allow_absolute=False)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            handle = open(filename, 'a+b')
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close(); handle = None
                raise ProjectBusyError('El proyecto está abierto para escritura en otro proceso') from None
        state['depth'] += 1
        try:
            yield
        finally:
            state['depth'] -= 1
    finally:
        if handle is not None:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        state['lock'].release()
