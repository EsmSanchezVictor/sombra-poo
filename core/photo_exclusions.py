"""Máscaras manuales: validación, rectángulos y estado JSON compacto sin Tk."""
import base64
import binascii
import math
import numpy as np

MAX_SIDE=640


def exclusion_mask(value, shape):
    array=np.asarray(value)
    if len(shape)!=2 or array.ndim!=2 or tuple(array.shape)!=tuple(shape):
        raise ValueError('Las exclusiones deben tener la misma forma 2D que el área de cálculo.')
    if array.dtype!=np.bool_ and not np.issubdtype(array.dtype,np.number):
        raise ValueError('La máscara de exclusiones debe ser numérica o booleana.')
    if not np.all(np.isfinite(array)):
        raise ValueError('La máscara de exclusiones no puede contener NaN o infinito.')
    return array.astype(bool,copy=True)


def add_rectangle(mask, bounds, display_size):
    result=exclusion_mask(mask,np.asarray(mask).shape)
    height,width=result.shape
    dw,dh=map(float,display_size);x1,y1,x2,y2=map(float,bounds)
    if not all(math.isfinite(v) for v in (dw,dh,x1,y1,x2,y2)) or dw<=0 or dh<=0:
        raise ValueError('Coordenadas de selección inválidas.')
    if x1==x2 or y1==y2:return result
    left=max(0,min(width,math.floor(min(x1,x2)*width/dw)))
    right=max(0,min(width,math.ceil(max(x1,x2)*width/dw)))
    top=max(0,min(height,math.floor(min(y1,y2)*height/dh)))
    bottom=max(0,min(height,math.ceil(max(y1,y2)*height/dh)))
    result[top:bottom,left:right]=True
    return result


def encode_state(mask, signature, *, pending=False):
    array=exclusion_mask(mask,np.asarray(mask).shape)
    if not all(0<side<=MAX_SIDE for side in array.shape):raise ValueError('Resolución de exclusiones fuera de rango.')
    if not isinstance(signature,str) or len(signature)!=64 or any(c not in '0123456789abcdef' for c in signature):
        raise ValueError('Firma de la selección inválida.')
    return dict(version=1,shape=list(array.shape),input_signature=signature,pending=bool(pending),
                bits=base64.b64encode(np.packbits(array.ravel(),bitorder='little').tobytes()).decode('ascii'))


def decode_state(state):
    if not isinstance(state,dict) or type(state.get('version')) is not int or state['version']!=1:
        raise ValueError('Estado de exclusiones no compatible.')
    shape=state.get('shape')
    if not isinstance(shape,list) or len(shape)!=2 or any(type(s) is not int or not 0<s<=MAX_SIDE for s in shape):
        raise ValueError('Resolución de exclusiones inválida.')
    signature=state.get('input_signature');bits=state.get('bits')
    if not isinstance(bits,str) or len(bits)>((MAX_SIDE*MAX_SIDE+7)//8+2)//3*4:
        raise ValueError('Datos de exclusiones inválidos o demasiado grandes.')
    try:data=base64.b64decode(bits,validate=True)
    except (ValueError,binascii.Error):raise ValueError('Datos de exclusiones dañados.') from None
    count=shape[0]*shape[1]
    if len(data)!=(count+7)//8:raise ValueError('Tamaño de exclusiones inconsistente.')
    array=np.unpackbits(np.frombuffer(data,dtype=np.uint8),bitorder='little')[:count].reshape(shape).astype(bool)
    # Revalidate signature and exact schema through the writer, without coercing dimensions.
    encode_state(array,signature,pending=state.get('pending',False))
    if type(state.get('pending',False)) is not bool:raise ValueError('Indicador de recálculo inválido.')
    return array,signature,state.get('pending',False)


def state_from_analysis(analysis, *, pending=False):
    if not isinstance(analysis,dict):return None
    mask=analysis.get('exclusion_mask')
    if mask is None and not pending:return None
    if mask is None:mask=np.zeros(np.asarray(analysis['shadow_mask']).shape,dtype=bool)
    return encode_state(mask,analysis.get('input_signature'),pending=pending)
