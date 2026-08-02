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

    def calcular_porcentaje_sombra(self, area_gris, area_referencia):
        """FIX: la versión anterior dividía directo por (max_val - min_val)
        sin ninguna guardia. Si el área analizada era uniforme o la
        referencia estaba mal elegida, eso producía una división por cero
        (o casi cero), y además el resultado podía quedar fuera de [0, 100]
        sin ningún clip. Ahora:
          - si no hay contraste suficiente, se devuelve 0.0 explícitamente
            en vez de dividir por (casi) cero.
          - el resultado siempre queda clippeado a [0, 100].
        """
        min_val = float(np.min(area_gris))
        max_val = float(np.median(area_referencia)) if area_referencia is not None \
            else float(np.max(area_gris))

        rango = max_val - min_val
        if rango <= 1e-6:
            return 0.0

        sombra_normalizada = (area_gris.astype(np.float64) - min_val) / rango
        sombra_normalizada = np.clip(sombra_normalizada, 0.0, 1.0)
        return float(100 - np.mean(sombra_normalizada) * 100)
