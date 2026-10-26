from pathlib import Path
import json
import numpy as np
import pytest
from PIL import Image
from services.shadow_detector import ShadowDetector,ShadowParams
from services.shadow_evaluation import mask_metrics,evaluate_manifest
from image_processor import ImageProcessor

FIXTURES=Path(__file__).parent/'fixtures/shadow_semantics'


def test_coverage_fraction_and_legacy_alias_have_identical_units():
    d=ShadowDetector();mask=np.array([[1,0],[1,0]])
    assert d.compute_shadow_coverage(mask)['coverage_fraction']==.5
    assert d.compute_shadow_quality(mask)['shadow_quality']==.5


def test_explicit_exclusions_remove_material_from_both_numerator_and_denominator():
    d=ShadowDetector();mask=np.array([[1,1],[0,0]]);excluded=np.array([[1,0],[0,0]])
    r=d.compute_shadow_coverage(mask,exclusion_mask=excluded)
    assert r['coverage_fraction']==pytest.approx(1/3)
    assert r['total_pixels']==3 and r['candidate_pixels']==1 and r['excluded_pixels']==1


def test_empty_roi_is_unknown_not_a_false_zero_percent():
    r=ShadowDetector().compute_shadow_coverage(np.ones((3,3)),np.zeros((3,3)))
    assert r['coverage_fraction'] is None and r['status']=='no_valid_pixels'


@pytest.mark.parametrize('mask,roi',[(np.ones((2,2)),np.ones((1,2))),(np.ones((2,2,3)),None),
                                   (np.array([[np.nan]]),None),(np.ones((2,2)),np.full((2,2),np.inf))])
def test_mismatched_or_nonfinite_masks_fail_instead_of_broadcasting(mask,roi):
    with pytest.raises(ValueError):ShadowDetector().compute_shadow_coverage(mask,roi)


def test_identical_dark_pixels_cannot_distinguish_shadow_from_material_labels():
    with Image.open(FIXTURES/'ambiguity.png') as im:image=np.asarray(im)
    predicted=ShadowDetector().detect_shadow_candidates(image,method='global',params=ShadowParams(threshold=110))
    # All four dark regions have exactly the same RGB values by construction.
    assert all(predicted[16,x] for x in (16,48,80,112))
    with Image.open(FIXTURES/'shadow.png') as im:truth=np.asarray(im)>0
    metrics=mask_metrics(predicted,truth)
    assert metrics['precision']==.25 and metrics['recall']==1
    assert metrics['coverage_error_pp']>0


def test_metrics_count_false_positives_and_do_not_hide_zero_denominators():
    r=mask_metrics([[1,0],[1,0]],[[1,1],[0,0]])
    assert (r['tp'],r['fp'],r['fn'],r['tn'])==(1,1,1,1)
    assert r['iou']==pytest.approx(1/3) and r['f1']==.5
    assert mask_metrics([[0]],[[0]])['iou'] is None
    with pytest.raises(ValueError):mask_metrics([[0]],[[0]],[[0]])


def test_manifest_reports_confounders_and_declares_synthetic_limits():
    result=evaluate_manifest(FIXTURES/'manifest.json')
    assert result['real_photo_cases']==0 and result['ground_truth_authenticity_verified'] is False
    for case in result['cases']:
        assert set(case['confounders'])=={'canopy','asphalt','water'}
        assert all(v['false_positive_fraction']==1 for v in case['confounders'].values())
        assert case['files_sha256']


def test_manifest_refuses_external_paths_and_duplicate_ids(tmp_path):
    path=tmp_path/'manifest.json'
    path.write_text(json.dumps({'schema_version':1,'cases':[{'id':'x','image':'../outside.png','reference_mask':'x.png'}]}))
    with pytest.raises(ValueError):evaluate_manifest(path)


def test_real_png_assets_are_io_regression_controls_not_photographic_ground_truth():
    assets=Path(__file__).parent/'imagen'
    for filename in ('sombra (3).png','vista-3d (3).png'):
        result=ShadowDetector().detect_shadow_candidates(str(assets/filename),method='otsu')
        assert result.ndim==2 and result.dtype==bool
        coverage=ShadowDetector().compute_shadow_coverage(result)
        assert 0<=coverage['coverage_fraction']<=1 and not coverage['semantic_discrimination']


def test_primary_photo_analysis_declares_material_ambiguity_without_changing_kernel():
    result=ImageProcessor().analizar_sombra_fotografica(np.array([[50,200],[50,200]]),np.full((2,2),200))
    assert result['coverage_pct']==50 and result['semantic_discrimination'] is False
    assert result['coverage_interpretation']=='photometric_estimate_not_semantic_ground_truth'
    assert result['warnings']
