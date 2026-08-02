import os
from abc import ABC, abstractmethod

import cv2
import numpy as np


class ShadowDetector(ABC):
    """Interfaz común para cualquier detector de sombra: clásico (Otsu) o
    basado en un modelo entrenado. Permite enchufar un modelo de IA más
    adelante sin tocar el resto de la app.
    """

    @abstractmethod
    def procesar_automatico(self, ruta_imagen):
        """Devuelve una máscara binaria (0/255), del mismo tamaño que la
        imagen de entrada, donde 255 = píxel en sombra."""
        raise NotImplementedError


class OtsuShadowDetector(ShadowDetector):
    """Detector clásico: umbral de Otsu sobre el canal L (luminosidad) del
    espacio de color Lab. Rápido y sin dependencias de ML, pero no distingue
    sombra de árbol de otras zonas oscuras (tierra húmeda, techos oscuros,
    sombra de nubes)."""

    def procesar_automatico(self, ruta_imagen):
        img = cv2.imread(ruta_imagen)
        if img is None:
            raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")

        # Convertimos a espacio de color LAB para separar luz de color
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab)

        # Suavizamos para no detectar sombras diminutas (pasto, piedritas)
        blurred = cv2.GaussianBlur(l_channel, (5, 5), 0)

        # Aplicamos el umbral inteligente de Otsu
        _, mascara = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return mascara


# Alias de compatibilidad: todo el código existente que hace
# `DetectorSombras()` sigue funcionando sin cambios.
DetectorSombras = OtsuShadowDetector


class MLShadowDetector(ShadowDetector):
    """Detector basado en un modelo entrenado (ONNX/TorchScript).

    Pensado para recibir pesos entrenados sobre las máscaras VIA que ya
    genera DatasetSaver.py (ver roadmap de IA para sombra de árboles:
    fine-tuning de un U-Net liviano, o bootstrap con SAM/Grounded-SAM para
    acelerar el etiquetado). Mientras no exista un modelo entrenado, usar
    OtsuShadowDetector.
    """

    def __init__(self, model_path):
        self.model_path = model_path
        self._modelo = None  # se carga de forma perezosa, recién al usarse

    def procesar_automatico(self, ruta_imagen):
        if self._modelo is None:
            if not os.path.exists(self.model_path):
                raise NotImplementedError(
                    f"No hay modelo entrenado en {self.model_path!r} todavía. "
                    "Usá OtsuShadowDetector mientras tanto, o entrená un "
                    "modelo con las máscaras que genera DatasetSaver.py."
                )
            self._modelo = self._cargar_modelo(self.model_path)
        return self._inferir(ruta_imagen)

    def _cargar_modelo(self, path):
        raise NotImplementedError(
            "Implementar carga de modelo ONNX/TorchScript (por ejemplo con "
            "onnxruntime.InferenceSession(path) o torch.jit.load(path))."
        )

    def _inferir(self, ruta_imagen):
        raise NotImplementedError(
            "Implementar preprocesamiento de la imagen + forward pass del "
            "modelo + postprocesamiento a máscara binaria 0/255."
        )
