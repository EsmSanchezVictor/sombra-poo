from core.uncertainty import OperationalUncertaintyConfig, estimate_tmrt_uncertainty


def test_standard_uncertainty_is_reproducible_and_ordered():
    cfg = OperationalUncertaintyConfig(samples=300, seed=123)
    a = estimate_tmrt_uncertainty(
        air_temp_c=25, tau=0.6, ghi=800, solar_elevation_deg=50,
        model_mode="standard", k_factor=0.04, source_quality="observed", config=cfg,
    )
    b = estimate_tmrt_uncertainty(
        air_temp_c=25, tau=0.6, ghi=800, solar_elevation_deg=50,
        model_mode="standard", k_factor=0.04, source_quality="observed", config=cfg,
    )
    assert a["tmrt_shade"] == b["tmrt_shade"]
    assert a["tmrt_shade"]["p05"] < a["tmrt_shade"]["p50"] < a["tmrt_shade"]["p95"]
    assert a["tmrt_sun"]["p50"] > a["tmrt_shade"]["p50"]


def test_advanced_uncertainty_runs_and_has_sensitivity():
    cfg = OperationalUncertaintyConfig(samples=120, seed=7)
    out = estimate_tmrt_uncertainty(
        air_temp_c=26, tau=0.5, ghi=850, dni=800, dhi=195,
        solar_elevation_deg=55, model_mode="advanced",
        source_quality="modeled_clear_sky", config=cfg,
    )
    assert out["tmrt_shade"]["p95"] > out["tmrt_shade"]["p05"]
    assert len(out["sensitivity"]) >= 4
    assert out["method"] == "operational_monte_carlo_v1"


def test_modeled_radiation_has_wider_default_sigma_than_observed():
    cfg = OperationalUncertaintyConfig(samples=120, seed=9)
    obs = estimate_tmrt_uncertainty(
        air_temp_c=25, tau=0.6, ghi=800, solar_elevation_deg=50,
        model_mode="standard", source_quality="observed", config=cfg,
    )
    mod = estimate_tmrt_uncertainty(
        air_temp_c=25, tau=0.6, ghi=800, solar_elevation_deg=50,
        model_mode="standard", source_quality="modeled_clear_sky", config=cfg,
    )
    assert mod["radiation_relative_sigma"] > obs["radiation_relative_sigma"]
