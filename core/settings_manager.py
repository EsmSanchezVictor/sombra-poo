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