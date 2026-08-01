"""Detectores intercambiables de sombra sobre imágenes."""

from abc import ABC, abstractmethod
from pathlib import Path
import cv2
import numpy as np

class ShadowDetector(ABC):
    @abstractmethod
    def procesar_automatico(self, ruta_imagen) -> np.ndarray:
        """Devuelve máscara 0/255 del tamaño de entrada; 255 indica sombra."""


class OtsuShadowDetector(ShadowDetector):
    """Baseline clásico basado en luminosidad Lab y umbral de Otsu."""

    def procesar_automatico(self, ruta_imagen) -> np.ndarray:
        img = cv2.imread(str(ruta_imagen))
        if img is None:
            raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab)

  
        blurred = cv2.GaussianBlur(l_channel, (5, 5), 0)
        _, mascara = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        return mascara


class MLShadowDetector(ShadowDetector):
    """Contrato futuro para modelos ONNX o TorchScript."""

    def __init__(self, ruta_modelo):
        self.ruta_modelo = Path(ruta_modelo)

    def procesar_automatico(self, ruta_imagen) -> np.ndarray:
        if not self.ruta_modelo.is_file():
            raise NotImplementedError(
                f"No existen pesos entrenados en '{self.ruta_modelo}'. "
                "Entrene/exporte un modelo ONNX o TorchScript antes de usar MLShadowDetector."
            )
        raise NotImplementedError("La inferencia ML se implementará al seleccionar la arquitectura final.")
        # Aplicamos el umbral inteligente de Otsu
        _, mascara = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        return mascara
# Alias público conservado para no romper integraciones existentes.
DetectorSombras = OtsuShadowDetector