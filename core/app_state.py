"""Estado serializable de la aplicación y soporte de preferencias."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
import tkinter as tk
from tkinter import messagebox
import numpy as np


import diseño as design
from core.scene_objects import ArbolEscena, EstructuraEscena

@dataclass
class ProjectMeta:
    name: str
    saved_at: str
    app: str = "sombra-poo"


class AppState:

    def __init__(self, app):
        self.app = app

    def build_payload(self, project) -> dict:
        saved_at = datetime.now().isoformat(timespec="seconds")
        meta = ProjectMeta(name=project.name, saved_at=saved_at)
        scene_objects = self._extract_scene_objects()
        vars_data = self._serialize_vars(self.app.vars)
        return {
            "version": 1,
            "meta": meta.__dict__,
            "name": project.name,
            "location": self.app.current_location or {},
            "next_n": project.next_n,
            "vars": vars_data,
            "ui": {
                "active_panel": self.app.active_panel,
                "model_mode": self.app.modo_modelo.get(),
                "edit_mode": getattr(self.app, "modo_edicion", tk.StringVar(value="advanced")).get(),
                "panel2_advanced": getattr(self.app, "panel2_advanced_mode", tk.BooleanVar(value=False)).get(),
                "shadow_detector_enabled": getattr(self.app, "shadow_detector_enabled", tk.BooleanVar(value=False)).get(),
                "selected_city": self.app.simple_city.get(),
                "selected_country": self.app.simple_country.get(),
                "curve_button_state": str(getattr(self.app, "curve_button", {}).cget("state")) if hasattr(self.app, "curve_button") else "disabled",
            },
            "paths": {
                "current_image": self._rel(project.root_path, self.app.last_image_path),
                "current_mask": self._rel(project.root_path, self.app.last_mask_path),
                "last_histogram": self._rel(project.root_path, self.app.last_histogram_path),
                "last_curve": self._rel(project.root_path, self.app.last_curve_path),
                "last_matrix_excel": self._rel(project.root_path, self.app.last_matrix_path),
                "edit_excel": self._rel(project.root_path, self.app.last_edit_excel_path),
                "model_excel": self._rel(project.root_path, self.app.last_model_excel_path),
            },
            "last_results_meta": {
                "tmrt_sun": self._to_float(getattr(self.app, "tmrt_result", {}).get("Tmrt_sol") if self.app.tmrt_result else None),
                "tmrt_shade": self._to_float(getattr(self.app, "tmrt_result", {}).get("Tmrt_sombra") if self.app.tmrt_result else None),
                "delta_tmrt": self._to_float(getattr(self.app, "tmrt_result", {}).get("Delta_Tmrt") if self.app.tmrt_result else None),
                "shadow_quality": self._to_float(getattr(self.app, "shadow_quality", None)),
                "temp_graph_image": self._rel(project.root_path, getattr(self.app, "last_temp_graph_path", None)),
            },
            "scene": {
                "objects": [self.scene_object_to_dict(obj) for obj in scene_objects],
            },
        }

    def apply_payload(self, payload: dict) -> None:
        if payload.get("version") != 1:
            messagebox.showerror("Error", "Versión de proyecto no soportada.")
            return

        defaults = self.app._build_vars()
        payload_vars = payload.get("vars", {})
        for key, value in payload_vars.items():
            if key not in self.app.vars:
                self.app.vars[key] = value
            if key not in self.app.vars_modelo:
                self.app.vars_modelo[key] = value
        vars_data = {**defaults, **payload_vars}
        self._apply_vars_data(self.app.vars, vars_data)
        self._apply_vars_data(self.app.vars_modelo, vars_data)

        scene = payload.get("scene", {}) if isinstance(payload.get("scene"), dict) else {}
        scene_objects = []
        if isinstance(scene.get("objects"), list):
            scene_objects = [
                obj for obj in (self.scene_object_from_dict(item) for item in scene.get("objects", [])) if obj
            ]
        else:
            legacy_arboles = self._deserialize_arboles(scene.get("arboles", []))
            legacy_estructuras = self._deserialize_estructuras(scene.get("estructuras", []))
            scene_objects = [
                *[self._arbol_to_scene_obj(arbol) for arbol in legacy_arboles],
                *[self._estructura_to_scene_obj(estructura) for estructura in legacy_estructuras],
            ]

        self.app.vars["_scene_objects"] = scene_objects
        self.app.vars["arboles"] = [self._scene_obj_to_arbol(o) for o in scene_objects if isinstance(o, ArbolEscena)]
        self.app.vars["estructuras"] = [
            self._scene_obj_to_estructura(o) for o in scene_objects if isinstance(o, EstructuraEscena)
        ]

        ui = payload.get("ui", payload.get("ui_state", {}))
        self.app.modo_modelo.set(ui.get("model_mode", ui.get("mode", self.app.modo_modelo.get())))
        if hasattr(self.app, "modo_edicion"):
            self.app.modo_edicion.set(ui.get("edit_mode", self.app.modo_edicion.get()))
        if hasattr(self.app, "panel2_advanced_mode"):
            self.app.panel2_advanced_mode.set(ui.get("panel2_advanced", self.app.panel2_advanced_mode.get()))
        if hasattr(self.app, "shadow_detector_enabled"):
            self.app.shadow_detector_enabled.set(ui.get("shadow_detector_enabled", self.app.shadow_detector_enabled.get()))        
        self.app.simple_country.set(ui.get("selected_country", self.app.simple_country.get()))
        if self.app.locations_data:
            self.app._update_city_options()
        self.app.simple_city.set(ui.get("selected_city", self.app.simple_city.get()))
        self.app._toggle_modelo_mode()
        if hasattr(self.app, "_toggle_edicion_mode"):
            self.app._toggle_edicion_mode()
        if hasattr(self.app, "_toggle_panel2_advanced"):
            self.app._toggle_panel2_advanced()

        location = payload.get("location")
        if location:
            self.app.apply_project_location(location)

        paths = payload.get("paths", {})
        project = self.app.project_manager.current_project
        root = project.root_path if project else ""
        self.app.last_image_path = self._abs(root, paths.get("current_image"))
        self.app.last_curve_path = self._abs(root, paths.get("last_curve"))
        self.app.last_matrix_path = self._abs(root, paths.get("last_matrix_excel"))
        self.app.last_mask_path = self._abs(root, paths.get("current_mask"))
        self.app.last_histogram_path = self._abs(root, paths.get("last_histogram"))
        self.app.last_edit_excel_path = self._abs(root, paths.get("edit_excel"))
        self.app.last_model_excel_path = self._abs(root, paths.get("model_excel"))

        last_meta = payload.get("last_results_meta", {})
        self.app.shadow_quality = last_meta.get("shadow_quality")
        self.app.last_temp_graph_path = self._abs(root, last_meta.get("temp_graph_image"))
        
        target_panel = ui.get("active_panel")
        if isinstance(target_panel, int) and 0 <= target_panel < len(self.app.panel_frames):
            self.app.open_panel(target_panel)
        

        saved_at = payload.get("meta", {}).get("saved_at")
        self.app.update_status_saved_time(saved_at)
        self.app.restore_project_artifacts()

    def _serialize_vars(self, vars_dict: dict) -> dict:
        data = {}
        excluded_keys = {
            "arboles",
            "estructuras",
            "_app_instance",
            "_scene_objects",
            "ax",
            "canvas",
            "figure",
            "fig",
            "toolbar",
        }
        for key, value in vars_dict.items():
            if key in excluded_keys:
                continue
            safe_value = self.make_json_safe(value)
            if safe_value is not None:
                data[key] = safe_value
        return data
    
    def make_json_safe(self, value):
        if isinstance(value, tk.Variable):
            return self.make_json_safe(value.get())
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (list, tuple)):
            converted = [self.make_json_safe(item) for item in value]
            return [item for item in converted if item is not None]
        if isinstance(value, dict):
            converted = {}
            for key, item in value.items():
                safe_item = self.make_json_safe(item)
                if safe_item is not None:
                    converted[str(key)] = safe_item
            return converted
        try:
            json.dumps(value)
            return value
        except TypeError:
            return None

    def _extract_scene_objects(self) -> list:
        raw_objects = self.app.vars.get("_scene_objects", [])
        scene_objects = [obj for obj in raw_objects if isinstance(obj, (ArbolEscena, EstructuraEscena))]
        if scene_objects:
            return scene_objects
        return [
            *[self._arbol_to_scene_obj(arbol) for arbol in self.app.vars.get("arboles", [])],
            *[self._estructura_to_scene_obj(estructura) for estructura in self.app.vars.get("estructuras", [])],
        ]

    def scene_object_to_dict(self, obj) -> dict:
        if isinstance(obj, ArbolEscena):
            payload = {
                "type": "ArbolEscena",
                "x": float(getattr(obj, "x", 0.0)),
                "y": float(getattr(obj, "y", 0.0)),
                "altura": float(getattr(obj, "altura", 0.0)),
                "radio_copa": float(getattr(obj, "radio_copa", 0.0)),
            }
            for attr in ("rho_copa", "opacidad", "id", "nombre"):
                if hasattr(obj, attr):
                    payload[attr] = self.make_json_safe(getattr(obj, attr))
            return payload
        if isinstance(obj, EstructuraEscena):
            payload = {
                "type": "EstructuraEscena",
                "tipo": str(getattr(obj, "tipo", "estructura")),
                "x1": float(getattr(obj, "x1", 0.0)),
                "y1": float(getattr(obj, "y1", 0.0)),
                "x2": float(getattr(obj, "x2", 0.0)),
                "y2": float(getattr(obj, "y2", 0.0)),
                "altura": float(getattr(obj, "altura", 0.0)),
            }
            for attr in ("material", "opacidad", "id", "nombre"):
                if hasattr(obj, attr):
                    payload[attr] = self.make_json_safe(getattr(obj, attr))
            return payload
        return {}

    def scene_object_from_dict(self, data: dict):
        if not isinstance(data, dict):
            return None
        obj_type = data.get("type")
        if obj_type == "ArbolEscena":
            obj = ArbolEscena(
                x=float(data.get("x", 0.0)),
                y=float(data.get("y", 0.0)),
                altura=float(data.get("altura", 0.0)),
                radio_copa=float(data.get("radio_copa", 0.0)),
            )
            if "rho_copa" in data:
                setattr(obj, "rho_copa", float(data.get("rho_copa", 0.0)))
            if "opacidad" in data:
                setattr(obj, "opacidad", float(data.get("opacidad", 1.0)))
            for attr in ("id", "nombre"):
                if attr in data:
                    setattr(obj, attr, data.get(attr))
            return obj
        if obj_type == "EstructuraEscena":
            obj = EstructuraEscena(
                x=float(data.get("x1", data.get("x", 0.0))),
                y=float(data.get("y1", data.get("y", 0.0))),
                altura=float(data.get("altura", 0.0)),
                tipo=str(data.get("tipo", "estructura")),
                x1=float(data.get("x1", 0.0)),
                y1=float(data.get("y1", 0.0)),
                x2=float(data.get("x2", 0.0)),
                y2=float(data.get("y2", 0.0)),
            )
            if "material" in data:
                setattr(obj, "material", data.get("material"))
            if "opacidad" in data:
                setattr(obj, "opacidad", float(data.get("opacidad", 1.0)))
            for attr in ("id", "nombre"):
                if attr in data:
                    setattr(obj, attr, data.get(attr))
            return obj
        return None

    def _arbol_to_scene_obj(self, arbol) -> ArbolEscena:
        obj = ArbolEscena(
            x=float(getattr(arbol, "x", 0.0)),
            y=float(getattr(arbol, "y", 0.0)),
            altura=float(getattr(arbol, "h", getattr(arbol, "altura", 0.0))),
            radio_copa=float(getattr(arbol, "radio_copa", 0.0)),
        )
        if hasattr(arbol, "rho_copa"):
            setattr(obj, "rho_copa", float(getattr(arbol, "rho_copa", 0.0)))
        return obj

    def _estructura_to_scene_obj(self, estructura) -> EstructuraEscena:
        obj = EstructuraEscena(
            x=float(getattr(estructura, "x1", 0.0)),
            y=float(getattr(estructura, "y1", 0.0)),
            altura=float(getattr(estructura, "altura", 0.0)),
            tipo=str(getattr(estructura, "tipo", "estructura")),
            x1=float(getattr(estructura, "x1", 0.0)),
            y1=float(getattr(estructura, "y1", 0.0)),
            x2=float(getattr(estructura, "x2", 0.0)),
            y2=float(getattr(estructura, "y2", 0.0)),
        )
        if hasattr(estructura, "material"):
            setattr(obj, "material", getattr(estructura, "material"))
        if hasattr(estructura, "opacidad"):
            setattr(obj, "opacidad", float(getattr(estructura, "opacidad", 1.0)))
        return obj

    def _scene_obj_to_arbol(self, obj: ArbolEscena):
        return design.Arbol(
            float(getattr(obj, "x", 0.0)),
            float(getattr(obj, "y", 0.0)),
            float(getattr(obj, "altura", 0.0)),
            float(getattr(obj, "rho_copa", 0.0)),
            float(getattr(obj, "radio_copa", 0.0)),
        )

    def _scene_obj_to_estructura(self, obj: EstructuraEscena):
        return design.Estructura(
            str(getattr(obj, "tipo", "Sendero")),
            float(getattr(obj, "x1", 0.0)),
            float(getattr(obj, "y1", 0.0)),
            float(getattr(obj, "x2", 0.0)),
            float(getattr(obj, "y2", 0.0)),
            altura=float(getattr(obj, "altura", 0.0)),
            opacidad=float(getattr(obj, "opacidad", 1.0)),
            material=getattr(obj, "material", None),
        )

    def _serialize_arbol(self, arbol) -> dict:
        if isinstance(arbol, dict):
            return arbol
        return {
            "x": getattr(arbol, "x", 0),
            "y": getattr(arbol, "y", 0),
            "radio_copa": getattr(arbol, "radio_copa", 0),
            "altura": getattr(arbol, "h", getattr(arbol, "altura", 0)),
            "rho_copa": getattr(arbol, "rho_copa", 0),
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
        }

    def _deserialize_arboles(self, items: list) -> list:
        return [
            design.Arbol(float(i.get("x", 0)), float(i.get("y", 0)), float(i.get("altura", 0)), float(i.get("rho_copa", 0)), float(i.get("radio_copa", 0)))
            if isinstance(i, dict) else i
            for i in items
        ]

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
                vars_dict[key].set(value.get() if hasattr(value, "get") else value)

    def _rel(self, root: str, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return os.path.relpath(value, root)
        except ValueError:
            return value

    def _abs(self, root: str, value: str | None) -> str | None:
        if not value:
            return None
        return value if os.path.isabs(value) else os.path.join(root, value)

    def _to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None



from core.settings_manager import SettingsManager