import datetime
import math


class Temperatura:
    def __init__(self):
        # Inicializa la interfaz y variables...
        pass

    def solar_declination(self, day_of_year):
        return 23.45 * math.sin(math.radians((360/365) * (day_of_year - 81)))

    def solar_angle(self, latitude, day_of_year, time_of_day):
        declination = self.solar_declination(day_of_year)
        hour_angle = 15 * (time_of_day - 12)
        latitude_rad = math.radians(latitude)
        declination_rad = math.radians(declination)
        solar_altitude = math.degrees(math.asin(
            math.sin(latitude_rad) * math.sin(declination_rad) + 
            math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(math.radians(hour_angle))
        ))
        return max(solar_altitude, 0)

    def solar_radiation(self, latitude, day_of_year, time_of_day):
        angle = self.solar_angle(latitude, day_of_year, time_of_day)
        solar_constant = 1367
        albedo = 0.3
        radiation = solar_constant * math.sin(math.radians(angle)) * (1 - albedo)
        return radiation if radiation > 0 else 0

    def shadow_index(self, opacity, shadow_density):
        return opacity * shadow_density

    def temperature_in_shade(self, temp_ambient, latitude, longitude, date, time_of_day, opacity, shadow_density):
        day_of_year = date.timetuple().tm_yday
        R_solar = self.solar_radiation(latitude, day_of_year, time_of_day)
        
        # Calcular el índice de sombra (SSI)
        SSI = self.shadow_index(opacity, shadow_density)
        
        # Coeficiente basado en el SSI
        alpha = 0.5 + 0.5 * (1 - SSI)
        
        # Estimar la temperatura bajo la sombra
        temp_shade = temp_ambient - (alpha * (R_solar / 10))
        return max(temp_shade, temp_ambient - 10)

    