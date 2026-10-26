"""Evaluación de máscaras frente a anotaciones externas; no genera ground truth."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from core.safe_paths import contained_path
from services.shadow_detector import ShadowDetector, ShadowParams


def mask_metrics(predicted, reference, roi=None):
    pred = ShadowDetector._binary_mask(predicted, 'predicted')
    truth = ShadowDetector._binary_mask(reference, 'reference', pred.shape)
    valid = np.ones_like(pred) if roi is None else ShadowDetector._binary_mask(roi, 'roi', pred.shape)
    n = int(valid.sum())
    if not n:
        raise ValueError('La evaluación no tiene píxeles válidos.')
    tp = int(np.count_nonzero(pred & truth & valid))
    fp = int(np.count_nonzero(pred & ~truth & valid))
    fn = int(np.count_nonzero(~pred & truth & valid))
    tn = n - tp - fp - fn
    def ratio(a,b):return a/b if b else None
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, pixels=n,
                precision=ratio(tp,tp+fp), recall=ratio(tp,tp+fn),
                f1=ratio(2*tp,2*tp+fp+fn), iou=ratio(tp,tp+fp+fn),
                predicted_coverage_fraction=(tp+fp)/n, reference_coverage_fraction=(tp+fn)/n,
                coverage_error_pp=100*(fp-fn)/n)


def summarize_cases(cases):
    """Agrupa por origen y algoritmo; nunca mezcla controles con fotos declaradas."""
    groups = {}
    for case in cases:
        # El umbral estimado en cada foto es un resultado, no otro algoritmo.
        algorithm = {k: v for k, v in case['algorithm'].items() if k != 'threshold_ratio'}
        key = (case['origin'], json.dumps(algorithm, sort_keys=True))
        group = groups.setdefault(key, dict(origin=case['origin'], algorithm=algorithm,
            cases=0, tp=0, fp=0, fn=0, tn=0, pixels=0, materials={}))
        group['cases'] += 1
        for field in ('tp', 'fp', 'fn', 'tn', 'pixels'):
            group[field] += case['metrics'][field]
        for label, counts in case['confounders'].items():
            material = group['materials'].setdefault(label, dict(negative_pixels=0, false_positives=0))
            for field in ('negative_pixels', 'false_positives'):
                material[field] += counts[field]
    for group in groups.values():
        tp, fp, fn, n = (group[k] for k in ('tp', 'fp', 'fn', 'pixels'))
        group['precision'] = tp/(tp+fp) if tp+fp else None
        group['recall'] = tp/(tp+fn) if tp+fn else None
        group['f1'] = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        group['iou'] = tp/(tp+fp+fn) if tp+fp+fn else None
        group['coverage_error_pp'] = 100*(fp-fn)/n
        for counts in group['materials'].values():
            n_negative = counts['negative_pixels']
            counts['false_positive_fraction'] = counts['false_positives']/n_negative if n_negative else None
    return list(groups.values())


def evaluate_manifest(manifest_path, *, require_real=False):
    path=Path(manifest_path).resolve()
    spec=json.loads(path.read_text(encoding='utf-8'))
    if spec.get('schema_version') != 1 or not isinstance(spec.get('cases'),list) or not spec['cases']:
        raise ValueError('Se requiere un manifiesto schema_version=1 con casos anotados.')
    results=[];identifiers=set()
    for case in spec['cases']:
        identifier=case['id']
        if not isinstance(identifier,str) or not identifier.strip() or identifier in identifiers:
            raise ValueError('Los identificadores deben ser únicos y no vacíos.')
        identifiers.add(identifier)
        provenance={}
        def read(relative, *, mask=False):
            source=Path(contained_path(path.parent,relative,allow_absolute=False))
            data=source.read_bytes();provenance[relative]=hashlib.sha256(data).hexdigest()
            with Image.open(source) as im:
                return np.asarray(im.convert('L') if mask else im.convert('RGB')).copy()
        image=read(case['image']);truth=read(case['reference_mask'],mask=True)>0
        shape=image.shape[:2]
        roi=np.ones(shape,dtype=bool) if not case.get('roi_mask') else read(case['roi_mask'],mask=True)>0
        exclusion=np.zeros(shape,dtype=bool) if not case.get('exclusion_mask') else read(case['exclusion_mask'],mask=True)>0
        roi=ShadowDetector._binary_mask(roi,'roi',shape)
        exclusion=ShadowDetector._binary_mask(exclusion,'exclusion',shape)
        valid=roi & ~exclusion
        profile=case.get('profile','detector')
        if profile=='detector':
            params=ShadowParams(**case.get('params',{}))
            predicted=ShadowDetector().detect_shadow_candidates(image,method=case.get('method','adaptive'),params=params)
            algorithm={'profile':profile,'method':case.get('method','adaptive'),'params':vars(params)}
        elif profile=='photo_reference':
            from image_processor import ImageProcessor
            import cv2
            reference_roi=read(case['lit_reference_mask'],mask=True)>0
            reference_roi=ShadowDetector._binary_mask(reference_roi,'lit_reference_mask',shape)
            gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
            result=ImageProcessor().analizar_sombra_fotografica(gray,gray,roi,reference_roi,exclusion_mask=exclusion)
            predicted=np.nan_to_num(result['shadow_mask'])>0
            algorithm={'profile':profile,'method':result['algorithm'],'threshold_ratio':result['threshold_ratio']}
        else:
            raise ValueError('Perfil de evaluación desconocido.')
        metrics=mask_metrics(predicted,truth,valid)
        confounders={}
        for label,filename in case.get('confounder_masks',{}).items():
            candidate=read(filename,mask=True)>0
            candidate=ShadowDetector._binary_mask(candidate,label,shape)
            negatives=candidate & valid & ~truth
            n=int(negatives.sum());fp=int(np.count_nonzero(predicted & negatives))
            confounders[label]={'negative_pixels':n,'false_positives':fp,'false_positive_fraction':fp/n if n else None}
        annotation = case.get('annotation', {})
        if not isinstance(annotation, dict):
            raise ValueError('annotation debe ser un objeto con author y method.')
        if require_real and case.get('origin') == 'real_photo':
            if not all(isinstance(annotation.get(k), str) and annotation[k].strip() for k in ('author', 'method')):
                raise ValueError('Las fotos reales requieren annotation.author y annotation.method.')
        results.append(dict(id=identifier,origin=case.get('origin','unspecified'),algorithm=algorithm,
            annotation=annotation,metrics=metrics,confounders=confounders,files_sha256=provenance,
            domain=dict(image_pixels=int(np.prod(shape)),roi_pixels=int(roi.sum()),
                        excluded_roi_pixels=int((roi & exclusion).sum()),evaluated_pixels=int(valid.sum()))))
    real_cases = [r for r in results if r['origin'] == 'real_photo']
    if require_real and not real_cases:
        raise ValueError('No hay fotografías reales anotadas; los controles sintéticos no cierran F4.')
    real_images = {spec['cases'][i]['image'] for i, r in enumerate(results) if r['origin'] == 'real_photo'}
    real_hashes = {r['files_sha256'][spec['cases'][i]['image']] for i, r in enumerate(results) if r['origin'] == 'real_photo'}
    return dict(schema_version=1,manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cases=results,
        real_photo_cases=len(real_cases),real_photo_files=len(real_images),unique_real_photo_sha256=len(real_hashes),
        summaries=summarize_cases(results),real_photos_required=require_real,
        ground_truth_authenticity_verified=False,
        warning='Las etiquetas provienen del manifiesto. Los casos sintéticos e iconos no validan precisión en fotografías reales.')
