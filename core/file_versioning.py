"""Helpers para versionado seguro de archivos."""

from __future__ import annotations

from pathlib import Path


def safe_path(dest_dir: str | Path, filename: str) -> Path:
    """Devuelve una ruta libre sin sobreescribir archivos existentes."""
    base_dir = Path(dest_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    candidate = base_dir / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    version = 2
    while True:
        versioned = base_dir / f"{stem}_v{version}{suffix}"
        if not versioned.exists():
            return versioned
        version += 1