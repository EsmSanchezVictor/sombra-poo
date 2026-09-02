from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from core.scientific_audit import run_scientific_audit
from core.solar_math import solar_position_deg
from core.surface_energy import solve_surface_energy_balance
from core.validation import leer_csv_mediciones
from shadow_temp import Temperatura
import modelo_con_excel as modelo


def test_solar_geometry_single_core_matches_legacy_wrappers():
    lat, lon, doy, hour, tz = -34.6037, -58.3816, 180, 15.0, -3.0
    az, elev = solar_position_deg(lat, lon, doy, hour, tz)

    calc = Temperatura(lat, lon, tz_offset_hours=tz)
    assert math.isclose(calc.solar_altitude(doy, hour), elev, abs_tol=1e-10)
    assert math.isclose(calc.solar_azimuth(doy, hour), az, abs_tol=1e-10)

    theta = modelo.angulo_solar(lat, lon, doy, hour, tz)
    az_r = modelo.azimut_solar(lat, lon, doy, hour, theta, tz)
    assert math.isclose(math.degrees(theta), elev, abs_tol=1e-10)
    assert math.isclose(math.degrees(az_r) % 360.0, az, abs_tol=1e-10)


def test_surface_solver_does_not_fake_convergence_when_clipped():
    result = solve_surface_energy_balance(
        air_temp_k=320.0,
        incident_shortwave_wm2=4000.0,
        solar_absorptance=1.0,
        longwave_emissivity=0.1,
        convective_coefficient_wm2k=0.0,
        thermal_conductivity_wmk=0.01,
        coupling_depth_m=1.0,
        rh_pct=10.0,
    )
    assert result["boundary_clipped"] is True
    assert result["converged"] is False
    assert result["max_abs_residual_wm2"] > 1.0


def test_scientific_audit_has_no_internal_failures_without_field_data():
    report = run_scientific_audit(settings={})
    assert report.counts["fail"] == 0
    assert report.counts["warning"] >= 1  # validación externa todavía no cargada
    assert "APTO CON ADVERTENCIAS" in report.readiness


def test_validation_uses_real_globe_geometry_when_supplied(tmp_path: Path):
    csv_path = tmp_path / "campaign.csv"
    pd.DataFrame([
        {
            "id": "A",
            "ta": 25.0,
            "tg": 35.0,
            "viento": 1.5,
            "ghi": 700.0,
            "globe_diameter_m": 0.05,
            "globe_emissivity": 0.95,
        }
    ]).to_csv(csv_path, index=False)
    rows = leer_csv_mediciones(str(csv_path))
    assert len(rows) == 1
    row = rows[0]
    assert math.isclose(row["globe_diameter_m"], 0.05)
    assert math.isclose(row["globe_emissivity"], 0.95)
    assert row["globe_geometry_default"] is False


def test_validation_marks_default_globe_geometry(tmp_path: Path):
    csv_path = tmp_path / "campaign_defaults.csv"
    pd.DataFrame([
        {"ta": 25.0, "tg": 35.0, "viento": 1.5, "ghi": 700.0}
    ]).to_csv(csv_path, index=False)
    row = leer_csv_mediciones(str(csv_path))[0]
    assert row["globe_geometry_default"] is True
    assert math.isclose(row["globe_diameter_m"], 0.15)
    assert math.isclose(row["globe_emissivity"], 0.97)
