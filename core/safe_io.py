"""Escrituras JSON indivisibles: el estado anterior sobrevive a fallos."""
import json
import os
import tempfile


def atomic_write_json(path, payload, *, indent=2, ensure_ascii=False, sort_keys=False):
    path = os.path.abspath(os.fspath(path))
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".sombra-json-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=indent, ensure_ascii=ensure_ascii, sort_keys=sort_keys)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(folder)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


from contextlib import contextmanager
import errno


def fsync_directory(folder):
    """Persistencia de renombres donde el SO permite sincronizar directorios."""
    if os.name == 'nt':
        return
    fd = os.open(folder, os.O_RDONLY)
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(fd)


@contextmanager
def atomic_output(path):
    """Publica Excel, NPZ o ZIP sólo cuando el escritor terminó correctamente."""
    path = os.path.abspath(os.fspath(path))
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    suffix = os.path.splitext(path)[1] or '.tmp'
    fd, temporary = tempfile.mkstemp(prefix='.sombra-write-', suffix=suffix, dir=folder)
    os.close(fd)
    try:
        yield temporary
        fsync_file(temporary)
        os.replace(temporary, path)
        fsync_directory(folder)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fsync_file(path):
    """Sincroniza sin truncar; Windows requiere un descriptor escribible."""
    with open(path, 'r+b') as stream:
        stream.flush()
        os.fsync(stream.fileno())
