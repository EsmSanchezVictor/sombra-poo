import datetime
import math


class Temperatura:
    """Modelo simplificado de radiación y Tmrt basado en porcentaje de sombra."""

    def __init__(self, latitude=0.0, longitude=0.0, k_factor=0.04):
        self.latitude = latitude
        self.longitude = longitude
        self.k_factor = k_factor

    def solar_declination(self, day_of_year):
        return 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))

    def solar_altitude(self, day_of_year, time_of_day):
        declination = self.solar_declination(day_of_year)
        hour_angle = 15 * (time_of_day - 12)
        latitude_rad = math.radians(self.latitude)
        declination_rad = math.radians(declination)
        altitude = math.degrees(
            math.asin(
                math.sin(latitude_rad) * math.sin(declination_rad)
                + math.cos(latitude_rad)
                * math.cos(declination_rad)
                * math.cos(math.radians(hour_angle))
            )
        )
        return altitude

    def clear_sky_radiation(self, solar_altitude):
        if solar_altitude <= 0:
            return 0
        solar_constant = 1367
        atmospheric_transmittance = 0.75
        radiation = solar_constant * math.sin(math.radians(solar_altitude)) * atmospheric_transmittance
        return max(radiation, 0)

    def shadow_transmittance(self, porcentaje_sombra, shadow_type):
        porcentaje = min(max(porcentaje_sombra, 0), 100)
        if shadow_type == "structure":
            tau_min, tau_max = 0.05, 0.30
        else:
            tau_min, tau_max = 0.15, 0.60
        tau = tau_max - (porcentaje / 100) * (tau_max - tau_min)
        return max(min(tau, tau_max), tau_min)

    def calculate_tmrt(self, air_temp, porcentaje_sombra, shadow_type="tree"):
        """Calcula Tmrt al sol, Tmrt en sombra y ΔTmrt usando radiación simplificada."""
        now = datetime.datetime.now()
        day_of_year = now.timetuple().tm_yday
        time_of_day = now.hour + now.minute / 60
        solar_altitude = self.solar_altitude(day_of_year, time_of_day)
        radiation = self.clear_sky_radiation(solar_altitude)

        tau = self.shadow_transmittance(porcentaje_sombra, shadow_type)

        if radiation <= 0:
            tmrt_sol = air_temp
            tmrt_sombra = air_temp
            delta_tmrt = 0
        else:
            tmrt_sol = air_temp + self.k_factor * radiation
            tmrt_sombra = air_temp + self.k_factor * (radiation * tau)
            delta_tmrt = tmrt_sol - tmrt_sombra

        return {
            "Tmrt_sol": round(tmrt_sol, 2),
            "Tmrt_sombra": round(tmrt_sombra, 2),
            "Delta_Tmrt": round(delta_tmrt, 2),
            "Radiacion_Wm2": round(radiation, 2),
            "Transmitancia_tau": round(tau, 2),
        }

    def temperature_in_shade(self, air_temp, porcentaje_sombra):
        """Compatibilidad con el método antiguo. Devuelve Tmrt en sombra."""
        result = self.calculate_tmrt(air_temp, porcentaje_sombra)
        return result["Tmrt_sombra"]
