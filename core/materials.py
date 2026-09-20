"""Biblioteca de propiedades térmicas/ópticas para el modelo avanzado.

El modelo estándar mantiene el diccionario histórico de ``modelo_con_excel``
para no cambiar resultados previos.  Este módulo se usa solamente cuando el
usuario activa el **modelo avanzado de superficies**.

Las propiedades son valores representativos (no certificados de fabricante).
Para materiales transmisivos se respeta explícitamente el cierre óptico:

    absorptancia + reflectancia + transmitancia = 1

La profundidad de acoplamiento es una longitud térmica efectiva usada por el
modelo estacionario para representar conducción hacia el sustrato. No debe
confundirse con el espesor constructivo real del elemento.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import unicodedata


@dataclass(frozen=True)
class SurfaceMaterial:
    name: str
    solar_absorptance: float
    longwave_emissivity: float
    solar_transmittance: float = 0.0
    solar_reflectance: float | None = None
    thermal_conductivity: float = 0.8  # W m-1 K-1
    coupling_depth_m: float = 0.20     # m, longitud térmica efectiva
    volumetric_heat_capacity: float = 1.6e6  # J m-3 K-1, diagnóstico/futuro transitorio
    source_quality: str = "representative"

    def validated(self) -> "SurfaceMaterial":
        vals = {
            "solar_absorptance": self.solar_absorptance,
            "longwave_emissivity": self.longwave_emissivity,
            "solar_transmittance": self.solar_transmittance,
            "thermal_conductivity": self.thermal_conductivity,
            "coupling_depth_m": self.coupling_depth_m,
            "volumetric_heat_capacity": self.volumetric_heat_capacity,
        }
        if self.solar_reflectance is not None:
            vals["solar_reflectance"] = self.solar_reflectance
        for name, value in vals.items():
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} debe ser finito")
        for name in ("solar_absorptance", "longwave_emissivity", "solar_transmittance"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ValueError(f"{name} debe estar entre 0 y 1")
        if self.solar_reflectance is not None and not 0.0 <= self.solar_reflectance <= 1.0:
            raise ValueError("solar_reflectance debe estar entre 0 y 1")
        if self.thermal_conductivity <= 0 or self.coupling_depth_m <= 0:
            raise ValueError("conductividad y profundidad deben ser positivas")
        if self.volumetric_heat_capacity <= 0:
            raise ValueError("capacidad térmica volumétrica debe ser positiva")
        if self.solar_absorptance + self.reflectance + self.solar_transmittance > 1.000001:
            raise ValueError("alpha + rho + tau no puede superar 1")
        return self

    @property
    def reflectance(self) -> float:
        if self.solar_reflectance is not None:
            return float(self.solar_reflectance)
        return max(0.0, 1.0 - self.solar_absorptance - self.solar_transmittance)

    @property
    def optical_closure(self) -> float:
        return self.solar_absorptance + self.reflectance + self.solar_transmittance

    @property
    def substrate_conductance(self) -> float:
        """Coeficiente equivalente k/d [W m-2 K-1]."""
        return self.thermal_conductivity / self.coupling_depth_m

    @property
    def areal_heat_capacity(self) -> float:
        """Capacidad térmica areal aproximada [J m-2 K-1]."""
        return self.volumetric_heat_capacity * self.coupling_depth_m


def _norm(text: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().lower()


# Valores representativos para simulación comparativa. Los transparentes se
# parametrizan ópticamente de manera distinta al diccionario legacy, donde
# alpha se había usado como un proxy genérico y no como absorptancia espectral.
_ADVANCED = [
    SurfaceMaterial("suelo", 0.70, 0.95, 0.00, 0.30, 0.80, 0.25, 1.6e6),
    SurfaceMaterial("asfalto", 0.90, 0.95, 0.00, 0.10, 0.75, 0.15, 1.9e6),
    SurfaceMaterial("cemento", 0.65, 0.90, 0.00, 0.35, 1.40, 0.20, 2.0e6),
    SurfaceMaterial("Hormigón", 0.65, 0.90, 0.00, 0.35, 1.40, 0.20, 2.0e6),
    SurfaceMaterial("Ladrillo cerámico", 0.70, 0.90, 0.00, 0.30, 0.70, 0.16, 1.5e6),
    SurfaceMaterial("Terracota", 0.65, 0.90, 0.00, 0.35, 0.80, 0.15, 1.5e6),
    SurfaceMaterial("madera tratada", 0.70, 0.85, 0.00, 0.30, 0.14, 0.08, 1.2e6),
    SurfaceMaterial("CLT (Madera laminada natural)", 0.70, 0.85, 0.00, 0.30, 0.13, 0.10, 1.2e6),
    SurfaceMaterial("acero inoxidable", 0.35, 0.25, 0.00, 0.65, 15.0, 0.05, 3.8e6),
    SurfaceMaterial("aluminio", 0.25, 0.15, 0.00, 0.75, 160.0, 0.05, 2.4e6),
    SurfaceMaterial("Corrugado de hierro", 0.75, 0.30, 0.00, 0.25, 45.0, 0.05, 3.7e6),
    SurfaceMaterial("Chapa de Zinc", 0.65, 0.25, 0.00, 0.35, 110.0, 0.05, 2.8e6),
    SurfaceMaterial("Acero Corten", 0.75, 0.75, 0.00, 0.25, 40.0, 0.05, 3.7e6),
    SurfaceMaterial("Caucho", 0.85, 0.95, 0.00, 0.15, 0.16, 0.08, 1.8e6),
    SurfaceMaterial("Plástico reciclado", 0.70, 0.93, 0.00, 0.30, 0.22, 0.08, 1.7e6),
    SurfaceMaterial("Composite Madera-Plástico", 0.70, 0.90, 0.00, 0.30, 0.25, 0.08, 1.6e6),
    # Materiales transmisivos: alpha + rho + tau = 1.
    SurfaceMaterial("policarbonato", 0.10, 0.90, 0.80, 0.10, 0.20, 0.04, 1.2e6),
    SurfaceMaterial("Policarbonato (paneles)", 0.10, 0.90, 0.80, 0.10, 0.20, 0.04, 1.2e6),
    SurfaceMaterial("Vidrio templado", 0.08, 0.90, 0.84, 0.08, 1.00, 0.04, 2.1e6),
    SurfaceMaterial("ETFE", 0.05, 0.85, 0.90, 0.05, 0.17, 0.02, 1.9e6),
    SurfaceMaterial("Fibra de vidrio", 0.30, 0.90, 0.30, 0.40, 0.35, 0.06, 1.5e6),
    SurfaceMaterial("Lámina de polietileno (HDPE)", 0.20, 0.92, 0.50, 0.30, 0.45, 0.03, 1.8e6),
    SurfaceMaterial("Concreto Translúcido", 0.45, 0.90, 0.10, 0.45, 1.20, 0.15, 2.0e6),
    SurfaceMaterial("Fotocerámica (Vidrio Fotovoltaico)", 0.75, 0.90, 0.05, 0.20, 1.00, 0.05, 2.0e6),
]

ADVANCED_MATERIALS = {_norm(m.name): m.validated() for m in _ADVANCED}


def get_surface_material(
    name: str | None,
    *,
    legacy_alpha: float | None = None,
    legacy_epsilon: float | None = None,
) -> SurfaceMaterial:
    """Obtiene material avanzado; para nombres desconocidos crea un opaco.

    El fallback usa las propiedades legacy si se suministran, pero completa
    conductividad/capacidad con valores genéricos. De esta manera no se rompe
    ningún Excel histórico con nombres de materiales fuera de la biblioteca.
    """
    key = _norm(name)
    if key in ADVANCED_MATERIALS:
        return ADVANCED_MATERIALS[key]
    alpha = 0.65 if legacy_alpha is None else min(1.0, max(0.0, float(legacy_alpha)))
    eps = 0.90 if legacy_epsilon is None else min(1.0, max(0.05, float(legacy_epsilon)))
    return SurfaceMaterial(
        str(name or "material genérico"), alpha, eps, 0.0,
        max(0.0, 1.0 - alpha), 0.8, 0.20, 1.6e6,
        source_quality="legacy_fallback",
    ).validated()


def effective_structure_transmittance(material_name: str | None, opacity: float, **legacy) -> float:
    """Transmitancia de una estructura combinando cobertura y material.

    ``opacity`` se interpreta como fracción del elemento efectivamente ocupada
    por el material. La fracción abierta (1-opacity) transmite 100 %; la parte
    ocupada transmite ``tau_material``. Para un material opaco tau=0 se reduce
    a la semántica histórica ``1-opacity``.
    """
    mat = get_surface_material(material_name, **legacy)
    op = min(1.0, max(0.0, float(opacity)))
    return float((1.0 - op) + op * mat.solar_transmittance)


def material_table() -> list[dict[str, float | str]]:
    """Tabla serializable para UI/reportes/tests."""
    rows = []
    for mat in sorted(ADVANCED_MATERIALS.values(), key=lambda m: m.name.lower()):
        rows.append({
            "Material": mat.name,
            "Absorptancia solar": mat.solar_absorptance,
            "Reflectancia solar": mat.reflectance,
            "Transmitancia solar": mat.solar_transmittance,
            "Emisividad LW": mat.longwave_emissivity,
            "Conductividad W/mK": mat.thermal_conductivity,
            "Profundidad efectiva m": mat.coupling_depth_m,
            "Capacidad volumétrica J/m3K": mat.volumetric_heat_capacity,
        })
    return rows
