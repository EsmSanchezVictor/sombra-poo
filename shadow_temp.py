import datetime
import math

DEBUG_TMRT = False


def _log_tmrt(message):
    if DEBUG_TMRT:
        print(message)


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

    def calculate_tmrt(self, air_temp, porcentaje_sombra, shadow_type="tree", date_value=None, time_value=None):
        """Calcula Tmrt al sol, Tmrt en sombra y ΔTmrt usando radiación simplificada."""
        if isinstance(date_value, datetime.date):
            day_of_year = date_value.timetuple().tm_yday
        else:
            now = datetime.datetime.now()
            day_of_year = now.timetuple().tm_yday
        if time_value is None:
            now = datetime.datetime.now()
            time_of_day = now.hour + now.minute / 60
        else:
            time_of_day = float(time_value)
        solar_altitude = self.solar_altitude(day_of_year, time_of_day)
        radiation = self.clear_sky_radiation(solar_altitude)

        tau = self.shadow_transmittance(porcentaje_sombra, shadow_type)
        sombra_frac = min(max(porcentaje_sombra / 100, 0), 1)
        radiation_sombra = radiation * tau
        
        if radiation <= 0:
            tmrt_sol = air_temp
            tmrt_sombra = air_temp
            delta_tmrt = 0
        else:
            tmrt_sol = air_temp + self.k_factor * radiation
            tmrt_sombra = air_temp + self.k_factor * radiation_sombra
            delta_tmrt = tmrt_sol - tmrt_sombra
            
        eps = 1.0
        _log_tmrt(
            "TMRT_DEBUG inputs:"
            f" day_of_year={day_of_year}, time={time_of_day:.2f}, lat={self.latitude}, lon={self.longitude}, T_air={air_temp}"
        )
        _log_tmrt(
            "TMRT_DEBUG solar/rad:"
            f" altitude={solar_altitude:.2f}°, I_total={radiation:.2f} W/m², I_directa=N/A, I_difusa=N/A"
        )
        _log_tmrt(
            "TMRT_DEBUG sombra:"
            f" sombra_frac={sombra_frac:.2f}, tau={tau:.2f}, I_sombra={radiation_sombra:.2f} W/m²"
        )
        _log_tmrt(
            "TMRT_DEBUG resultados:"
            f" Tmrt_sol={tmrt_sol:.2f}, Tmrt_sombra={tmrt_sombra:.2f}, delta={delta_tmrt:.2f}"
        )
        if solar_altitude <= 0:
            _log_tmrt("TMRT_DEBUG nota: elevación solar <= 0, radiación directa ~0 ⇒ ΔTmrt ~ 0.")
        if radiation <= eps:
            _log_tmrt("TMRT_DEBUG nota: radiación efectiva baja ⇒ ΔTmrt ~ 0.")
        if radiation > eps and sombra_frac > 0 and math.isclose(radiation_sombra, radiation, rel_tol=1e-6):
            _log_tmrt("TMRT_DEBUG alerta: I_sombra == I_sol con sombra > 0 (posible sombra no aplicada).")
        if sombra_frac == 0:
            _log_tmrt("TMRT_DEBUG nota: sombra_promedio=0 ⇒ Tmrt_sol ≈ Tmrt_sombra.")


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

def _debug_tmrt_case():
    if not DEBUG_TMRT:
        return
    test_date = datetime.date(2026, 2, 7)
    calc = Temperatura(latitude=-34.6037, longitude=-58.3816)
    result = calc.calculate_tmrt(34.0, 50.0, date_value=test_date, time_value=8)
    _log_tmrt(f"TMRT_DEBUG test_case result: {result}")


if __name__ == "__main__":
    _debug_tmrt_case()
