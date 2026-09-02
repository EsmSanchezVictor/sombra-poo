"""Gestiona preferencias persistentes de la aplicación."""

from __future__ import annotations

import json
import os


class SettingsManager:
    """Maneja lectura, escritura y aplicación de settings.json."""

    def __init__(self, settings_path: str):
        self.settings_path = settings_path

    def default_settings(self) -> dict:
        return {
            "version": 1,
            "ui_mode": "simple",
            "units": "C",
            "temp_unit": "C",
            "distance_unit": "m",
            "default_country": "Argentina",
            "default_city": "Paraná",
            "default_cloudiness": "Despejado",
            "default_wind": "moderado",
            "k_factor": 0.04,
            "tmrt_model_mode": "standard",
            "surface_model_mode": "standard",
            # Vegetación/ET v13: solo interviene si el usuario selecciona
            # advanced_vegetation; el modo estándar sigue intacto.
            "ground_vegetation_fraction": 0.50,
            "vegetation_water_availability": 0.75,
            "canopy_water_availability": 0.75,
            # Fuente radiativa/meteorológica v14. El default conserva el
            # comportamiento previo: cielo despejado modelado.
            "radiation_source_mode": "clear_sky",
            "clear_sky_use_pvlib": False,
            "meteorology_max_gap_minutes": 90.0,
            "k_factor_info": None,
            # Ta local estimada: defaults conservadores v8; solo cambian si
            # el usuario aplica explícitamente una calibración de campaña.
            "local_air_tree_coefficient": 0.0025,
            "local_air_tree_max_cooling": 2.5,
            "local_air_tree_calibration_info": None,
            "local_air_structure_coefficient": 0.0012,
            "local_air_structure_max_cooling": 1.2,
            "local_air_structure_calibration_info": None,
            "last_project_path": None,
        }

    def load(self) -> dict:
        """Carga settings.json, creando el archivo si no existe."""
        defaults = self.default_settings()
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        if not os.path.exists(self.settings_path):
            self.write(defaults)
        try:
            with open(self.settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            data = {}
        return {**defaults, **data}

    def write(self, data: dict) -> None:
        """Persiste settings.json en disco."""
        with open(self.settings_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def apply_to_app(self, app, settings: dict) -> None:
        """Aplica preferencias a la UI sin recalcular."""
        if not settings:
            return
        app.modo_modelo.set(settings.get("ui_mode", "simple"))
        if hasattr(app, "tmrt_model_mode"):
            app.tmrt_model_mode.set(settings.get("tmrt_model_mode", "standard"))
        if hasattr(app, "surface_model_mode"):
            app.surface_model_mode.set(settings.get("surface_model_mode", "standard"))
        if hasattr(app, "radiation_source_mode"):
            app.radiation_source_mode.set(settings.get("radiation_source_mode", "clear_sky"))
        if hasattr(app, "use_pvlib_engine"):
            app.use_pvlib_engine.set(bool(settings.get("clear_sky_use_pvlib", False)))
        app.temp_unit.set(settings.get("temp_unit", settings.get("units", "C")))
        app.distance_unit.set(settings.get("distance_unit", "m"))
        app.simple_cloudiness.set(settings.get("default_cloudiness", "Despejado"))
        app.simple_country.set(settings.get("default_country", app.simple_country.get()))
        app.simple_city.set(settings.get("default_city", app.simple_city.get()))
        default_wind = settings.get("default_wind", "moderado")
        if "viento" in app.vars:
            app.vars["viento"].set(default_wind)
        if "viento" in app.vars_modelo:
            app.vars_modelo["viento"].set(default_wind)
        if hasattr(app, "city_combo") and app.locations_data:
            app._update_city_options()
        app._toggle_modelo_mode()