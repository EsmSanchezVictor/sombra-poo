"""Análisis fotométrico ligado a una selección concreta y sus exclusiones."""
import hashlib
import json
import numpy as np
from core.photo_exclusions import exclusion_mask


def selection_signature(area,reference,area_mask=None,reference_mask=None):
    digest=hashlib.sha256()
    for value,mask in ((area,area_mask),(reference,reference_mask)):
        array=np.asarray(value,dtype='<f4')
        if array.ndim!=2 or not array.size:raise ValueError('Se necesitan dos áreas fotográficas 2D.')
        valid=np.isfinite(array)
        if mask is not None:valid &= exclusion_mask(mask,array.shape)
        canonical=np.where(valid,array,0).astype('<f4',copy=False)
        digest.update(json.dumps(array.shape).encode());digest.update(canonical.tobytes())
        digest.update(np.packbits(valid,bitorder='little').tobytes())
    return digest.hexdigest()


def analyze_selection(processor,area,reference,area_mask=None,reference_mask=None,*,previous=None,exclusions=None,reuse_previous=True):
    signature=selection_signature(area,reference,area_mask,reference_mask)
    if exclusions is None and reuse_previous and previous and previous.get('input_signature')==signature:
        exclusions=previous.get('exclusion_mask')
    result=processor.analizar_sombra_fotografica(area,reference,mascara_area=area_mask,
        mascara_referencia=reference_mask,exclusion_mask=exclusions)
    result['input_signature']=signature
    return result


def restore_analysis_mask(analysis,entry,area,reference,area_mask=None,reference_mask=None):
    mask=analysis.get('exclusion_mask')
    if mask is None:
        if entry.get('photo_excluded_pixels',0):raise ValueError('Falta la máscara de exclusiones guardada; no se recalculará sin ella.')
        return analysis
    signature=selection_signature(area,reference,area_mask,reference_mask)
    saved=entry.get('photo_input_signature')
    if saved!=signature:raise ValueError('Las exclusiones guardadas no corresponden a las áreas restauradas.')
    mask=exclusion_mask(mask,np.asarray(area).shape)
    count=int(mask.sum())
    if type(entry.get('photo_excluded_pixels')) is not int or entry['photo_excluded_pixels']!=count:
        raise ValueError('El número de píxeles excluidos no coincide con la máscara guardada.')
    valid=np.isfinite(np.asarray(area))
    if area_mask is not None:valid &= exclusion_mask(area_mask,mask.shape)
    if np.any(mask & ~valid):raise ValueError('Las exclusiones guardadas salen de la ROI original.')
    analysis['exclusion_mask']=mask
    analysis['input_signature']=signature
    analysis['excluded_pixels']=entry.get('photo_excluded_pixels',int(mask.sum()))
    return analysis
