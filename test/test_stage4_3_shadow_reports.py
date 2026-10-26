"""Los informes no mezclan orígenes ni acreditan evidencia inexistente."""
import json
from pathlib import Path
import pytest
from services.shadow_evaluation import evaluate_manifest, summarize_cases

FIXTURES = Path(__file__).parent/'fixtures/shadow_semantics'


def test_real_requirement_refuses_synthetic_benchmark():
    with pytest.raises(ValueError, match='fotografías reales'):
        evaluate_manifest(FIXTURES/'manifest.json', require_real=True)


def test_weighted_summary_uses_counts_and_separates_profiles_and_origins():
    result = evaluate_manifest(FIXTURES/'manifest.json')
    a, b = result['cases']
    small = dict(a, metrics=dict(a['metrics'], tp=1, fp=0, fn=1, tn=2, pixels=4), confounders={})
    # Same pixels under different profiles/origins must not silently inflate one group.
    groups = summarize_cases([a, small, b, dict(b, origin='unspecified')])
    assert len(groups) == 3
    combined = groups[0]
    assert combined['cases'] == 2
    assert combined['tp'] == a['metrics']['tp']+1
    assert combined['recall'] == pytest.approx(combined['tp']/(combined['tp']+combined['fn']))
    assert combined['materials']['water']['false_positive_fraction'] == 1.


def test_report_includes_full_evaluation_domain_and_does_not_certify_authenticity():
    result = evaluate_manifest(FIXTURES/'manifest.json')
    assert result['real_photo_files'] == result['unique_real_photo_sha256'] == 0
    assert result['ground_truth_authenticity_verified'] is False
    for case in result['cases']:
        assert case['domain']['image_pixels'] == case['domain']['evaluated_pixels']
        assert case['domain']['excluded_roi_pixels'] == 0
    json.dumps(result, allow_nan=False)


def test_real_labels_require_annotation_metadata_and_duplicate_images_are_counted_once(tmp_path):
    import shutil
    for p in FIXTURES.iterdir():
        if p.is_file():
            shutil.copyfile(p, tmp_path/p.name)
    path = tmp_path/'manifest.json'
    spec = json.loads(path.read_text())
    for case in spec['cases']:
        case['origin'] = 'real_photo'
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='annotation.author'):
        evaluate_manifest(path, require_real=True)
    # Deliberately relabel synthetic bytes to show that declarations cannot prove authenticity.
    for case in spec['cases']:
        case['annotation'] = dict(author='Prueba automatizada', method='Etiquetas sintéticas; no son fotos reales')
    path.write_text(json.dumps(spec))
    result = evaluate_manifest(path, require_real=True)
    assert result['real_photo_cases'] == 2
    assert result['real_photo_files'] == result['unique_real_photo_sha256'] == 1
    assert result['ground_truth_authenticity_verified'] is False
