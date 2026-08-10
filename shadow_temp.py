"""Modelo simplificado de radiación y Tmrt basado en porcentaje de sombra.

CAMBIOS respecto a la versión original:

1. Los `print` gateados por `DEBUG_TMRT` se reemplazan por el módulo
   estándar `logging`. Así se puede activar/desactivar el detalle sin
   tocar código, y los logs se pueden mandar a archivo en producción
   en vez de a stdout.

2. Se agrega `solar_azimuth()`. Antes el azimut solo se calculaba en
   `services/solar_engine.py` con una aproximación lineal cruda
   (`(180 + (hora-12)*15) % 360`), que no es la fórmula real de
   azimut solar. Ahora vive acá, al lado de `solar_altitude()`, con
   la misma fuente de declinación — así ambos módulos usan una sola
   fuente de verdad para la geometría solar.

3. `calculate_tmrt()` acepta un parámetro opcional `radiation_override`.
   Esto es importante: hoy existen DOS modelos de radiación de cielo
   despejado que pueden dar resultados distintos para la misma fecha/
   hora — el de acá (fórmula propia con transmitancia fija 0.75) y el
   de `SolarEngine` (que usa pvlib/Ineichen cuando está disponible,
   mucho más preciso). Si quien llama ya calculó la radiación con
   SolarEngine, ahora puede pasarla y evitar la inconsistencia. Si no
   se pasa nada, se sigue usando el modelo simplificado interno (no
   rompe compatibilidad).

4. Se agrega `calibrate_k_factor()`: dado que k_factor=0.04 estaba
   hardcodeado sin respaldo documentado, este método permite ajustarlo
   contra una medición real de Tmrt en campo (por ejemplo con
   termómetro de globo), en vez de dejarlo como un número mágico.
   No inventa un valor "correcto" — deja explícito que hay que
   calibrarlo con datos reales del sitio de estudio.
"""
import datetime
import logging
import math

import numpy as np

logger = logging.getLogger("sombra_poo.tmrt")


