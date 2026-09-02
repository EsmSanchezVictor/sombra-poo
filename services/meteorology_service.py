"""Orquestación de fuentes meteorológicas y radiativas (v14)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.meteorology import MeteorologicalSeries, complete_radiation_components


SOURCE_LABELS = {
    "clear_sky": "Cielo despejado modelado",
    "manual_measured": "Medición puntual ingresada",
    "manual_scenario": "Escenario radiativo manual",
    "observed_series": "Serie meteorológica importada",
}


class MeteorologyService:
    def __init__(self):
        self.series: MeteorologicalSeries | None = None

    def load_series(self, path: str | Path, *, timezone: str) -> dict[str, Any]:
        self.series = MeteorologicalSeries.from_csv(path, timezone=timezone)
        return self.series.summary()

    def clear_series(self) -> None:
        self.series = None

    def resolve(
        self,
        *,
        mode: str,
        solar_engine,
        lat: float,
        lon: float,
        dt,
        manual_ghi: float | None = None,
        manual_dni: float | None = None,
        manual_dhi: float | None = None,
        max_gap_minutes: float = 90.0,
    ) -> dict[str, Any]:
        mode = str(mode or "clear_sky").strip().lower()
        if mode not in SOURCE_LABELS:
            mode = "clear_sky"

        azimuth, elevation = solar_engine.get_solar_position(lat, lon, dt)
        day = dt.timetuple().tm_yday
        warnings: list[str] = []
        weather = {"ta_c": None, "rh_pct": None, "wind_m_s": None, "cloud_fraction": None}
        sample_status = None

        if mode == "clear_sky":
            rad = solar_engine.get_radiation(lat, lon, dt)
            # source detail mantiene pvlib/fallback sin confundirlo con la
            # categoría científica de procedencia.
            source_detail = rad.get("source", "fallback")
            components = {"ghi": rad["ghi"], "dni": rad["dni"], "dhi": rad["dhi"], "derived": [], "warnings": []}
            quality = "modeled_clear_sky"
        elif mode in {"manual_measured", "manual_scenario"}:
            components = complete_radiation_components(
                ghi=manual_ghi, dni=manual_dni, dhi=manual_dhi,
                elevation_deg=elevation, day_of_year=day,
            )
            source_detail = "manual"
            quality = "measured_point" if mode == "manual_measured" else "prescribed_scenario"
            warnings.extend(components.get("warnings", []))
            if components.get("derived"):
                quality += "+derived_components"
        else:
            if self.series is None:
                raise ValueError("No hay una serie meteorológica importada.")
            sample = self.series.sample_at(dt, max_gap_minutes=max_gap_minutes)
            if sample is None:
                raise ValueError(
                    "La serie meteorológica no tiene un dato utilizable para este instante "
                    f"(cobertura {self.series.start.isoformat()} a {self.series.end.isoformat()})."
                )
            sample_status = sample.status
            warnings.extend(sample.warnings)
            weather = {k: sample.values.get(k) for k in weather}
            components = complete_radiation_components(
                ghi=sample.values.get("ghi"),
                dni=sample.values.get("dni"),
                dhi=sample.values.get("dhi"),
                elevation_deg=elevation,
                day_of_year=day,
            )
            warnings.extend(components.get("warnings", []))
            source_detail = Path(self.series.path).name if self.series.path else "serie"
            quality = sample.status
            if components.get("derived"):
                quality += "+derived_components"

        return {
            "ghi": float(components["ghi"]),
            "dni": float(components["dni"]),
            "dhi": float(components["dhi"]),
            "azimuth": float(azimuth),
            "elevation": float(elevation),
            "timezone": solar_engine.tz,
            "source_mode": mode,
            "source": mode,  # compatibilidad con código previo
            "source_label": SOURCE_LABELS[mode],
            "source_detail": source_detail,
            "quality": quality,
            "derived_components": list(components.get("derived", [])),
            "warnings": warnings,
            "sample_status": sample_status,
            **weather,
        }
