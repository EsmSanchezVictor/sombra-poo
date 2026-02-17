"""Detección opcional de sombras para fotos reales."""

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

    def compute_shadow_quality(self, mask, roi_mask=None) -> dict:
        mask_bool = np.asarray(mask).astype(bool)
        if roi_mask is None:
            roi = np.ones_like(mask_bool, dtype=bool)
        else:
            roi = np.asarray(roi_mask).astype(bool)
        valid = roi.sum()
        if valid == 0:
            return {"shadow_quality": 0.0, "dark_pixels": 0, "total_pixels": 0}
        dark = int(np.logical_and(mask_bool, roi).sum())
        quality = float(dark / valid)
        return {"shadow_quality": quality, "dark_pixels": dark, "total_pixels": int(valid)}

    def _to_gray_array(self, image_path_or_pil):
        if isinstance(image_path_or_pil, Image.Image):
            img = image_path_or_pil
        elif isinstance(image_path_or_pil, str):
            img = Image.open(image_path_or_pil)
        else:
            arr = np.asarray(image_path_or_pil)
            if arr.ndim == 2:
                return arr.astype(np.uint8)
            return np.mean(arr[..., :3], axis=2).astype(np.uint8)
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