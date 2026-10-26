"""Synthetic campaign fixtures validate the reporting tool, never field accuracy."""
import csv
from pathlib import Path
import json
import subprocess
import sys
import pytest
from services.field_validation import evaluate_campaign,json_report


def campaign(path,*,same_campaign=False,missing_campaign=False,globe=False,invalid=False):
    columns=['id','campania','conjunto','ta','ghi','tmrt','tg','viento','rh','elevacion_solar','sombra_pct','globe_diameter_m','globe_emissivity']
    rows=[]
    for i in range(6):
        group='calibracion' if i<3 else 'validacion'
        rows.append(dict(id=f'synthetic-{i}',campania='' if missing_campaign else ('same' if same_campaign else group),
            conjunto=group,ta=25+i/2,ghi=400+i*40,tmrt='' if globe else 35+i,tg=30+i if globe else '',
            viento=1,rh=50,elevacion_solar=45,sombra_pct=50,globe_diameter_m=.15,globe_emissivity=.97))
    if invalid:rows[-1]['ta']=''
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
    return path


def test_report_has_bias_rmse_for_each_model_and_does_not_apply_calibration(tmp_path):
    file=campaign(tmp_path/'synthetic.csv');before=file.read_bytes()
    result=evaluate_campaign(file)
    assert result['normalized_rows']==6 and result['campaign_policy']=='disjoint_campaign_labels'
    assert result['calibration_applied'] is False and not result['measurement_authenticity_verified']
    assert len(result['metrics_by_model'])==3
    for metrics in result['metrics_by_model'].values():
        assert metrics['n']==3 and 'bias' in metrics and 'rmse' in metrics
    assert file.read_bytes()==before
    json.dumps(json_report(result),allow_nan=False)


@pytest.mark.parametrize('options',[{'same_campaign':True},{'missing_campaign':True},{'invalid':True}])
def test_strict_campaign_rejects_leakage_missing_metadata_and_discarded_rows(tmp_path,options):
    file=campaign(tmp_path/'synthetic.csv',**options)
    with pytest.raises(ValueError):evaluate_campaign(file)


def test_internal_diagnostic_is_named_explicitly(tmp_path):
    result=evaluate_campaign(campaign(tmp_path/'synthetic.csv',missing_campaign=True),strict_campaigns=False)
    assert result['campaign_policy']=='internal_diagnostic'


def test_globe_conversion_is_counted_and_keeps_instrument_geometry(tmp_path):
    result=evaluate_campaign(campaign(tmp_path/'synthetic.csv',globe=True))
    assert result['source_counts']=={'globo_convertido':6}
    assert result['split']['validacion'][0]['globe_diameter_m']==.15
    assert result['split']['validacion'][0]['globe_emissivity']==.97


def test_duplicate_sample_id_is_rejected(tmp_path):
    path=campaign(tmp_path/'synthetic.csv')
    path.write_text(path.read_text().replace('synthetic-5','synthetic-0'))
    with pytest.raises(ValueError,match='id'):evaluate_campaign(path)


def test_cli_emits_strict_json_and_success_without_opening_projects(tmp_path):
    source=campaign(tmp_path/'synthetic.csv');output=tmp_path/'report.json'
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'tools/validate_field_campaign.py'),str(source),'--report',str(output)],
        cwd=tmp_path,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(output.read_text());assert report['calibration_applied'] is False
    assert report['input_sha256']
