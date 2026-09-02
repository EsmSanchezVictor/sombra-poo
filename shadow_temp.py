"""Modelo empírico simplificado de radiación y Tmrt.

La relación ``Tmrt = Ta + k * GHI`` se conserva como modelo rápido y
calibrable. No sustituye un balance radiativo humano completo. Las mejoras de
esta versión se concentran en coherencia solar, semántica de la sombra y
compatibilidad con un motor solar externo (pvlib/SolarEngine).
"""
from __future__ import annotations

import datetime
import logging
import math

import numpy as np

from core.radiative_tmrt import AdvancedTmrtConfig, calculate_radiative_tmrt
from core.solar_math import (
    equation_of_time_minutes, solar_declination_deg, solar_hour_angle_deg,
    solar_elevation_deg, solar_azimuth_deg, standard_meridian_deg,
)

logger = logging.getLogger("sombra_poo.tmrt")


class Temperatura:
    """Estimación relativa de Tmrt basada en radiación y cobertura de sombra.

    ``porcentaje_sombra`` se interpreta como FRACCIÓN DE ÁREA/EXPOSICIÓN
    sombreada: 0 % implica pleno sol (transmitancia efectiva = 1) y 100 %
    implica sombra completa con la transmitancia residual de copa/estructura.
    """

    DEFAULT_FULL_SHADE_TAU = {
        "tree": 0.15,
        "structure": 0.05,
    }

    # Modelo empírico y deliberadamente conservador para estimar la
    # temperatura del aire local bajo sombra.  NO convierte Tmrt en Ta.
    # Parte de la radiación solar que deja de llegar al punto:
    #
    #   ΔTa_local = min(ΔTa_max, c_air * (GHI - GHI_efectiva))
    #
    # c_air tiene unidades K/(W/m²).  Los valores por defecto buscan
    # representar que el aire cambia mucho menos que la carga radiante.
    # Deben considerarse parámetros calibrables si se dispone de medición
    # microclimática local.
    DEFAULT_LOCAL_AIR_MODEL = {
        "tree": {"coefficient": 0.0025, "max_cooling": 2.5},
        "structure": {"coefficient": 0.0012, "max_cooling": 1.2},
    }

    MODEL_STANDARD = "standard"
    MODEL_ADVANCED = "advanced"

    def __init__(
        self,
        latitude=0.0,
        longitude=0.0,
        k_factor=0.04,
        tz_offset_hours=None,
        model_mode="standard",
        advanced_config=None,
    ):
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.k_factor = float(k_factor)
        self.tz_offset_hours = tz_offset_hours
        self.model_mode = self._normalize_model_mode(model_mode)
        self.advanced_config = advanced_config or AdvancedTmrtConfig()

    @classmethod
    def _normalize_model_mode(cls, value):
        value = str(value or cls.MODEL_STANDARD).strip().lower()
        aliases = {
            "standard": cls.MODEL_STANDARD,
            "estandar": cls.MODEL_STANDARD,
            "estándar": cls.MODEL_STANDARD,
            "empirical": cls.MODEL_STANDARD,
            "empirico": cls.MODEL_STANDARD,
            "empírico": cls.MODEL_STANDARD,
            "advanced": cls.MODEL_ADVANCED,
            "avanzado": cls.MODEL_ADVANCED,
            "radiative": cls.MODEL_ADVANCED,
        }
        if value not in aliases:
            raise ValueError(f"Modelo Tmrt desconocido: {value}")
        return aliases[value]

    @property
    def model_label(self):
        return (
            "Avanzado · balance radiativo v1"
            if self.model_mode == self.MODEL_ADVANCED
            else "Estándar · empírico calibrable"
        )

    def _meridiano_estandar(self):
        return standard_meridian_deg(self.longitude, self.tz_offset_hours)

    def _ecuacion_del_tiempo(self, day_of_year):
        return equation_of_time_minutes(day_of_year)

    def _hour_angle(self, time_of_day, day_of_year=None):
        if day_of_year is None:
            # Compatibilidad histórica para llamadas internas sin día.
            return 15.0 * (float(time_of_day) - 12.0) + (self.longitude - self._meridiano_estandar())
        return solar_hour_angle_deg(
            self.longitude, day_of_year, time_of_day, self.tz_offset_hours
        )

    def solar_declination(self, day_of_year):
        return solar_declination_deg(day_of_year)

    def solar_altitude(self, day_of_year, time_of_day):
        return solar_elevation_deg(
            self.latitude, self.longitude, day_of_year, time_of_day, self.tz_offset_hours
        )

    def solar_azimuth(self, day_of_year, time_of_day):
        """Azimut 0-360°, desde norte en sentido horario."""
        return solar_azimuth_deg(
            self.latitude, self.longitude, day_of_year, time_of_day, self.tz_offset_hours
        )

    def clear_sky_radiation(self, solar_altitude):
        """Fallback simple de GHI de cielo despejado (W/m²)."""
        if float(solar_altitude) <= 0.0:
            return 0.0
        solar_constant = 1367.0
        atmospheric_transmittance = 0.75
        radiation = solar_constant * math.sin(math.radians(float(solar_altitude))) * atmospheric_transmittance
        return max(float(radiation), 0.0)

    @classmethod
    def _tau_sombra_total(cls, shadow_type: str, full_shadow_transmittance=None) -> float:
        if full_shadow_transmittance is None:
            tau = cls.DEFAULT_FULL_SHADE_TAU.get(shadow_type, cls.DEFAULT_FULL_SHADE_TAU["tree"])
        else:
            tau = float(full_shadow_transmittance)
        return min(max(float(tau), 0.0), 1.0)

    def shadow_transmittance(self, porcentaje_sombra, shadow_type="tree", full_shadow_transmittance=None):
        """Transmitancia efectiva del área analizada.

        Si S es la fracción sombreada y tau_s la transmitancia residual de la
        zona totalmente sombreada::

            tau_eff = (1-S)*1 + S*tau_s = 1 - S*(1-tau_s)

        Esto garantiza que 0 % de sombra no produzca enfriamiento ficticio.
        """
        s = min(max(float(porcentaje_sombra) / 100.0, 0.0), 1.0)
        tau_s = self._tau_sombra_total(shadow_type, full_shadow_transmittance)
        return 1.0 - s * (1.0 - tau_s)

    def shadow_transmittance_map(
        self,
        porcentaje_sombra_map,
        shadow_type="tree",
        full_shadow_transmittance=None,
    ):
        porcentaje = np.asarray(porcentaje_sombra_map, dtype=np.float32)
        s = np.clip(porcentaje / 100.0, 0.0, 1.0)
        tau_s = self._tau_sombra_total(shadow_type, full_shadow_transmittance)
        return 1.0 - s * (1.0 - tau_s)


    @classmethod
    def _local_air_parameters(cls, shadow_type="tree", cooling_coefficient=None, max_cooling=None):
        defaults = cls.DEFAULT_LOCAL_AIR_MODEL.get(
            shadow_type, cls.DEFAULT_LOCAL_AIR_MODEL["tree"]
        )
        coefficient = (
            float(defaults["coefficient"])
            if cooling_coefficient is None
            else max(0.0, float(cooling_coefficient))
        )
        cooling_cap = (
            float(defaults["max_cooling"])
            if max_cooling is None
            else max(0.0, float(max_cooling))
        )
        return coefficient, cooling_cap

    def estimate_local_air_temperature_map(
        self,
        air_temp,
        porcentaje_sombra_map,
        radiation,
        shadow_type="tree",
        full_shadow_transmittance=None,
        cooling_coefficient=None,
        max_cooling=None,
        transmittance_map_override=None,
    ):
        """Estima Ta local bajo sombra sin confundirla con Tmrt.

        La estimación usa la reducción de radiación de onda corta respecto
        a pleno sol y aplica una respuesta empírica acotada.  Es una
        variable microclimática *estimada*, no una medición ni una solución
        CFD/energética del aire.

        Con 0 % de sombra, Ta_local == Ta_referencia.  La reducción máxima
        queda limitada por ``max_cooling`` (2.5 °C para árbol por defecto).
        """
        sombra = np.asarray(porcentaje_sombra_map, dtype=np.float32)
        if transmittance_map_override is not None:
            tau = np.asarray(transmittance_map_override, dtype=np.float32)
            if tau.shape != sombra.shape:
                raise ValueError("transmittance_map_override debe tener la misma forma que el mapa de sombra.")
            tau = np.clip(tau, 0.0, 1.0)
        else:
            tau = self.shadow_transmittance_map(
                sombra,
                shadow_type=shadow_type,
                full_shadow_transmittance=full_shadow_transmittance,
            )
        ghi = max(0.0, float(radiation))
        coefficient, cooling_cap = self._local_air_parameters(
            shadow_type,
            cooling_coefficient=cooling_coefficient,
            max_cooling=max_cooling,
        )
        radiacion_evitada = ghi * np.clip(1.0 - tau, 0.0, 1.0)
        delta_t = np.minimum(cooling_cap, coefficient * radiacion_evitada)
        local_air = float(air_temp) - delta_t
        local_air = np.asarray(local_air, dtype=np.float32)
        local_air[np.isnan(sombra)] = np.nan
        return local_air

    def estimate_local_air_temperature(
        self,
        air_temp,
        porcentaje_sombra,
        radiation,
        shadow_type="tree",
        full_shadow_transmittance=None,
        cooling_coefficient=None,
        max_cooling=None,
        transmittance_override=None,
    ):
        """Versión escalar de :meth:`estimate_local_air_temperature_map`."""
        result = self.estimate_local_air_temperature_map(
            air_temp,
            np.asarray([float(porcentaje_sombra)], dtype=np.float32),
            radiation,
            shadow_type=shadow_type,
            full_shadow_transmittance=full_shadow_transmittance,
            cooling_coefficient=cooling_coefficient,
            max_cooling=max_cooling,
            transmittance_map_override=(
                None if transmittance_override is None
                else np.asarray([float(transmittance_override)], dtype=np.float32)
            ),
        )
        return float(result[0])

    @staticmethod
    def _date_time(date_value=None, time_value=None):
        if isinstance(date_value, datetime.date):
            day_of_year = date_value.timetuple().tm_yday
        else:
            day_of_year = datetime.datetime.now().timetuple().tm_yday
        if time_value is None:
            now = datetime.datetime.now()
            time_of_day = now.hour + now.minute / 60.0 + now.second / 3600.0
        else:
            time_of_day = float(time_value)
        return day_of_year, time_of_day

    def calculate_tmrt_map(
        self,
        air_temp,
        porcentaje_sombra_map,
        shadow_type="tree",
        date_value=None,
        time_value=None,
        radiation_override=None,
        solar_altitude_override=None,
        full_shadow_transmittance=None,
        dni_override=None,
        dhi_override=None,
        model_mode=None,
        transmittance_map_override=None,
    ):
        porcentaje_sombra_map = np.asarray(porcentaje_sombra_map, dtype=np.float32)
        day_of_year, time_of_day = self._date_time(date_value, time_value)
        solar_altitude = (
            float(solar_altitude_override)
            if solar_altitude_override is not None
            else float(self.solar_altitude(day_of_year, time_of_day))
        )
        radiation = (
            max(0.0, float(radiation_override))
            if radiation_override is not None
            else self.clear_sky_radiation(solar_altitude)
        )

        if transmittance_map_override is not None:
            tau_map = np.asarray(transmittance_map_override, dtype=np.float32)
            if tau_map.shape != porcentaje_sombra_map.shape:
                raise ValueError("transmittance_map_override debe tener la misma forma que porcentaje_sombra_map.")
            tau_map = np.clip(tau_map, 0.0, 1.0)
        else:
            tau_map = self.shadow_transmittance_map(
                porcentaje_sombra_map,
                shadow_type,
                full_shadow_transmittance=full_shadow_transmittance,
            )
        selected_model = self._normalize_model_mode(model_mode or self.model_mode)

        if radiation <= 0.0:
            tmrt_map = np.full_like(porcentaje_sombra_map, float(air_temp), dtype=np.float32)
            advanced = None
        elif selected_model == self.MODEL_ADVANCED:
            advanced = calculate_radiative_tmrt(
                air_temp,
                tau_map,
                radiation,
                solar_altitude,
                dni=dni_override,
                dhi=dhi_override,
                config=self.advanced_config,
            )
            tmrt_map = np.asarray(advanced["tmrt_c"], dtype=np.float32)
        else:
            advanced = None
            tmrt_map = float(air_temp) + self.k_factor * radiation * tau_map

        tmrt_map = np.asarray(tmrt_map, dtype=np.float32)
        tmrt_map[np.isnan(porcentaje_sombra_map)] = np.nan
        result = {
            "Tmrt_map": tmrt_map,
            "Radiacion_Wm2": round(radiation, 2),
            "Solar_altitude": round(solar_altitude, 2),
            "Modelo_Tmrt": selected_model,
            "Modelo_Tmrt_label": (
                "Avanzado · balance radiativo v1"
                if selected_model == self.MODEL_ADVANCED
                else "Estándar · empírico calibrable"
            ),
        }
        if advanced is not None:
            result.update({
                "DNI_Wm2": round(float(advanced["dni"]), 2),
                "DHI_Wm2": round(float(advanced["dhi"]), 2),
                "Longwave_equivalent_Wm2": round(float(advanced["longwave_equivalent"]), 2),
            })
        return result

    def calculate_tmrt(
        self,
        air_temp,
        porcentaje_sombra,
        shadow_type="tree",
        date_value=None,
        time_value=None,
        radiation_override=None,
        solar_altitude_override=None,
        full_shadow_transmittance=None,
        dni_override=None,
        dhi_override=None,
        model_mode=None,
        transmittance_override=None,
    ):
        """Calcula Tmrt al sol y en sombra con el modelo seleccionado.

        ``standard`` conserva exactamente el modelo empírico histórico.
        ``advanced`` usa un balance radiativo humano simplificado con
        GHI/DNI/DHI y parámetros físicamente interpretables.
        """
        air_temp = float(air_temp)
        day_of_year, time_of_day = self._date_time(date_value, time_value)
        solar_altitude = (
            float(solar_altitude_override)
            if solar_altitude_override is not None
            else float(self.solar_altitude(day_of_year, time_of_day))
        )
        radiation = (
            max(0.0, float(radiation_override))
            if radiation_override is not None
            else self.clear_sky_radiation(solar_altitude)
        )
        tau = (
            float(np.clip(float(transmittance_override), 0.0, 1.0))
            if transmittance_override is not None
            else self.shadow_transmittance(
                porcentaje_sombra,
                shadow_type,
                full_shadow_transmittance=full_shadow_transmittance,
            )
        )
        selected_model = self._normalize_model_mode(model_mode or self.model_mode)

        if radiation <= 0.0:
            tmrt_sol = tmrt_sombra = air_temp
            advanced_sol = advanced_sombra = None
        elif selected_model == self.MODEL_ADVANCED:
            advanced_sol = calculate_radiative_tmrt(
                air_temp, 1.0, radiation, solar_altitude,
                dni=dni_override, dhi=dhi_override, config=self.advanced_config,
            )
            advanced_sombra = calculate_radiative_tmrt(
                air_temp, tau, radiation, solar_altitude,
                dni=dni_override, dhi=dhi_override, config=self.advanced_config,
            )
            tmrt_sol = float(advanced_sol["tmrt_c"])
            tmrt_sombra = float(advanced_sombra["tmrt_c"])
        else:
            advanced_sol = advanced_sombra = None
            tmrt_sol = air_temp + self.k_factor * radiation
            tmrt_sombra = air_temp + self.k_factor * radiation * tau

        delta_tmrt = tmrt_sol - tmrt_sombra
        logger.debug(
            "TMRT[%s]: doy=%s hora=%.3f alt=%.2f GHI=%.2f tau=%.3f Ta=%.2f sol=%.2f sombra=%.2f",
            selected_model, day_of_year, time_of_day, solar_altitude, radiation, tau,
            air_temp, tmrt_sol, tmrt_sombra,
        )
        result = {
            "Tmrt_sol": round(tmrt_sol, 2),
            "Tmrt_sombra": round(tmrt_sombra, 2),
            "Delta_Tmrt": round(delta_tmrt, 2),
            "Radiacion_Wm2": round(radiation, 2),
            "Transmitancia_tau": round(tau, 4),
            "Modelo_Tmrt": selected_model,
            "Modelo_Tmrt_label": (
                "Avanzado · balance radiativo v1"
                if selected_model == self.MODEL_ADVANCED
                else "Estándar · empírico calibrable"
            ),
        }
        if advanced_sol is not None:
            result.update({
                "DNI_Wm2": round(float(advanced_sol["dni"]), 2),
                "DHI_Wm2": round(float(advanced_sol["dhi"]), 2),
                "K_sw_sol_Wm2": round(float(advanced_sol["shortwave_effective"]), 2),
                "K_sw_sombra_Wm2": round(float(advanced_sombra["shortwave_effective"]), 2),
                "Longwave_equivalent_Wm2": round(float(advanced_sol["longwave_equivalent"]), 2),
            })
        return result

    def temperature_in_shade(self, air_temp, porcentaje_sombra):
        return self.calculate_tmrt(air_temp, porcentaje_sombra)["Tmrt_sombra"]

    def calibrate_k_factor(self, tmrt_medido: float, air_temp: float, radiation: float) -> float:
        radiation = float(radiation)
        if radiation <= 0.0:
            raise ValueError("No se puede calibrar con radiación <= 0.")
        return (float(tmrt_medido) - float(air_temp)) / radiation


def _debug_tmrt_case():
    logging.basicConfig(level=logging.DEBUG)
    test_date = datetime.date(2026, 2, 7)
    calc = Temperatura(latitude=-34.6037, longitude=-58.3816, tz_offset_hours=-3)
    logger.debug("Caso de prueba: %s", calc.calculate_tmrt(34.0, 50.0, date_value=test_date, time_value=8))


if __name__ == "__main__":
    _debug_tmrt_case()
