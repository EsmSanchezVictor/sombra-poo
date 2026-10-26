"""Migración explícita y compatible de estados de proyecto."""
from copy import deepcopy

STATE_SCHEMA_VERSION = 3
ANALYSIS_SCHEMA_VERSION = 1

class UnsupportedSchemaError(ValueError):
    pass


def validate_analysis_schema(connection):
    """Inspección de sólo lectura, antes de configurar/migrar/copiar SQLite."""
    header = connection.execute('PRAGMA user_version').fetchone()[0]
    table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone()
    marker = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone() if table else None
    try:
        version = int(marker[0]) if marker else header
    except (ValueError, TypeError):
        raise UnsupportedSchemaError('Versión de la base de análisis inválida') from None
    if not 0 <= header <= ANALYSIS_SCHEMA_VERSION or not 0 <= version <= ANALYSIS_SCHEMA_VERSION:
        raise UnsupportedSchemaError('La base de análisis usa un esquema más reciente o inválido; no se modificó')


def migrate_payload(payload):
    if not isinstance(payload, dict) or type(payload.get('version')) is not int or payload['version'] != 1:
        raise UnsupportedSchemaError('Versión de proyecto no soportada')
    schema = payload.get('state_schema_version', 1)
    if type(schema) is not int or not 1 <= schema <= STATE_SCHEMA_VERSION:
        raise UnsupportedSchemaError('El proyecto usa un esquema más reciente o inválido; no se modificó')
    if type(payload.get('layout_version', 2)) is not int or not 1 <= payload.get('layout_version', 2) <= 2:
        raise UnsupportedSchemaError('Estructura de proyecto no soportada')
    for key in ('meta', 'vars', 'vars_modelo', 'scene', 'ui', 'paths'):
        if key in payload and not isinstance(payload[key], dict):
            raise ValueError(f'{key} debe ser un objeto JSON')
    if not isinstance(payload.get('snapshots', []), list) or any(not isinstance(x, dict) for x in payload.get('snapshots', [])):
        raise ValueError('Los análisis del proyecto no son válidos')
    if not isinstance(payload.get('integrity_events', []), list):
        raise ValueError('Historial de integridad inválido')
    number = payload.get('next_n', 1)
    if type(number) is not int or number < 1:
        raise ValueError('Numeración de análisis inválida')
    result = deepcopy(payload)
    if schema == 1:
        result['state_schema_version'] = 2
        history = result.setdefault('schema_migrations', [])
        if not isinstance(history, list):
            raise ValueError('Historial de migración inválido')
        history.append({'from': 1, 'to': 2, 'operation': 'add_recovery_and_integrity_metadata'})
    return result
