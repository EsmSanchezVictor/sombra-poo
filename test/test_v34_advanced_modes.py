from pathlib import Path
from types import SimpleNamespace

import pytest

from core.climate_profile import VIENTO_CATEGORIA_MS, viento_categoria_a_ms
from database_manager import DatabaseManager
from modelo_con_excel import (
    _surface_model_mode,
    calcular_coeficiente_conveccion,
    cargar_preset,
)


class Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _preset_vars(lat=-31.0, year=2026):
    return {
        "lat": Var(lat),
        "T_min": Var(290.0),
        "T_max": Var(310.0),
        "I_sol_base": Var(800.0),
        "dia": Var(180),
        "nubosidad": Var("Parcial"),
        "_year": year,
        "_update_required": False,
    }


def test_season_presets_follow_hemisphere_and_sync_date():
    south = _preset_vars(-31.0)
    cargar_preset("verano", south)
    assert south["dia"].get() == 355
    assert south["_date_iso"] == "2026-12-21"
    cargar_preset("invierno", south)
    assert south["dia"].get() == 172
    assert south["_date_iso"] == "2026-06-21"

    north = _preset_vars(40.0)
    cargar_preset("verano", north)
    assert north["dia"].get() == 172
    cargar_preset("invierno", north)
    assert north["dia"].get() == 355


def test_sunny_and_cloudy_presets_change_radiation_and_cloud_label():
    values = _preset_vars()
    cargar_preset("soleado", values)
    assert values["I_sol_base"].get() == 1200
    assert values["nubosidad"].get() == "Despejado"
    cargar_preset("nublado", values)
    assert values["I_sol_base"].get() == 300
    assert values["nubosidad"].get() == "Nublado"


def test_wind_accepts_categories_and_numeric_strings_consistently():
    assert viento_categoria_a_ms("nulo") == VIENTO_CATEGORIA_MS["nulo"] == 0.5
    assert viento_categoria_a_ms("3,2") == pytest.approx(3.2)
    assert calcular_coeficiente_conveccion("3.2") == pytest.approx(5.7 + 3.8 * 3.2)
    assert calcular_coeficiente_conveccion("fuerte") > calcular_coeficiente_conveccion("moderado")
    assert calcular_coeficiente_conveccion("moderado") > calcular_coeficiente_conveccion("nulo")


def test_surface_advanced_mode_cannot_leak_into_hidden_simple_ui():
    app = SimpleNamespace()
    app.modo_modelo = Var("simple")
    app.modo_edicion = Var("simple")
    app.surface_model_mode = Var("advanced_vegetation")
    app.vars_modelo = {"_app_instance": app}
    app.vars = {"_app_instance": app}

    assert _surface_model_mode(app.vars_modelo) == "standard"
    assert _surface_model_mode(app.vars) == "standard"

    app.modo_modelo.set("advanced")
    assert _surface_model_mode(app.vars_modelo) == "advanced_vegetation"
    app.modo_edicion.set("advanced")
    assert _surface_model_mode(app.vars) == "advanced_vegetation"


def test_delete_session_history_preserves_active_session_and_cascades_projects(tmp_path):
    db = DatabaseManager(str(tmp_path / "users.db"))
    try:
        assert db.add_user("admin", "clave-prueba-2026", True, "A", "Admin", "1", "a@a.com", "", "", "", "X")
        old_session = db.start_session("admin")
        db.start_project_work(old_session, "Viejo", project_root="/old")
        db.end_session(old_session)
        active_session = db.start_session("admin")
        active_project = db.start_project_work(active_session, "Actual", project_root="/new")

        deleted = db.delete_session_history(exclude_session_id=active_session)
        assert deleted == 1
        rows = db.fetch_session_history(limit=20)
        assert rows
        assert {row["session_id"] for row in rows} == {active_session}
        assert {row["project_period_id"] for row in rows} == {active_project}

        db.cursor.execute("SELECT COUNT(*) FROM session_projects WHERE session_id = ?", (old_session,))
        assert db.cursor.fetchone()[0] == 0
    finally:
        db.close()


