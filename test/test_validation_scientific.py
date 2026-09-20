from __future__ import annotations

import math

import pandas as pd
import pytest

from core.validation import (
    evaluar_modelos,
    exportar_reporte_validacion,
    guardar_plantilla_csv,
    leer_csv_mediciones,
    particionar_mediciones,
)


def _tau(sombra_pct, tau_total=0.15):
    return 1.0 - (sombra_pct / 100.0) * (1.0 - tau_total)


def _synthetic_rows(k=0.05, air_coeff=0.003):
    rows = []
    for i, (rad, sombra) in enumerate(
        [(400, 10), (500, 20), (600, 30), (700, 40), (800, 50), (900, 60), (750, 25), (850, 45)]
    ):
        ta = 25.0 + (i % 2)
        tau = _tau(sombra)
        tmrt = ta + k * rad * tau
        avoided = rad * (1.0 - tau)
        ta_local = ta - min(2.5, air_coeff * avoided)
        rows.append({
            "id": str(i + 1),
            "ta": ta,
            "tmrt_medido": tmrt,
            "rad": float(rad),
            "dni": 700.0,
            "dhi": 120.0,
            "elevacion": 55.0,
            "sombra_pct": float(sombra),
            "tau": None,
            "tau_sombra_total": 0.15,
            "tipo_sombra": "tree",
            "ta_local": ta_local,
            "v": 1.0,
            "v_fue_default": False,
            "fuente_tmrt": "tmrt_observada",
            "conjunto": "calibracion" if i < 5 else "validacion",
            "fecha": None,
            "hora": None,
            "lat": None,
            "lon": None,
            "timezone": None,
            "tz_offset": None,
            "rh": 50.0,
            "tg": None,
            "especie": "Test",
        })
    return rows


def test_explicit_split_is_respected():
    rows = _synthetic_rows()
    split = particionar_mediciones(rows, validation_fraction=0.4, seed=123)
    assert split.fuente == "partición explícita del CSV"
    assert len(split.calibracion) == 5
    assert len(split.validacion) == 3
    assert split.advertencia is None


def test_scientific_validation_recovers_standard_k_and_local_air_coefficient():
    rows = _synthetic_rows(k=0.05, air_coeff=0.003)
    report = evaluar_modelos(rows, k_actual=0.04)
    assert report["k_calibrado"] == pytest.approx(0.05, abs=1e-8)
    assert report["metricas_modelos"]["Estándar calibrado"]["rmse"] == pytest.approx(0.0, abs=1e-6)
    assert report["metricas_modelos"]["Avanzado v1"] is not None
    air = report["ajuste_aire_local"]["tree"]
    assert air["coefficient"] == pytest.approx(0.003, abs=1e-5)
    assert report["metricas_aire_local"]["tree"]["rmse"] == pytest.approx(0.0, abs=0.01)


def test_internal_holdout_is_reproducible():
    rows = _synthetic_rows()
    for r in rows:
        r["conjunto"] = None
    a = particionar_mediciones(rows, validation_fraction=0.25, seed=77)
    b = particionar_mediciones(rows, validation_fraction=0.25, seed=77)
    assert [r["id"] for r in a.validacion] == [r["id"] for r in b.validacion]
    assert "holdout interno" in a.fuente
    assert a.advertencia


def test_csv_reader_template_and_export(tmp_path):
    template = tmp_path / "plantilla.csv"
    guardar_plantilla_csv(str(template))
    columns = list(pd.read_csv(template).columns)
    assert "ta" in columns
    assert "tmrt" in columns
    assert "sombra_pct" in columns
    assert "conjunto" in columns

    csv_path = tmp_path / "mediciones.csv"
    rows = _synthetic_rows()
    pd.DataFrame([
        {
            "id": r["id"],
            "conjunto": r["conjunto"],
            "ta": r["ta"],
            "tmrt": r["tmrt_medido"],
            "ghi": r["rad"],
            "dni": r["dni"],
            "dhi": r["dhi"],
            "elevacion_solar": r["elevacion"],
            "sombra_pct": r["sombra_pct"],
            "ta_local": r["ta_local"],
            "tipo_sombra": "arbol",
        }
        for r in rows
    ]).to_csv(csv_path, index=False)

    parsed = leer_csv_mediciones(str(csv_path))
    assert len(parsed) == len(rows)
    report = evaluar_modelos(parsed, k_actual=0.04)
    out = tmp_path / "validacion.xlsx"
    exportar_reporte_validacion(str(out), report)
    assert out.exists()
    with pd.ExcelFile(out) as xls:
        assert set(["Resultados", "Metricas", "Calibracion", "Metadatos"]).issubset(xls.sheet_names)
