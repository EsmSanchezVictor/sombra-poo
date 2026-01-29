"""Estado serializable de la aplicación y soporte de preferencias."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

import diseño as design


@dataclass
class ProjectMeta:
    """Metadatos básicos del proyecto."""

    name: str
    saved_at: str
    app: str = "sombra-poo"


class AppState:
    """Serializa y aplica el estado de la app sin ejecutar el modelo."""

    def __init__(self, app):
        self.app = app

    def build_payload(self, project) -> dict:
        """Construye el JSON de proyecto con información de UI y escena."""
        meta = ProjectMeta(
            name=project.name,
            saved_at=datetime.now().isoformat(),
        )
        return {
            "version": 1,
            "meta": meta.__dict__,
            "next_n": project.next_n,
            "vars": self._serialize_vars(self.app.vars),
            "ui": {
                "active_panel": self.app.active_panel,
                "mode": self.app.modo_modelo.get(),
                "selected_city": self.app.simple_city.get(),
                "selected_country": self.app.simple_country.get(),
            },
            "scene": {
                "arboles": [self._serialize_arbol(a) for a in self.app.vars.get("arboles", [])],
                "estructuras": [self._serialize_estructura(e) for e in self.app.vars.get("estructuras", [])],
            },
        }

    def apply_payload(self, payload: dict) -> None:
        """Aplica un payload validado sobre la UI y el estado interno."""
        if payload.get("version") != 1:
            messagebox.showerror("Error", "Versión de proyecto no soportada.")
            return

        defaults = self.app._build_vars()
        payload_vars = payload.get("vars", {})
        # Preservar claves nuevas en memoria para no perderlas al re-guardar
        for key, value in payload_vars.items():
            if key not in self.app.vars:
                self.app.vars[key] = value
            if key not in self.app.vars_modelo:
                self.app.vars_modelo[key] = value
        vars_data = {**defaults, **payload_vars}
        self._apply_vars_data(self.app.vars, vars_data)
        self._apply_vars_data(self.app.vars_modelo, vars_data)

        scene = payload.get("scene", {})
        self.app.vars["arboles"] = self._deserialize_arboles(scene.get("arboles", []))
        self.app.vars["estructuras"] = self._deserialize_estructuras(scene.get("estructuras", []))

        ui = payload.get("ui", {})
        self.app.modo_modelo.set(ui.get("mode", self.app.modo_modelo.get()))
        self.app.simple_country.set(ui.get("selected_country", self.app.simple_country.get()))
        if self.app.locations_data:
            self.app._update_city_options()
        self.app.simple_city.set(ui.get("selected_city", self.app.simple_city.get()))
        self.app._toggle_modelo_mode()

        if hasattr(self.app, "entry_lat") and self.app.entry_lat:
            self.app.entry_lat.delete(0, tk.END)
            self.app.entry_lat.insert(0, str(self.app.vars["lat"].get()))
        if hasattr(self.app, "entry_lon") and self.app.entry_lon:
            self.app.entry_lon.delete(0, tk.END)
            self.app.entry_lon.insert(0, str(self.app.vars["lon"].get()))
        if hasattr(self.app, "entry_temp") and self.app.entry_temp:
            self.app.entry_temp.delete(0, tk.END)
            self.app.entry_temp.insert(0, str(self.app.simple_temp_air_c.get()))

        target_panel = ui.get("active_panel")
        if isinstance(target_panel, int) and 0 <= target_panel < len(self.app.panel_frames):
            self.app.open_panel(target_panel)

    def _serialize_vars(self, vars_dict: dict) -> dict:
        data = {}
        for key, value in vars_dict.items():
            if key in ("arboles", "estructuras", "_app_instance"):
                continue
            if hasattr(value, "get"):
                data[key] = value.get()
            else:
                data[key] = value
        return data

    def _serialize_arbol(self, arbol) -> dict:
        if isinstance(arbol, dict):
            return arbol
        return {
            "x": getattr(arbol, "x", 0),
            "y": getattr(arbol, "y", 0),
            "radio_copa": getattr(arbol, "radio_copa", 0),
            "altura": getattr(arbol, "h", getattr(arbol, "altura", 0)),
            "rho_copa": getattr(arbol, "rho_copa", 0),
            "nombre": getattr(arbol, "nombre", None),
        }

    def _serialize_estructura(self, estructura) -> dict:
        if isinstance(estructura, dict):
            return estructura
        return {
            "tipo": getattr(estructura, "tipo", None),
            "x1": getattr(estructura, "x1", 0),
            "y1": getattr(estructura, "y1", 0),
            "x2": getattr(estructura, "x2", 0),
            "y2": getattr(estructura, "y2", 0),
            "altura": getattr(estructura, "altura", 0),
            "material": getattr(estructura, "material", None),
            "opacidad": getattr(estructura, "opacidad", 1),
            "nombre": getattr(estructura, "nombre", None),
        }

    def _deserialize_arboles(self, items: list) -> list:
        arboles = []
        for item in items:
            if isinstance(item, dict):
                arboles.append(
                    design.Arbol(
                        float(item.get("x", 0)),
                        float(item.get("y", 0)),
                        float(item.get("altura", 0)),
                        float(item.get("rho_copa", 0)),
                        float(item.get("radio_copa", 0)),
                    )
                )
            else:
                arboles.append(item)
        return arboles

    def _deserialize_estructuras(self, items: list) -> list:
        estructuras = []
        for item in items:
            if isinstance(item, dict):
                estructuras.append(
                    design.Estructura(
                        item.get("tipo", "Sendero"),
                        float(item.get("x1", 0)),
                        float(item.get("y1", 0)),
                        float(item.get("x2", 0)),
                        float(item.get("y2", 0)),
                        altura=float(item.get("altura", 0)),
                        opacidad=float(item.get("opacidad", 1)),
                        material=item.get("material"),
                    )
                )
            else:
                estructuras.append(item)
        return estructuras

    def _apply_vars_data(self, vars_dict: dict, data: dict) -> None:
        for key, value in data.items():
            if key in ("arboles", "estructuras"):
                continue
            if key in vars_dict and hasattr(vars_dict[key], "set"):
                if hasattr(value, "get"):
                    vars_dict[key].set(value.get())
                else:
                    vars_dict[key].set(value)


from core.settings_manager import SettingsManager