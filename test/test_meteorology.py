from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from core.meteorology import MeteorologicalSeries, complete_radiation_components
from services.meteorology_service import MeteorologyService


def test_series_aliases_exact_and_interpolation(tmp_path: Path):
    p = tmp_path / "met.csv"
    p.write_text(
        "fecha,hora,radiacion_global,temperatura_aire,humedad_relativa,velocidad_viento\n"
        "2026-01-15,12:00,800,25,50,2\n"
        "2026-01-15,13:00,600,27,60,4\n",
        encoding="utf-8",
    )
    serie = MeteorologicalSeries.from_csv(p, timezone="America/Argentina/Buenos_Aires")
    exact = serie.sample_at(datetime(2026, 1, 15, 12, 0))
    assert exact is not None
    assert exact.status == "observed"
    assert exact.get("ghi") == pytest.approx(800)
    assert exact.get("ta_c") == pytest.approx(25)

    mid = serie.sample_at(datetime(2026, 1, 15, 12, 30))
    assert mid is not None
    assert mid.status == "interpolated"
    assert mid.get("ghi") == pytest.approx(700)
    assert mid.get("ta_c") == pytest.approx(26)
    assert mid.get("rh_pct") == pytest.approx(55)
    assert mid.get("wind_m_s") == pytest.approx(3)


def test_series_does_not_extrapolate_or_bridge_large_gap(tmp_path: Path):
    p = tmp_path / "met.csv"
    p.write_text(
        "timestamp,ghi\n"
        "2026-01-15 10:00,500\n"
        "2026-01-15 14:00,900\n",
        encoding="utf-8",
    )
    serie = MeteorologicalSeries.from_csv(p, timezone="UTC")
    assert serie.sample_at(datetime(2026, 1, 15, 9, 0)) is None
    assert serie.sample_at(datetime(2026, 1, 15, 12, 0), max_gap_minutes=90) is None


def test_complete_components_identity_from_ghi_dhi():
    out = complete_radiation_components(
        ghi=800, dni=None, dhi=160, elevation_deg=30, day_of_year=180
    )
    assert out["dni"] == pytest.approx((800 - 160) / 0.5)
    assert out["dni"] * 0.5 + out["dhi"] == pytest.approx(800)
    assert "dni_identity" in out["derived"]


def test_erbs_from_ghi_closes_horizontal_balance():
    out = complete_radiation_components(
        ghi=850, dni=None, dhi=None, elevation_deg=55, day_of_year=30
    )
    import math
    recomposed = out["dni"] * math.sin(math.radians(55)) + out["dhi"]
    assert recomposed == pytest.approx(850, rel=1e-10)
    assert "dni_erbs" in out["derived"]
    assert "dhi_erbs" in out["derived"]


class _SolarStub:
    tz = "UTC"
    def get_solar_position(self, lat, lon, dt):
        return 20.0, 30.0
    def get_radiation(self, lat, lon, dt):
        return {"ghi": 900.0, "dni": 1200.0, "dhi": 300.0, "source": "pvlib"}


def test_service_manual_measured_is_traced():
    service = MeteorologyService()
    out = service.resolve(
        mode="manual_measured", solar_engine=_SolarStub(), lat=0, lon=0,
        dt=datetime(2026, 1, 15, 12), manual_ghi=700, manual_dni=None, manual_dhi=None,
    )
    assert out["source_mode"] == "manual_measured"
    assert out["quality"].startswith("measured_point")
    assert out["ghi"] == pytest.approx(700)
    assert out["derived_components"]


def test_service_observed_series_uses_weather_and_marks_interpolation(tmp_path: Path):
    p = tmp_path / "met.csv"
    p.write_text(
        "timestamp,ghi,ta_c,rh_pct,wind_m_s,cloud_cover\n"
        "2026-01-15 12:00,800,24,45,2,20\n"
        "2026-01-15 13:00,600,26,55,4,60\n",
        encoding="utf-8",
    )
    service = MeteorologyService()
    service.load_series(p, timezone="UTC")
    out = service.resolve(
        mode="observed_series", solar_engine=_SolarStub(), lat=0, lon=0,
        dt=datetime(2026, 1, 15, 12, 30), max_gap_minutes=90,
    )
    assert out["source_mode"] == "observed_series"
    assert out["sample_status"] == "interpolated"
    assert out["ta_c"] == pytest.approx(25)
    assert out["rh_pct"] == pytest.approx(50)
    assert out["wind_m_s"] == pytest.approx(3)
    assert out["ghi"] == pytest.approx(700)
    assert out["cloud_fraction"] == pytest.approx(0.40)
