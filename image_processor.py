import cv2
import numpy as np


class ImageProcessor:

    def load_image(self, file_path):
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError("No se pudo leer la imagen seleccionada.")
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except cv2.error as exc:
            raise ValueError("El archivo seleccionado no es una imagen válida.") from exc
        return img, img_rgb

    def convertir_a_grises(self, area, matriz_size):
        area_gris = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY)
        area_gris_resized = cv2.resize(area_gris, (matriz_size, matriz_size))
        return area_gris_resized

    def calcular_porcentaje_sombra(self, area_gris, area_referencia=None):
        """
        Calcula qué porcentaje del área analizada está en sombra.

        CAMBIOS respecto a la versión original:
        - Se evita la división por cero: si `max_val - min_val` es ~0
          (superficie perfectamente uniforme, o area_referencia con un
          solo tono), se retorna 0.0 en vez de crashear o devolver NaN/inf.
        - El resultado se recorta (clip) a [0, 100]. En la versión original
          era matemáticamente posible obtener valores fuera de ese rango
          si area_referencia tenía píxeles más oscuros que area_gris.
        - Se castea a float32 antes de restar para evitar overflow/underflow
          silencioso típico de operar directo sobre arrays uint8.
        """
        min_val = float(np.min(area_gris))
        if area_referencia is not None and area_referencia.size > 0:
            max_val = float(np.median(area_referencia))
        else:
            max_val = float(np.max(area_gris))

        rango = max_val - min_val
        if rango <= 1e-6:
            # No hay contraste suficiente para afirmar que hay sombra.
            return 0.0

        sombra_normalizada = (area_gris.astype(np.float32) - min_val) / rango
        porcentaje = 100 - np.mean(sombra_normalizada) * 100
        return float(np.clip(porcentaje, 0, 100))

    def calcular_mapa_sombra(self, area_gris, area_referencia=None):
        """NUEVO: versión "mapa" de calcular_porcentaje_sombra — misma
        normalización, pero sin promediar al final. Devuelve un array del
        mismo tamaño que area_gris con el % de sombra LOCAL de cada
        píxel (0-100). Se usa para que las curvas de nivel puedan
        mostrar temperatura calculada punto por punto en vez de un único
        valor agregado para toda el área.
        """
        min_val = float(np.min(area_gris))
        if area_referencia is not None and area_referencia.size > 0:
            max_val = float(np.median(area_referencia))
        else:
            max_val = float(np.max(area_gris))

        rango = max_val - min_val
        if rango <= 1e-6:
            return np.zeros_like(area_gris, dtype=np.float32)

        sombra_normalizada = (area_gris.astype(np.float32) - min_val) / rango
        mapa = 100 - sombra_normalizada * 100
        return np.clip(mapa, 0, 100)
