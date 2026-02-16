import cv2
import numpy as np

class ProcesadorSombras:
    def __init__(self):
        self.mascara_automatica = None

    def generar_mascara_automatica(self, ruta_imagen):
        # Tu código con una pequeña mejora de contraste
        img = cv2.imread(ruta_imagen)
        if img is None:
            return None
            
        # Convertimos a LAB para aislar la luminosidad (L) de los colores (A, B)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab)

        # Aplicamos un filtro para suavizar texturas (como el pasto) 
        # que a veces confunden a la IA
        l_blur = cv2.GaussianBlur(l_channel, (5, 5), 0)

        # 3. Umbral de Otsu
        _, mascara = cv2.threshold(l_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 4. Limpieza de ruido
        kernel = np.ones((5,5), np.uint8)
        self.mascara_automatica = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
        
        return self.mascara_automatica