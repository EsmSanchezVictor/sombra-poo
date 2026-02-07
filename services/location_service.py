"""Servicio para cargar y buscar ubicaciones desde CSV."""

from __future__ import annotations

import csv
import os


class LocationService:
    """Carga ubicaciones de LATAM desde un CSV local."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load(self) -> tuple[dict | None, str | None]:
        if not os.path.exists(self.csv_path):
            return None, f"No se encontró el archivo de ubicaciones: {self.csv_path}"
        try:
            countries = set()
            cities_by_country: dict[str, list[str]] = {}
            lookup: dict[str, dict] = {}
            with open(self.csv_path, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    country = row.get("country", "").strip()
                    city = row.get("city", "").strip()
                    province = row.get("province", "").strip()
                    if not country or not city:
                        continue
                    label = f"{city} ({province})" if province else city
                    countries.add(country)
                    cities_by_country.setdefault(country, []).append(label)
                    lookup[label] = {
                        "country": country,
                        "city": city,
                        "province": province,
                        "lat": float(row.get("lat", 0) or 0),
                        "lon": float(row.get("lon", 0) or 0),
                        "tz": row.get("tz", "").strip(),
                        "kind": row.get("kind", "").strip(),
                    }
            countries_list = sorted(countries)
            for country_key in cities_by_country:
                cities_by_country[country_key] = sorted(cities_by_country[country_key])
            return {"countries": countries_list, "cities": cities_by_country, "lookup": lookup}, None
        except Exception as exc:
            return None, f"No se pudo leer el archivo de ubicaciones: {exc}"