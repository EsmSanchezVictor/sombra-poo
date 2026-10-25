"""Rutas portables confinadas al proyecto, también para archivos de Windows."""
import ntpath
import os
import re
import unicodedata

RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789¹²³"}
ARTIFACT_KEYS = frozenset(("image", "curve", "matrix", "reference", "calc_data", "reference_data",
    "tmrt_data", "photo_analysis_data", "histogram", "shadow_classification", "temperature_summary",
    "edit_excel", "model_excel", "temp_graph_image"))


def safe_component(value):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 150:
        raise ValueError("Nombre vacío o no válido.")
    if value in (".", "..") or ".." in value or value.endswith((".", " ")):
        raise ValueError("El nombre contiene una secuencia no permitida.")
    if any(ord(c) < 32 or c in '<>:"/\\|?*' for c in value):
        raise ValueError("El nombre contiene caracteres de ruta no permitidos.")
    if value.split(".", 1)[0].upper() in RESERVED:
        raise ValueError("El nombre está reservado por Windows.")
    return value


def validate_analysis_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Identificador de análisis no válido.")
    return safe_component(value)


def relative_path(value):
    if not isinstance(value, str) or not value or ntpath.splitdrive(value)[0] or value.startswith(("/", "\\")):
        raise ValueError("Se requiere una ruta relativa al proyecto.")
    parts = value.replace("\\", "/").split("/")
    for part in parts:
        safe_component(part)
    return "/".join(parts)


def contained_path(root, value, *, allow_absolute=True):
    root = os.path.realpath(os.path.abspath(root))
    value = os.fspath(value)
    if allow_absolute and os.path.isabs(value):
        candidate = os.path.realpath(value)
    else:
        candidate = os.path.realpath(os.path.join(root, relative_path(value)))
    if os.path.commonpath((root, candidate)) != root:
        raise ValueError("La ruta sale del proyecto.")
    return candidate


def safe_project_reference(root, value, *, strict=False):
    if not value:
        return None
    try:
        return contained_path(root, value, allow_absolute=not strict)
    except (ValueError, TypeError, OSError):
        if strict:
            raise ValueError("El proyecto contiene una referencia externa o no válida.") from None
        return None


def sanitize_entry(root, entry, *, strict=False):
    result = dict(entry)
    if result.get("analysis_id"):
        validate_analysis_id(result["analysis_id"])
    for key in ARTIFACT_KEYS:
        if result.get(key):
            path = safe_project_reference(root, result[key], strict=strict)
            result[key] = os.path.relpath(path, root).replace("\\", "/") if path else None
    return result


def sanitize_payload(root, payload, *, strict=False):
    if not isinstance(payload, dict):
        raise ValueError("El estado del proyecto debe ser un objeto JSON.")
    result = dict(payload)
    paths = result.get("paths") or {}
    if not isinstance(paths, dict):
        raise ValueError("Las rutas del proyecto no son válidas.")
    result["paths"] = {}
    for key, value in paths.items():
        path = safe_project_reference(root, value, strict=strict)
        result["paths"][key] = os.path.relpath(path, root).replace("\\", "/") if path else None
    result["snapshots"] = [sanitize_entry(root, item, strict=strict) for item in (result.get("snapshots") or [])]
    if result.get("last_results_meta"):
        result["last_results_meta"] = sanitize_entry(root, result["last_results_meta"], strict=strict)
    return result


def collision_key(value):
    return unicodedata.normalize("NFC", value).casefold()
