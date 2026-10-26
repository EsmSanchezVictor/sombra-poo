"""Informe de campaña sin modificar calibraciones ni preferencias de la app."""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import hashlib
import math
from core.validation import leer_csv_mediciones, evaluar_modelos
from core.model_registry import methodology_manifest, TMRT_MODELS


def evaluate_campaign(csv_path, *, strict_campaigns=True, k_actual=0.04):
    source=Path(csv_path)
    rows=leer_csv_mediciones(str(source))
    identifiers=[r.get('id') for r in rows]
    if any(not i for i in identifiers) or len(set(identifiers))!=len(identifiers):
        raise ValueError('Cada medición debe tener un id único y no vacío.')
    # Do not silently discard rows rejected by the existing CSV normalizer.
    import pandas as pd
    try:raw=pd.read_csv(source,sep=None,engine='python',encoding='utf-8-sig')
    except UnicodeDecodeError:raw=pd.read_csv(source,sep=None,engine='python',encoding='latin-1')
    if len(raw)!=len(rows):
        raise ValueError(f'Hay {len(raw)-len(rows)} filas no utilizables; corrija el CSV antes de reportar una campaña.')
    if strict_campaigns:
        if any(r.get('conjunto') not in ('calibracion','validacion') or not r.get('campaign') for r in rows):
            raise ValueError('Indique campania y conjunto (calibracion/validacion) en todas las filas.')
        groups={k:[r for r in rows if r['conjunto']==k] for k in ('calibracion','validacion')}
        if any(len(g)<2 for g in groups.values()):raise ValueError('Se necesitan al menos dos mediciones por conjunto.')
        camps={k:{r['campaign'].strip().casefold() for r in v} for k,v in groups.items()}
        if camps['calibracion'] & camps['validacion']:
            raise ValueError('Una misma campaña no puede usarse para calibración y validación.')
    result=evaluar_modelos(rows,k_actual=k_actual)
    return dict(schema_version=1,methodology=methodology_manifest(),
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),normalized_rows=len(rows),
        campaign_policy='disjoint_campaign_labels' if strict_campaigns else 'internal_diagnostic',
        measurement_authenticity_verified=False,calibration_applied=False,
        source_counts=dict(Counter(r['fuente_tmrt'] for r in rows)),
        metrics_by_model={(TMRT_MODELS['advanced']['label'] if k=='Avanzado v1' else k):v for k,v in result['metricas_modelos'].items()},metrics_local_air=result['metricas_aire_local'],
        warnings=result['advertencias'],split=asdict(result['split']),
        suggested_k=result['k_calibrado'],current_k=result['k_actual'])


def json_report(value):
    """JSON estricto: fechas ISO y ausencias explícitas, nunca NaN/Infinity."""
    if isinstance(value,dict):return {str(k):json_report(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_report(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    if callable(getattr(value,'isoformat',None)):return value.isoformat()
    return value
