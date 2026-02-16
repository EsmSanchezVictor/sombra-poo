import cv2
import numpy as np

class DetectorSombras:
    def procesar_automatico(self, ruta_imagen):
        img = cv2.imread(ruta_imagen)
        # Convertimos a espacio de color LAB para separar luz de color
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab)

        # Suavizamos para no detectar sombras diminutas (pasto, piedritas)
        blurred = cv2.GaussianBlur(l_channel, (5, 5), 0)

        # Aplicamos el umbral inteligente de Otsu
        _, mascara = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        return mascara