class Temperatura:
    """Modelo simplificado de radiación y Tmrt basado en porcentaje de sombra.

    AVISO IMPORTANTE (léase antes de confiar en los resultados):
    `Tmrt = T_air + k_factor * radiación` es una aproximación LINEAL,
    no el cálculo riguroso de temperatura media radiante que define
    ISO 7726 (que requiere temperatura de globo o un balance de flujos
    radiativos de onda corta/larga con factores de vista del cuerpo
    humano). Sirve como estimación relativa de "cuánto ayuda la sombra"
    pero los valores absolutos de Tmrt no deberían presentarse como
    medición certificada sin calibrar `k_factor` contra datos reales.
    """

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

    def solar_azimuth(self, day_of_year, time_of_day):
        """NUEVO. Azimut solar real (0-360°, medido desde el norte,
        sentido horario), reemplaza la aproximación lineal que vivía
        suelta en solar_engine.py."""
        declination = self.solar_declination(day_of_year)
        hour_angle = 15 * (time_of_day - 12)
        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        altitude_rad = math.radians(self.solar_altitude(day_of_year, time_of_day))
        hour_angle_rad = math.radians(hour_angle)

        sin_az = -math.sin(hour_angle_rad) * math.cos(dec_rad) / max(math.cos(altitude_rad), 1e-6)
        cos_az = (math.sin(dec_rad) - math.sin(lat_rad) * math.sin(altitude_rad)) / max(
            (math.cos(lat_rad) * math.cos(altitude_rad)), 1e-6
        )
        azimuth = math.degrees(math.atan2(sin_az, cos_az))
        return azimuth % 360

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

    def shadow_transmittance_map(self, porcentaje_sombra_map, shadow_type):
        """NUEVO: misma fórmula que shadow_transmittance() pero vectorizada
        sobre un array de numpy en vez de un escalar."""
        porcentaje = np.clip(porcentaje_sombra_map, 0, 100)
        if shadow_type == "structure":
            tau_min, tau_max = 0.05, 0.30
        else:
            tau_min, tau_max = 0.15, 0.60
        tau = tau_max - (porcentaje / 100) * (tau_max - tau_min)
        return np.clip(tau, tau_min, tau_max)

    def calculate_tmrt_map(self, air_temp, porcentaje_sombra_map, shadow_type="tree",
                            date_value=None, time_value=None, radiation_override=None):
        """NUEVO: versión de calculate_tmrt() que opera sobre un mapa
        (array 2D) de % de sombra en vez de un único valor promedio.

        Se usa para que las curvas de nivel del Panel 2 muestren
        TEMPERATURA en sombra calculada punto por punto (según el % de
        sombra local de cada píxel, la ubicación, fecha y hora), en vez
        de graficar directamente los valores crudos de gris de la
        imagen — que no tienen unidad física ni son comparables entre
        fotos con distinta exposición.

        La posición solar y la radiación de cielo despejado son
        iguales para toda la escena en un mismo instante, así que se
        calculan UNA sola vez (escalares) y solo la transmitancia y el
        Tmrt final se vectorizan sobre el mapa.
        """
        porcentaje_sombra_map = np.asarray(porcentaje_sombra_map, dtype=np.float32)

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
        if radiation_override is not None:
            radiation = max(0.0, float(radiation_override))
        else:
            radiation = self.clear_sky_radiation(solar_altitude)

        if radiation <= 0:
            tmrt_map = np.full_like(porcentaje_sombra_map, air_temp, dtype=np.float32)
            return {"Tmrt_map": tmrt_map, "Radiacion_Wm2": 0.0, "Solar_altitude": solar_altitude}

        tau_map = self.shadow_transmittance_map(porcentaje_sombra_map, shadow_type)
        radiation_map = radiation * tau_map
        tmrt_map = air_temp + self.k_factor * radiation_map
        return {
            "Tmrt_map": tmrt_map,
            "Radiacion_Wm2": round(radiation, 2),
            "Solar_altitude": round(solar_altitude, 2),
        }

    def calculate_tmrt(self, air_temp, porcentaje_sombra, shadow_type="tree",
                        date_value=None, time_value=None, radiation_override=None):
        """Calcula Tmrt al sol, Tmrt en sombra y ΔTmrt.

        radiation_override: si se pasa (por ejemplo, el GHI calculado por
        SolarEngine vía pvlib), se usa en vez de recalcular con el modelo
        simplificado interno. Recomendado cuando pvlib está disponible,
        porque es más preciso que la transmitancia fija de 0.75 de acá.
        """
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

        if radiation_override is not None:
            radiation = max(0.0, float(radiation_override))
        else:
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
        logger.debug(
            "TMRT inputs: day_of_year=%s time=%.2f lat=%s lon=%s T_air=%s",
            day_of_year, time_of_day, self.latitude, self.longitude, air_temp,
        )
        logger.debug(
            "TMRT solar/rad: altitude=%.2f° I_total=%.2f W/m2 (fuente=%s)",
            solar_altitude, radiation, "override" if radiation_override is not None else "modelo interno",
        )
        logger.debug(
            "TMRT sombra: sombra_frac=%.2f tau=%.2f I_sombra=%.2f W/m2",
            sombra_frac, tau, radiation_sombra,
        )
        logger.debug(
            "TMRT resultados: Tmrt_sol=%.2f Tmrt_sombra=%.2f delta=%.2f",
            tmrt_sol, tmrt_sombra, delta_tmrt,
        )
        if solar_altitude <= 0:
            logger.debug("Elevación solar <= 0: radiación directa ~0, ΔTmrt ~0.")
        if radiation <= eps:
            logger.debug("Radiación efectiva baja: ΔTmrt ~0.")
        if radiation > eps and sombra_frac > 0 and math.isclose(radiation_sombra, radiation, rel_tol=1e-6):
            logger.warning("I_sombra == I_sol con sombra > 0 (posible sombra no aplicada).")
        if sombra_frac == 0:
            logger.debug("sombra_promedio=0: Tmrt_sol ≈ Tmrt_sombra.")

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

    def calibrate_k_factor(self, tmrt_medido: float, air_temp: float, radiation: float) -> float:
        """NUEVO: calibra k_factor contra una medición real de Tmrt en
        campo (por ejemplo, termómetro de globo negro) para un momento
        en que se conoce la radiación efectiva. No reemplaza automáticamente
        self.k_factor — devuelve el valor sugerido para que se revise
        antes de aplicarlo:

            k_sugerido = calc.calibrate_k_factor(tmrt_medido=45.2,
                                                   air_temp=30.0,
                                                   radiation=750.0)
            calc.k_factor = k_sugerido  # solo si el valor es razonable
        """
        if radiation <= 0:
            raise ValueError("No se puede calibrar con radiación <= 0.")
        return (tmrt_medido - air_temp) / radiation


def _debug_tmrt_case():
    logging.basicConfig(level=logging.DEBUG)
    test_date = datetime.date(2026, 2, 7)
    calc = Temperatura(latitude=-34.6037, longitude=-58.3816)
    result = calc.calculate_tmrt(34.0, 50.0, date_value=test_date, time_value=8)
    logger.debug("Caso de prueba: %s", result)


if __name__ == "__main__":
    _debug_tmrt_case()
