"""Detección fotométrica opcional de candidatos oscuros, sin clasificación semántica."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover
    cv2 = None


@dataclass
class ShadowParams:
    block_size: int = 31
    c: int = 8
    blur_kernel: int = 3
    threshold: int = 110


class ShadowDetector:
    def __init__(self, prefer_opencv: bool = True):
        self.prefer_opencv = prefer_opencv and cv2 is not None

    def detect_shadow_mask(self, image_path_or_pil: Any, method: str = "adaptive", params: ShadowParams | None = None):
        params = params or ShadowParams()
        gray = self._to_gray_array(image_path_or_pil)

        if self.prefer_opencv and method == "adaptive":
            blur = gray
            if params.blur_kernel and params.blur_kernel > 1:
                k = params.blur_kernel + (1 - params.blur_kernel % 2)
                blur = cv2.GaussianBlur(gray, (k, k), 0)
            block_size = params.block_size + (1 - params.block_size % 2)
            binary = cv2.adaptiveThreshold(
                blur,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                max(3, block_size),
                params.c,
            )
            return binary > 0

        thresh = self._otsu_threshold(gray) if method != "global" else params.threshold
        return gray <= thresh

    def compute_shadow_coverage(self, mask, roi_mask=None, *, exclusion_mask=None) -> dict:
        """Fracción 0..1 de candidatos oscuros dentro de la ROI válida.

        No estima precisión ni calidad térmica. Las exclusiones se anotan
        manualmente; el umbral RGB no identifica materiales ni objetos.
        """
        mask_bool = self._binary_mask(mask, "mask")
        roi = np.ones_like(mask_bool) if roi_mask is None else self._binary_mask(roi_mask, "roi_mask", mask_bool.shape)
        excluded = np.zeros_like(mask_bool) if exclusion_mask is None else self._binary_mask(exclusion_mask, "exclusion_mask", mask_bool.shape)
        excluded_count = int(np.count_nonzero(roi & excluded))
        roi = roi & ~excluded
        valid = int(roi.sum())
        dark = int(np.count_nonzero(mask_bool & roi))
        return {"coverage_fraction": float(dark / valid) if valid else None,
                "candidate_pixels": dark, "total_pixels": valid, "excluded_pixels": excluded_count,
                "status": "estimated" if valid else "no_valid_pixels",
                "interpretation": "dark_candidate_coverage", "units": "fraction",
                "semantic_discrimination": False,
                "warnings": ["La copa, el asfalto, el agua y otros materiales oscuros pueden confundirse con sombra; revise la ROI y las exclusiones."]}

    def compute_shadow_quality(self, mask, roi_mask=None) -> dict:
        """API histórica: shadow_quality siempre fue una cobertura, no calidad."""
        result = self.compute_shadow_coverage(mask, roi_mask)
        return {"shadow_quality": result["coverage_fraction"],
                "dark_pixels": result["candidate_pixels"], "total_pixels": result["total_pixels"]}

    @staticmethod
    def _binary_mask(mask, name, shape=None):
        arr = np.asarray(mask)
        if arr.ndim != 2 or (shape is not None and arr.shape != shape):
            raise ValueError(f"{name} debe ser una máscara 2D del mismo tamaño que la imagen.")
        if not np.issubdtype(arr.dtype, np.number) and arr.dtype != np.bool_:
            raise ValueError(f"{name} debe contener valores numéricos o booleanos.")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} no puede contener NaN o infinito.")
        return arr.astype(bool)

    def detect_shadow_candidates(self, image_path_or_pil, method="adaptive", params=None):
        """Candidatos por intensidad; requieren revisión antes de llamarlos sombra."""
        return self.detect_shadow_mask(image_path_or_pil, method=method, params=params)

    def _to_gray_array(self, image_path_or_pil):
        if isinstance(image_path_or_pil, Image.Image):
            img = image_path_or_pil
        elif isinstance(image_path_or_pil, str):
            # No dejar un decoder/descriptor PIL abierto durante sesiones largas.
            with Image.open(image_path_or_pil) as img:
                return np.asarray(img.convert("L"), dtype=np.uint8)
        else:
            arr = np.asarray(image_path_or_pil)
            if arr.ndim == 2:
                return arr.astype(np.uint8, copy=False)
            arr3 = np.ascontiguousarray(arr[..., :3], dtype=np.uint8)
            # np.mean(..., axis=2) promovía una foto completa a float64 y
            # podía crear ~96 MB temporales en 12 MP. OpenCV convierte
            # directamente uint8 -> uint8 sin ese buffer intermedio.
            if cv2 is not None:
                return cv2.cvtColor(arr3, cv2.COLOR_RGB2GRAY)
            return np.asarray(Image.fromarray(arr3, mode="RGB").convert("L"), dtype=np.uint8)
        return np.asarray(img.convert("L"), dtype=np.uint8)

    def _otsu_threshold(self, gray: np.ndarray) -> int:
        hist, _ = np.histogram(gray.ravel(), bins=256, range=(0, 256))
        total = gray.size
        sum_total = np.dot(np.arange(256), hist)
        sum_b = 0.0
        w_b = 0.0
        var_max = -1.0
        threshold = 127
        for t in range(256):
            w_b += hist[t]
            if w_b == 0:
                continue
            w_f = total - w_b
            if w_f == 0:
                break
            sum_b += t * hist[t]
            m_b = sum_b / w_b
            m_f = (sum_total - sum_b) / w_f
            var_between = w_b * w_f * (m_b - m_f) ** 2
            if var_between > var_max:
                var_max = var_between
                threshold = t
        return int(threshold)