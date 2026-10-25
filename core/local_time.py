"""Instantes IANA sin correcciones ni elecciones DST implícitas.

Una hora de pared sin offset debe existir y representar un único instante.
CSV/API pueden desambiguar con un offset explícito; API admite fold=0/1.
No depende de pandas ni de los motores científicos opcionales.
"""
from datetime import date, datetime, timedelta, timezone as utc_timezone
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIME_POLICY = "strict_local_time_v1"
UTC = utc_timezone.utc


class LocalTimeError(ValueError):
    """Hora local que requiere corrección o una elección explícita."""


def iana_zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(timezone))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Zona horaria IANA inválida o no disponible: {timezone}") from exc


def resolve_local_datetime(dt: datetime, timezone: str, *, fold=None) -> datetime:
    if not isinstance(dt, datetime):
        raise ValueError("El instante debe ser una fecha y hora válidas.")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError("fold debe ser 0 o 1.")
    zone = iana_zone(timezone)

    if dt.tzinfo is not None and dt.utcoffset() is not None:
        if fold is not None:
            raise ValueError("Use un offset explícito o fold, no ambos.")
        # .replace(tzinfo=ZoneInfo(...)) también permite construir horas que
        # nunca existieron. Validar su pared antes de convertirlas.
        if isinstance(dt.tzinfo, ZoneInfo):
            back = dt.astimezone(UTC).astimezone(dt.tzinfo)
            if back.replace(tzinfo=None) != dt.replace(tzinfo=None):
                raise LocalTimeError(f"Hora local inexistente: {dt.isoformat()} ({dt.tzinfo}). Cambie la hora.")
        return dt.astimezone(UTC).astimezone(zone)

    candidates = {}
    for choice in (0, 1):
        local = dt.replace(tzinfo=zone, fold=choice)
        back = local.astimezone(UTC).astimezone(zone)
        if back.replace(tzinfo=None) == dt.replace(tzinfo=None):
            candidates[choice] = back
    if not candidates:
        raise LocalTimeError(f"Hora local inexistente: {dt.isoformat()} ({timezone}). Cambie la hora; no se desplaza automáticamente.")
    instants = {local.astimezone(UTC) for local in candidates.values()}
    if len(instants) > 1 and fold is None:
        offsets = ", ".join(local.isoformat() for local in candidates.values())
        raise LocalTimeError(f"Hora local ambigua: {dt.isoformat()} ({timezone}). Use otro horario o indique un offset explícito en el CSV: {offsets}.")
    return candidates[fold if fold is not None else 0]


def local_instant(fecha: date, hour: float, timezone: str, *, fold=None) -> datetime:
    hour = float(hour)
    if not math.isfinite(hour) or not 0 <= hour <= 24:
        raise ValueError("La hora debe ser finita y estar entre 0 y 24.")
    dt = datetime.combine(fecha, datetime.min.time()) + timedelta(hours=hour)
    return resolve_local_datetime(dt, timezone, fold=fold)


def instant_metadata(local: datetime) -> dict:
    if local.tzinfo is None or local.utcoffset() is None:
        raise ValueError("La procedencia temporal requiere un instante con zona horaria.")
    return dict(instant_local_iso=local.isoformat(), instant_utc_iso=local.astimezone(UTC).isoformat(),
                utc_offset_hours=local.utcoffset().total_seconds() / 3600.0,
                time_fold=local.fold, time_policy=TIME_POLICY)
