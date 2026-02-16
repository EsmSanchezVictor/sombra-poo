import pvlib
import pandas as pd

class MotorSolar:
    def __init__(self, lat, lon, tz='America/Argentina/Buenos_Aires'):
        self.lat = lat
        self.lon = lon
        self.tz = tz
        self.location = pvlib.location.Location(lat, lon, tz=tz)

    def obtener_posicion_y_radiacion(self, fecha_hora):
        # Aseguramos que la fecha tenga zona horaria
        fecha_dt = pd.to_datetime(fecha_hora).tz_localize(self.tz)
        
        sol = self.location.get_solarposition(fecha_dt)
        rad = self.location.get_clearsky(fecha_dt)
        
        return {
            'azimut': sol['azimuth'].values[0],
            'elevacion': sol['elevation'].values[0],
            'ghi': rad['ghi'].values[0] # Radiación total en W/m2
        }