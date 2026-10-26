"""Numerical invariants and hostile-input checks for opt-in manual exclusions."""
import copy
import json
import numpy as np
import pytest
from core.photo_exclusions import add_rectangle,encode_state,decode_state
from image_processor import ImageProcessor
from services.photo_selection import analyze_selection,selection_signature,restore_analysis_mask


def areas():return np.tile([40,40,200,200],(4,1)).astype(np.uint8),np.full((2,2),200,dtype=np.uint8)


def test_default_and_empty_exclusions_preserve_all_scalar_and_spatial_results():
    area,reference=areas();p=ImageProcessor()
    a=p.analizar_sombra_fotografica(area,reference)
    b=p.analizar_sombra_fotografica(area,reference,exclusion_mask=np.zeros(area.shape))
    for key in ('coverage_pct','attenuation_pct','effective_transmittance','threshold_ratio','legacy_shadow_index_pct'):
        assert a[key]==b[key]
    for key in ('shadow_mask','local_transmittance_map','local_attenuation_map','ratio_map'):
        assert np.array_equal(a[key],b[key],equal_nan=True)
    assert a['algorithm']==b['algorithm']=='photo-shadow-v2-coverage-attenuation'


def test_exclusion_changes_both_coverage_denominator_and_thermal_domain_without_mutating_inputs():
    area,reference=areas();original=area.copy();mask=np.zeros(area.shape,dtype=bool);mask[:,0]=True
    result=ImageProcessor().analizar_sombra_fotografica(area,reference,exclusion_mask=mask)
    assert result['coverage_pct']==pytest.approx(100/3)
    assert result['excluded_pixels']==4 and result['valid_pixels']==12 and result['shadow_pixels']==4
    assert np.isnan(result['local_transmittance_map'][:,0]).all()
    assert np.isnan(result['shadow_mask'][:,0]).all()
    assert result['algorithm'].endswith('manual-exclusions-v1')
    assert np.array_equal(original,area) and reference.min()==200


def test_exclusions_outside_roi_are_not_counted_and_cannot_restore_invalid_pixels():
    area,reference=areas();roi=np.ones(area.shape,dtype=bool);roi[0,:]=False
    excluded=np.zeros(area.shape,dtype=bool);excluded[0,:]=True
    result=ImageProcessor().analizar_sombra_fotografica(area,reference,roi,exclusion_mask=excluded)
    assert result['excluded_pixels']==0 and result['valid_pixels']==12


@pytest.mark.parametrize('mask',[np.ones((4,4)),np.ones((1,4)),np.full((4,4),np.nan)])
def test_all_excluded_or_malformed_domains_fail_explicitly(mask):
    area,reference=areas()
    with pytest.raises(ValueError):ImageProcessor().analizar_sombra_fotografica(area,reference,exclusion_mask=mask)


def test_masks_bind_to_area_reference_and_roi_not_to_a_filename():
    area,reference=areas();p=ImageProcessor();mask=np.zeros(area.shape,dtype=bool);mask[:,0]=True
    first=analyze_selection(p,area,reference,exclusions=mask,reuse_previous=False)
    again=analyze_selection(p,area.copy(),reference.copy(),previous=first)
    assert again['excluded_pixels']==4
    changed=area.copy();changed[0,0]+=1
    assert analyze_selection(p,changed,reference,previous=first)['excluded_pixels']==0
    assert analyze_selection(p,area,reference+1,previous=first)['excluded_pixels']==0
    roi=np.ones(area.shape,dtype=bool);roi[0,0]=False
    assert analyze_selection(p,area,reference,roi,previous=first)['excluded_pixels']==0


def test_packed_state_roundtrips_and_fits_maximum_grid_without_python_objects():
    mask=np.zeros((640,640),dtype=bool);mask[13:93,18:140]=True
    state=encode_state(mask,'a'*64,pending=True)
    assert len(json.dumps(state))<70000
    restored,signature,pending=decode_state(json.loads(json.dumps(state)))
    assert np.array_equal(mask,restored) and signature=='a'*64 and pending


@pytest.mark.parametrize('change',[{'version':2},{'shape':[641,1]},{'shape':[True,4]},
 {'bits':'not-base64!'},{'bits':''},{'input_signature':'x'},{'pending':'false'}])
def test_untrusted_project_states_are_validated_before_allocation(change):
    state=encode_state(np.zeros((4,4)),'b'*64);state.update(change)
    with pytest.raises(ValueError):decode_state(state)


def test_rectangle_coordinate_mapping_handles_direction_edges_and_zero_area():
    mask=np.zeros((4,8),dtype=bool)
    result=add_rectangle(mask,(40,40,0,0),(80,40))
    assert result[:,:4].all() and not result[:,4:].any() and not mask.any()
    assert not add_rectangle(mask,(2,2,2,20),(80,40)).any()
    assert add_rectangle(mask,(-20,-30,100,90),(80,40)).all()
    with pytest.raises(ValueError):add_rectangle(mask,(0,0,np.nan,4),(80,40))


def test_saved_exclusions_are_never_silently_dropped_when_a_bundle_is_missing_or_mismatched():
    area,reference=areas();signature=selection_signature(area,reference)
    with pytest.raises(ValueError,match='Falta'):restore_analysis_mask({},dict(photo_excluded_pixels=4),area,reference)
    mask=np.zeros(area.shape,dtype=bool);mask[:,0]=True
    with pytest.raises(ValueError):restore_analysis_mask({'exclusion_mask':mask},dict(photo_input_signature='c'*64,photo_excluded_pixels=4),area,reference)
    loaded=restore_analysis_mask({'exclusion_mask':mask},dict(photo_input_signature=signature,photo_excluded_pixels=4),area,reference)
    assert loaded['input_signature']==signature and loaded['excluded_pixels']==4


@pytest.mark.parametrize('mode',['standard','advanced'])
def test_excluded_pixels_remain_absent_in_both_thermal_models(mode):
    from shadow_temp import Temperatura
    area,reference=areas();mask=np.zeros(area.shape,dtype=bool);mask[:,0]=True
    result=ImageProcessor().analizar_sombra_fotografica(area,reference,exclusion_mask=mask)
    calc=Temperatura();calc.model_mode=mode
    thermal=calc.calculate_tmrt_map(30,result['shadow_mask']*100,
        radiation_override=700,solar_altitude_override=45,dni_override=600,dhi_override=150,
        transmittance_map_override=result['local_transmittance_map'])
    assert np.isnan(thermal['Tmrt_map'][:,0]).all()
    assert np.isfinite(thermal['Tmrt_map'][:,1:]).all()