def test_v34_ui_wiring_uses_correct_model_vars_and_hides_advanced_sections():
    root = Path(__file__).parents[1]
    panels = (root / "ui" / "panels.py").read_text(encoding="utf-8")
    app_ui = (root / "ui" / "app_ui.py").read_text(encoding="utf-8")
    state = (root / "core" / "app_state.py").read_text(encoding="utf-8")

    assert '("Verano", "verano"), ("Invierno", "invierno")' in panels
    assert 'modelo.cargar_preset(p, app.vars_modelo)' in panels
    assert 'app.model_tools_frame = herramientas' in panels
    assert 'tools.grid_remove()' in panels
    assert 'def _toggle_temperatura_mode(app):' in panels
    assert 'frame.pack_forget()' in panels
    assert 'text="Entrada avanzada"' in panels
    assert 'variable=app.tmrt_model_mode' in panels
    assert 'variable=app.surface_model_mode' in panels

    assert 'self.modo_temperatura = tk.StringVar(value="simple")' in app_ui
    controller = (root / "services" / "meteorology_controller.py").read_text(encoding="utf-8")
    assert 'mode_override=None if advanced else "clear_sky"' in controller
    assert "resolve_temperature_context(self," in app_ui
    assert 'def _resolve_temperature_scenario' in app_ui
    assert "self.vars_modelo['_app_instance'] = self" in app_ui

    assert '"vars_modelo": self._serialize_vars(self.app.vars_modelo)' in state
    assert '"tmrt_model_mode"' in state
    assert '"surface_model_mode"' in state
    assert '"manual_ghi"' in state
    assert '"manual_dni"' in state
    assert '"manual_dhi"' in state


def _thermal_vars(mode="advanced", wind="moderado", rh=50.0, cloud="Despejado"):
    return {
        "_surface_model_mode": mode,
        "arboles": [],
        "estructuras": [],
        "dia": Var(355),
        "lat": Var(-31.0),
        "humedad": Var(rh),
        "viento": Var(wind),
        "nubosidad": Var(cloud),
    }


def test_advanced_surface_controls_have_measurable_effects():
    import numpy as np
    from modelo_con_excel import calcular_campo_termico_superficie

    x = np.linspace(0.0, 10.0, 4)
    X, Y = np.meshgrid(x, x)
    theta = np.deg2rad(55.0)
    azimuth = np.deg2rad(20.0)

    calm = calcular_campo_termico_superficie(
        _thermal_vars("advanced", wind="nulo", rh=40, cloud="Despejado"),
        X, Y, theta, azimuth, 800.0, 300.0,
    )
    windy = calcular_campo_termico_superficie(
        _thermal_vars("advanced", wind="fuerte", rh=40, cloud="Despejado"),
        X, Y, theta, azimuth, 800.0, 300.0,
    )
    cloudy = calcular_campo_termico_superficie(
        _thermal_vars("advanced", wind="nulo", rh=85, cloud="Nublado"),
        X, Y, theta, azimuth, 800.0, 300.0,
    )

    assert windy["h_c"] > calm["h_c"]
    assert not np.allclose(windy["T"], calm["T"])
    assert not np.allclose(cloudy["T"], calm["T"])


def test_surface_model_selector_changes_calculation_path():
    import numpy as np
    from modelo_con_excel import calcular_campo_termico_superficie

    X, Y = np.meshgrid(np.linspace(0, 5, 3), np.linspace(0, 5, 3))
    theta = np.deg2rad(50.0)
    azimuth = np.deg2rad(10.0)
    standard = calcular_campo_termico_superficie(
        _thermal_vars("standard"), X, Y, theta, azimuth, 700.0, 299.0
    )
    advanced = calcular_campo_termico_superficie(
        _thermal_vars("advanced"), X, Y, theta, azimuth, 700.0, 299.0
    )
    vegetation = calcular_campo_termico_superficie(
        _thermal_vars("advanced_vegetation"), X, Y, theta, azimuth, 700.0, 299.0
    )

    assert standard["model"] == "standard"
    assert advanced["model"] == "advanced"
    assert vegetation["model"] == "advanced_vegetation"
    assert not np.allclose(standard["T"], advanced["T"])
    assert not np.allclose(advanced["T"], vegetation["T"])
