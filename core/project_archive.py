"""Preflight y extracción acotada de paquetes .3es sin extractall."""
from dataclasses import dataclass
import os
import stat
from core.safe_paths import relative_path, contained_path, collision_key


@dataclass(frozen=True)
class ArchiveLimits:
    max_members: int = 10000
    max_member_bytes: int = 256 * 1024 * 1024
    max_total_bytes: int = 1024 * 1024 * 1024
    max_ratio: float = 200.0


def validate_archive(archive, limits=ArchiveLimits()):
    infos = archive.infolist()
    if len(infos) > limits.max_members:
        raise ValueError("El paquete contiene demasiados archivos.")
    seen = {}
    total = 0
    for info in infos:
        name = relative_path(info.filename[:-1] if info.is_dir() else info.filename)
        key = collision_key(name)
        if key in seen:
            raise ValueError("El paquete contiene rutas duplicadas o ambiguas.")
        seen[key] = info.is_dir()
        mode = (info.external_attr >> 16) & 0xffff
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or info.flag_bits & 1:
            raise ValueError("No se admiten enlaces, archivos especiales ni entradas cifradas.")
        if info.file_size > limits.max_member_bytes:
            raise ValueError("Un archivo supera el tamaño máximo permitido.")
        total += info.file_size
        if total > limits.max_total_bytes:
            raise ValueError("El paquete supera el tamaño total permitido.")
        if info.file_size / max(1, info.compress_size) > limits.max_ratio:
            raise ValueError("El paquete supera la relación de compresión permitida.")
    for key in seen:
        parts = key.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            if parent in seen and not seen[parent]:
                raise ValueError("Una ruta del paquete es archivo y directorio a la vez.")
    return infos


def extract_validated_archive(archive, destination, limits=ArchiveLimits()):
    infos = validate_archive(archive, limits)
    total = 0
    for info in infos:
        name = relative_path(info.filename[:-1] if info.is_dir() else info.filename)
        target = contained_path(destination, name, allow_absolute=False)
        if info.is_dir():
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        count = 0
        with archive.open(info) as source, open(target, "xb") as output:
            while True:
                data = source.read(1024 * 1024)
                if not data:
                    break
                count += len(data)
                total += len(data)
                if count > limits.max_member_bytes or total > limits.max_total_bytes or count > info.file_size:
                    raise ValueError("El contenido descomprimido excede los límites.")
                output.write(data)
        if count != info.file_size:
            raise ValueError("Tamaño descomprimido incorrecto.")
