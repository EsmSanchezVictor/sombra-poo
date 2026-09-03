"""Auditoría interna de preparación científica del proyecto.

La auditoría NO valida el modelo contra la realidad: comprueba consistencia
interna, dependencias, trazabilidad y disponibilidad de evidencia externa.
Sirve como checklist reproducible antes de iniciar o cerrar una campaña de
validación.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import importlib.util
import json
import math
import os
import zoneinfo
from typing import Any, Iterable

import numpy as np

from core.materials import ADVANCED_MATERIALS
from core.model_registry import SCIENTIFIC_RELEASE, SCIENTIFIC_SCHEMA, methodology_manifest
from core.solar_math import solar_position_deg
from core.species import nombres_especies, propiedades_especie
from core.surface_energy import solve_surface_energy_balance, SurfaceEnergyConfig
from shadow_temp import Temperatura


@dataclass(frozen=True)
class AuditItem:
    code: str
    level: str  # pass | warning | fail | info
    title: str
    detail: str


@dataclass
class ScientificAuditReport:
    generated_at: str
    scientific_release: str
    scientific_schema: str
    items: list[AuditItem]
    project_root: str | None = None

    @property
    def counts(self) -> dict[str, int]:
        out = {"pass": 0, "warning": 0, "fail": 0, "info": 0}
        for item in self.items:
            out[item.level] = out.get(item.level, 0) + 1
        return out

    @property
    def readiness(self) -> str:
        c = self.counts
        if c.get("fail", 0):
            return "NO APTO: hay fallas internas que deben resolverse"
        if c.get("warning", 0):
            return "APTO CON ADVERTENCIAS: listo para campaña, no para afirmar validación externa"
        return "APTO INTERNAMENTE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "scientific_release": self.scientific_release,
            "scientific_schema": self.scientific_schema,
            "project_root": self.project_root,
            "readiness": self.readiness,
            "counts": self.counts,
            "items": [asdict(i) for i in self.items],
            "methodology": methodology_manifest(),
        }


_REQUIRED_MODULES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "opencv": "cv2",
    "openpyxl": "openpyxl",
    "matplotlib": "matplotlib",
    "Pillow": "PIL",
    "fpdf2": "fpdf",
}
_OPTIONAL_MODULES = {
    "pvlib": "pvlib",
    "pythermalcomfort": "pythermalcomfort",
}


def _item(code: str, level: str, title: str, detail: str) -> AuditItem:
    return AuditItem(code=code, level=level, title=title, detail=detail)


def _check_dependencies(items: list[AuditItem]) -> None:
    for label, module in _REQUIRED_MODULES.items():
        if importlib.util.find_spec(module) is None:
            items.append(_item(f"dep.{module}", "fail", f"Dependencia requerida: {label}", "No está instalada."))
        else:
            items.append(_item(f"dep.{module}", "pass", f"Dependencia requerida: {label}", "Disponible."))
    for label, module in _OPTIONAL_MODULES.items():
        if importlib.util.find_spec(module) is None:
            msg = (
                "No disponible: las rutas asociadas quedan deshabilitadas o usan fallback. "
                "Antes de una liberación científica conviene ejecutar la suite también con esta dependencia."
            )
            items.append(_item(f"dep.optional.{module}", "warning", f"Dependencia opcional: {label}", msg))
        else:
            items.append(_item(f"dep.optional.{module}", "pass", f"Dependencia opcional: {label}", "Disponible."))


def _check_timezone(items: list[AuditItem]) -> None:
    try:
        zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")
        items.append(_item("timezone.iana", "pass", "Base de zonas horarias IANA", "America/Argentina/Buenos_Aires disponible."))
    except Exception as exc:
        items.append(_item("timezone.iana", "fail", "Base de zonas horarias IANA", f"No se pudo abrir la zona: {exc}"))


def _check_solar(items: list[AuditItem]) -> None:
    try:
        az, elev = solar_position_deg(-34.6037, -58.3816, 180, 12.0, -3.0)
        finite = math.isfinite(az) and math.isfinite(elev) and 0.0 <= az < 360.0 and -90.0 <= elev <= 90.0
        if not finite:
            raise ValueError(f"posición inválida az={az}, elev={elev}")
        items.append(_item(
            "solar.shared_core", "pass", "Geometría solar analítica compartida",
            f"Sanity check Buenos Aires: elev={elev:.2f}°, az={az:.2f}°."
        ))
    except Exception as exc:
        items.append(_item("solar.shared_core", "fail", "Geometría solar analítica compartida", str(exc)))


def _check_shadow(items: list[AuditItem]) -> None:
    try:
        calc = Temperatura(-34.6, -58.4, tz_offset_hours=-3)
        t0 = calc.shadow_transmittance(0.0, "tree")
        t100 = calc.shadow_transmittance(100.0, "tree")
        if not math.isclose(t0, 1.0, abs_tol=1e-12):
            raise ValueError(f"0 % sombra produjo tau={t0}")
        if not (0.0 <= t100 < 1.0):
            raise ValueError(f"100 % sombra produjo tau={t100}")
        items.append(_item("shadow.invariants", "pass", "Invariantes de sombra", f"tau(0%)={t0:.3f}; tau(100%)={t100:.3f}."))
    except Exception as exc:
        items.append(_item("shadow.invariants", "fail", "Invariantes de sombra", str(exc)))


def _check_materials(items: list[AuditItem]) -> None:
    bad = []
    for key, mat in ADVANCED_MATERIALS.items():
        closure = mat.optical_closure
        if not math.isfinite(closure) or abs(closure - 1.0) > 1e-6:
            bad.append(f"{mat.name}: alpha+rho+tau={closure:.6f}")
    if bad:
        items.append(_item("materials.optical_closure", "fail", "Cierre óptico de materiales", "; ".join(bad[:8])))
    else:
        items.append(_item("materials.optical_closure", "pass", "Cierre óptico de materiales", f"{len(ADVANCED_MATERIALS)} entradas cumplen α+ρ+τ=1."))
    items.append(_item(
        "materials.provenance", "warning", "Propiedades de materiales",
        "La biblioteca avanzada usa valores representativos; para uso predictivo absoluto deben documentarse fabricante/literatura y rango de incertidumbre."
    ))


def _check_species(items: list[AuditItem]) -> None:
    names = nombres_especies()
    generic = []
    for name in names:
        props = propiedades_especie(name)
        if props.get("veg_source_quality") == "generic_default":
            generic.append(name)
    if generic:
        items.append(_item(
            "species.generic_vegetation", "warning", "LAI/Kc específicos por especie",
            f"{len(generic)}/{len(names)} especies usan LAI/Kc genéricos. Es válido para comparación, pero requiere calibración/bibliografía antes de afirmar predicción específica por especie."
        ))
    else:
        items.append(_item("species.generic_vegetation", "pass", "LAI/Kc específicos por especie", "Todas las especies tienen procedencia específica."))


def _check_surface_solver(items: list[AuditItem]) -> None:
    try:
        cfg = SurfaceEnergyConfig()
        r = solve_surface_energy_balance(
            air_temp_k=298.15,
            incident_shortwave_wm2=700.0,
            solar_absorptance=0.70,
            longwave_emissivity=0.95,
            convective_coefficient_wm2k=10.0,
            thermal_conductivity_wmk=0.8,
            coupling_depth_m=0.2,
            rh_pct=50.0,
            cloud_fraction=0.2,
            config=cfg,
        )
        if not r["converged"] or r["max_abs_residual_wm2"] > cfg.residual_tolerance_wm2:
            raise ValueError(f"no cerró: residual={r['max_abs_residual_wm2']:.4g} W/m²")
        items.append(_item(
            "surface.energy_closure", "pass", "Cierre del balance avanzado de superficie",
            f"Residual máximo={r['max_abs_residual_wm2']:.4g} W/m²; iteraciones={r['iterations']}."
        ))

        extreme = solve_surface_energy_balance(
            air_temp_k=320.0,
            incident_shortwave_wm2=4000.0,
            solar_absorptance=1.0,
            longwave_emissivity=0.1,
            convective_coefficient_wm2k=0.0,
            thermal_conductivity_wmk=0.01,
            coupling_depth_m=1.0,
            rh_pct=10.0,
            config=cfg,
        )
        if extreme["boundary_clipped"] and extreme["converged"]:
            raise ValueError("un caso saturado en el límite fue marcado falsamente como convergente")
        items.append(_item(
            "surface.boundary_diagnostic", "pass", "Diagnóstico de límites numéricos",
            "El solver distingue saturación en límites de convergencia energética real."
        ))
    except Exception as exc:
        items.append(_item("surface.energy_closure", "fail", "Solver avanzado de superficies", str(exc)))


def _check_project_structure(items: list[AuditItem], project_root: str | None) -> None:
    if not project_root:
        items.append(_item("project.none", "info", "Proyecto abierto", "Auditoría estática: no se proporcionó carpeta de proyecto."))
        return
    required = [
        os.path.join("entradas", "imagenes"),
        os.path.join("entradas", "meteorologia"),
        "escena",
        os.path.join("analisis", "elementos"),
        os.path.join("resultados", "proyecto"),
        os.path.join("resultados", "validacion"),
        os.path.join("resultados", "informes"),
        "respaldos", "config",
    ]
    missing = [rel for rel in required if not os.path.isdir(os.path.join(project_root, rel))]
    if missing:
        items.append(_item("project.structure", "fail", "Estructura de proyecto", "Faltan carpetas: " + ", ".join(missing)))
    else:
        items.append(_item("project.structure", "pass", "Estructura de proyecto", "Carpetas esperadas disponibles."))


def _check_settings(items: list[AuditItem], settings: dict[str, Any] | None) -> None:
    settings = settings or {}
    tmrt = str(settings.get("tmrt_model_mode", "standard"))
    surf = str(settings.get("surface_model_mode", "standard"))
    rad = str(settings.get("radiation_source_mode", "clear_sky"))
    valid = True
    if tmrt not in {"standard", "advanced"}:
        items.append(_item("settings.tmrt_mode", "fail", "Modo Tmrt", f"Valor no reconocido: {tmrt}")); valid = False
    if surf not in {"standard", "advanced", "advanced_vegetation"}:
        items.append(_item("settings.surface_mode", "fail", "Modo de superficie", f"Valor no reconocido: {surf}")); valid = False
    if rad not in {"clear_sky", "manual_measured", "manual_scenario", "observed_series"}:
        items.append(_item("settings.radiation_mode", "fail", "Fuente radiativa", f"Valor no reconocido: {rad}")); valid = False
    if valid:
        items.append(_item("settings.model_modes", "pass", "Modos metodológicos", f"Tmrt={tmrt}; superficie={surf}; radiación={rad}."))


def _check_snapshots(items: list[AuditItem], snapshots: Iterable[dict] | None) -> None:
    snaps = list(snapshots or [])
    if not snaps:
        items.append(_item("evidence.snapshots", "warning", "Evidencia del proyecto", "No hay snapshots formales guardados para auditar trazabilidad de resultados."))
        return
    missing_model = sum(not s.get("modelo_tmrt") for s in snaps)
    missing_rad = sum(not s.get("fuente_radiativa") for s in snaps)
    if missing_model or missing_rad:
        items.append(_item(
            "evidence.snapshot_provenance", "warning", "Trazabilidad de snapshots",
            f"{missing_model} sin modelo Tmrt; {missing_rad} sin fuente radiativa. Pueden corresponder a snapshots históricos."
        ))
    else:
        items.append(_item("evidence.snapshot_provenance", "pass", "Trazabilidad de snapshots", f"{len(snaps)} snapshots con modelo y fuente radiativa."))


def _check_validation(items: list[AuditItem], validation_summary: Any) -> None:
    if not validation_summary:
        items.append(_item(
            "validation.external", "warning", "Validación experimental externa",
            "No hay una campaña de validación asociada. El software está preparado, pero los resultados aún no constituyen validación empírica."
        ))
        return
    items.append(_item("validation.external", "pass", "Validación cargada", "Existe un resumen de campaña/calibración en el proyecto; revise n, partición y métricas antes de publicar."))


def run_scientific_audit(
    *,
    project_root: str | None = None,
    settings: dict[str, Any] | None = None,
    snapshots: Iterable[dict] | None = None,
    validation_summary: Any = None,
) -> ScientificAuditReport:
    items: list[AuditItem] = []
    _check_dependencies(items)
    _check_timezone(items)
    _check_solar(items)
    _check_shadow(items)
    _check_materials(items)
    _check_species(items)
    _check_surface_solver(items)
    _check_project_structure(items, project_root)
    _check_settings(items, settings)
    _check_snapshots(items, snapshots)
    _check_validation(items, validation_summary)
    return ScientificAuditReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        scientific_release=SCIENTIFIC_RELEASE,
        scientific_schema=SCIENTIFIC_SCHEMA,
        items=items,
        project_root=project_root,
    )


def format_audit_text(report: ScientificAuditReport) -> str:
    icons = {"pass": "[OK]", "warning": "[ADVERTENCIA]", "fail": "[FALLA]", "info": "[INFO]"}
    lines = [
        f"Auditoría científica {report.scientific_release}",
        f"Fecha: {report.generated_at}",
        f"Estado: {report.readiness}",
        f"Conteos: {report.counts}",
        "",
    ]
    for item in report.items:
        lines.append(f"{icons.get(item.level, '[?]')} {item.title}")
        lines.append(f"  {item.detail}")
    return "\n".join(lines)


def save_audit_json(path: str, report: ScientificAuditReport) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    return path
