from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
import tkinter as tk


@dataclass
class AppState:
    vars: Dict[str, Any]
    ui: Dict[str, Any]
    scene: Dict[str, Any]
    next_n: int = 1
    version: int = 1

    @staticmethod
    def serialize_vars(vars_dict: Dict[str, Any]) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for key, value in vars_dict.items():
            if key in ("arboles", "estructuras", "_app_instance"):
                continue
            if hasattr(value, "get"):
                data[key] = value.get()
            else:
                data[key] = value
        return data

    @staticmethod
    def serialize_arbol(arbol: Any) -> Dict[str, Any]:
        if isinstance(arbol, dict):
            return arbol
        return {
            "x": getattr(arbol, "x", 0),
            "y": getattr(arbol, "y", 0),
            "radio_copa": getattr(arbol, "radio_copa", 0),
            "altura": getattr(arbol, "h", getattr(arbol, "altura", 0)),
            "rho_copa": getattr(arbol, "rho_copa", 0),
            "nombre": getattr(arbol, "nombre", None),
            "id": getattr(arbol, "id", None),
        }

    @staticmethod
    def serialize_estructura(estructura: Any) -> Dict[str, Any]:
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
            "id": getattr(estructura, "id", None),
        }

    @staticmethod
    def deserialize_arboles(items: List[Any], design_module: Any) -> List[Any]:
        arboles: List[Any] = []
        for item in items:
            if isinstance(item, dict):
                arboles.append(
                    design_module.Arbol(
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

    @staticmethod
    def deserialize_estructuras(items: List[Any], design_module: Any) -> List[Any]:
        estructuras: List[Any] = []
        for item in items:
            if isinstance(item, dict):
                estructuras.append(
                    design_module.Estructura(
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

    @staticmethod
    def apply_vars_data(vars_dict: Dict[str, Any], data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if key in ("arboles", "estructuras"):
                continue
            if key in vars_dict and hasattr(vars_dict[key], "set"):
                if hasattr(value, "get"):
                    vars_dict[key].set(value.get())
                else:
                    vars_dict[key].set(value)

    @staticmethod
    def merge_vars(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(defaults)
        merged.update(overrides)
        return merged

    @classmethod
    def from_app(cls, app: Any, next_n: int = 1) -> "AppState":
        vars_data = cls.serialize_vars(app.vars)
        ui = {
            "active_panel": app.active_panel,
            "mode": app.modo_modelo.get(),
            "selected_city": app.simple_city.get(),
            "selected_country": app.simple_country.get(),
        }
        scene = {
            "arboles": [cls.serialize_arbol(a) for a in app.vars.get("arboles", [])],
            "estructuras": [cls.serialize_estructura(e) for e in app.vars.get("estructuras", [])],
        }
        return cls(vars=vars_data, ui=ui, scene=scene, next_n=next_n)

    def to_dict(self, app_name: str, name: str) -> Dict[str, Any]:
        return {
            "version": self.version,
            "meta": {
                "name": name,
                "saved_at": datetime.now().isoformat(),
                "app": app_name,
            },
            "next_n": self.next_n,
            "vars": self.vars,
            "ui": self.ui,
            "scene": self.scene,
        }

    def apply_to_app(self, app: Any, design_module: Any) -> None:
        self.apply_vars_data(app.vars, self.vars)
        self.apply_vars_data(app.vars_modelo, self.vars)
        scene = self.scene or {}
        app.vars["arboles"] = self.deserialize_arboles(scene.get("arboles", []), design_module)
        app.vars["estructuras"] = self.deserialize_estructuras(scene.get("estructuras", []), design_module)

        ui = self.ui or {}
        app.modo_modelo.set(ui.get("mode", app.modo_modelo.get()))
        app.simple_country.set(ui.get("selected_country", app.simple_country.get()))
        if app.locations_data:
            app._update_city_options()
        app.simple_city.set(ui.get("selected_city", app.simple_city.get()))
        app._toggle_modelo_mode()

        if hasattr(app, "entry_lat") and app.entry_lat:
            app.entry_lat.delete(0, tk.END)
            app.entry_lat.insert(0, str(app.vars["lat"].get()))
        if hasattr(app, "entry_lon") and app.entry_lon:
            app.entry_lon.delete(0, tk.END)
            app.entry_lon.insert(0, str(app.vars["lon"].get()))
        if hasattr(app, "entry_temp") and app.entry_temp:
            app.entry_temp.delete(0, tk.END)
            app.entry_temp.insert(0, str(app.simple_temp_air_c.get()))

        target_panel = ui.get("active_panel")
        if isinstance(target_panel, int) and 0 <= target_panel < len(app.panel_frames):
            app.open_panel(target_panel)
