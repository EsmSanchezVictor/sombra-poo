import math

import numpy as np
import pytest

from core.radiative_tmrt import AdvancedTmrtConfig, calculate_radiative_tmrt, resolve_shortwave_components
from core.settings_manager import SettingsManager
from shadow_temp import Temperatura


def test_default_settings_keep_standard_model(tmp_path):
    manager = SettingsManager(str(tmp_path / "settings.json"))
    assert manager.default_settings()["tmrt_model_mode"] == "standard"


def test_standard_model_preserves_empirical_equation():
    calc = Temperatura(k_factor=0.04, model_mode="standard")
    r = calc.calculate_tmrt(
        25.0, 45.0,
        radiation_override=883.0,
        solar_altitude_override=58.2,
    )
    tau = 1.0 - 0.45 * (1.0 - 0.15)
    assert r["Tmrt_sol"] == pytest.approx(25.0 + 0.04 * 883.0, abs=0.01)
    assert r["Tmrt_sombra"] == pytest.approx(25.0 + 0.04 * 883.0 * tau, abs=0.01)
    assert r["Modelo_Tmrt"] == "standard"


def test_advanced_without_shortwave_returns_air_temperature():
    calc = Temperatura(model_mode="advanced")
    r = calc.calculate_tmrt(
        25.0, 100.0,
        radiation_override=0.0,
        solar_altitude_override=-5.0,
    )
    assert r["Tmrt_sol"] == pytest.approx(25.0, abs=0.01)
    assert r["Tmrt_sombra"] == pytest.approx(25.0, abs=0.01)
    assert r["Modelo_Tmrt"] == "advanced"


def test_advanced_tmrt_uses_dni_dhi_and_shade_monotonically():
    calc = Temperatura(model_mode="advanced")
    kwargs = dict(
        radiation_override=883.0,
        solar_altitude_override=58.2,
        dni_override=832.0,
        dhi_override=176.0,
    )
    sol = calc.calculate_tmrt(25.0, 0.0, **kwargs)
    mid = calc.calculate_tmrt(25.0, 45.0, **kwargs)
    shade = calc.calculate_tmrt(25.0, 100.0, **kwargs)
    assert sol["Tmrt_sombra"] > mid["Tmrt_sombra"] > shade["Tmrt_sombra"] > 25.0
    assert sol["Tmrt_sol"] == pytest.approx(mid["Tmrt_sol"], abs=0.01)
    assert mid["DNI_Wm2"] == pytest.approx(832.0)
    assert mid["DHI_Wm2"] == pytest.approx(176.0)


def test_advanced_map_same_range_semantics_as_scalar():
    calc = Temperatura(model_mode="advanced")
    shade = np.array([[0.0, 50.0, 100.0]], dtype=float)
    m = calc.calculate_tmrt_map(
        25.0, shade,
        radiation_override=800.0,
        solar_altitude_override=60.0,
        dni_override=740.0,
        dhi_override=159.0,
    )["Tmrt_map"]
    assert m.shape == shade.shape
    assert m[0, 0] > m[0, 1] > m[0, 2] > 25.0


def test_fallback_shortwave_components_close_energy_balance():
    ghi, dni, dhi = resolve_shortwave_components(900.0, 45.0)
    assert dni * math.sin(math.radians(45.0)) + dhi == pytest.approx(ghi, rel=1e-9)


def test_advanced_config_validation():
    with pytest.raises(ValueError):
        AdvancedTmrtConfig(ground_albedo=1.2).validated()
    with pytest.raises(ValueError):
        AdvancedTmrtConfig(longwave_emissivity=0.0).validated()


def test_radiative_core_solar_increases_tmrt():
    cfg = AdvancedTmrtConfig()
    no_sun = calculate_radiative_tmrt(25.0, 1.0, 0.0, -2.0, config=cfg)
    sun = calculate_radiative_tmrt(25.0, 1.0, 900.0, 60.0, dni=850.0, dhi=164.0, config=cfg)
    assert no_sun["tmrt_c"] == pytest.approx(25.0, abs=1e-6)
    assert sun["tmrt_c"] > no_sun["tmrt_c"]
