import cv2
import numpy as np

class ImageProcessor:
    def load_image(self, file_path):
        img = cv2.imread(file_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img, img_rgb

    def convertir_a_grises(self, area, matriz_size):
        area_gris = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY)
        area_gris_resized = cv2.resize(area_gris, (matriz_size, matriz_size))
        return area_gris_resized

    def calcular_porcentaje_sombra(self, area_gris, area_referencia):
        min_val = np.min(area_gris)
        max_val = np.median(area_referencia) if area_referencia is not None else np.max(area_gris)
        sombra_normalizada = (area_gris - min_val) / (max_val - min_val)
        return 100-np.mean(sombra_normalizada) * 100
