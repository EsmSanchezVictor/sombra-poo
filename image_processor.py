import cv2
import numpy as np


class ImageProcessor:
    """Procesamiento fotográfico para el índice de sombra.

    IMPORTANTE: el resultado derivado de intensidad de gris se interpreta como
    un **índice fotográfico de sombra/oscuridad relativa**, no como una medición
    radiométrica certificada de porcentaje geométrico de área sombreada. La
    exposición, el color del material y los reflejos pueden afectar el valor.
    """

    def load_image_rgb(self, file_path):
        """Carga una sola copia RGB de la fotografía.

        OpenCV decodifica inicialmente en BGR. La conversión RGB crea otro
        buffer; por eso la aplicación v18 no conserva ambos. El BGR queda
        como temporal local y se libera al retornar. En una foto de 12 MP
        esto evita retener ~36 MB adicionales de RAM.
        """
        img_bgr = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("No se pudo leer la imagen seleccionada.")
        try:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        except cv2.error as exc:
            raise ValueError("El archivo seleccionado no es una imagen válida.") from exc
        return img_rgb

    def load_image(self, file_path):
        """API legacy: devuelve BGR+RGB.

        Se mantiene para compatibilidad externa, pero la GUI v18 usa
        :meth:`load_image_rgb` para no conservar dos copias de la foto.
        """
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("No se pudo leer la imagen seleccionada.")
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except cv2.error as exc:
            raise ValueError("El archivo seleccionado no es una imagen válida.") from exc
        return img, img_rgb

    def convertir_a_grises(self, area, matriz_size):
        area_gris = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY)
        return cv2.resize(area_gris, (matriz_size, matriz_size), interpolation=cv2.INTER_AREA)

    def convertir_a_grises_con_mascara(self, area, mascara, matriz_size):
        """Convierte/cambia tamaño preservando qué píxeles son válidos.

        La máscara se redimensiona con vecino más próximo para evitar crear
        píxeles válidos artificiales en los bordes de círculos/polígonos.
        """
        gris = self.convertir_a_grises(area, matriz_size)
        if mascara is None:
            return gris, np.ones(gris.shape, dtype=bool)
        mask_u8 = (np.asarray(mascara, dtype=np.uint8) > 0).astype(np.uint8)
        mask_r = cv2.resize(
            mask_u8,
            (matriz_size, matriz_size),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)
        return gris, mask_r

    @staticmethod
    def _validos(array, mascara=None):
        arr = np.asarray(array, dtype=np.float32)
        valid = np.isfinite(arr)
        if mascara is not None:
            m = np.asarray(mascara, dtype=bool)
            if m.shape != arr.shape:
                raise ValueError("La máscara debe tener la misma forma que el área.")
            valid &= m
        return arr, valid

    def media_valida(self, area, mascara=None):
        arr, valid = self._validos(area, mascara)
        if not np.any(valid):
            return float("nan")
        return float(np.mean(arr[valid]))

    def _extremos_normalizacion(
        self,
        area_gris,
        area_referencia=None,
        mascara_area=None,
        mascara_referencia=None,
    ):
        area, valid = self._validos(area_gris, mascara_area)
        if not np.any(valid):
            raise ValueError("El área de cálculo no contiene píxeles válidos.")
        valores = area[valid]

        # El mínimo absoluto es extremadamente sensible a un único píxel
        # negro. Se usa percentil 2 como extremo oscuro robusto.
        min_val = float(np.percentile(valores, 2.0))

        if area_referencia is not None and np.asarray(area_referencia).size > 0:
            ref, valid_ref = self._validos(area_referencia, mascara_referencia)
            if np.any(valid_ref):
                max_val = float(np.median(ref[valid_ref]))
            else:
                max_val = float(np.percentile(valores, 98.0))
        else:
            max_val = float(np.percentile(valores, 98.0))

        return min_val, max_val, area, valid

    def calcular_indice_sombra(
        self,
        area_gris,
        area_referencia=None,
        mascara_area=None,
        mascara_referencia=None,
    ):
        """Índice fotográfico de sombra/oscuridad relativa, 0-100.

        0 representa intensidad similar a la referencia iluminada y 100 al
        extremo oscuro robusto del área. No debe interpretarse literalmente
        como fracción geométrica de superficie sombreada sin calibración.
        """
        min_val, max_val, area, valid = self._extremos_normalizacion(
            area_gris,
            area_referencia,
            mascara_area,
            mascara_referencia,
        )
        rango = max_val - min_val
        if rango <= 1e-6:
            return 0.0
        normalizada = (area[valid] - min_val) / rango
        indice = 100.0 - float(np.mean(normalizada)) * 100.0
        return float(np.clip(indice, 0.0, 100.0))

    def calcular_porcentaje_sombra(
        self,
        area_gris,
        area_referencia=None,
        mascara_area=None,
        mascara_referencia=None,
    ):
        """Alias compatible del índice fotográfico de sombra.

        Se conserva el nombre para no romper código/proyectos anteriores.
        La UI nueva lo rotula explícitamente como índice fotográfico.
        """
        return self.calcular_indice_sombra(
            area_gris,
            area_referencia,
            mascara_area,
            mascara_referencia,
        )

    def calcular_mapa_sombra(
        self,
        area_gris,
        area_referencia=None,
        mascara_area=None,
        mascara_referencia=None,
    ):
        """Mapa local 0-100 del mismo índice fotográfico.

        Los píxeles fuera de la máscara válida se devuelven como NaN para que
        no entren en estadísticas ni curvas de nivel.
        """
        min_val, max_val, area, valid = self._extremos_normalizacion(
            area_gris,
            area_referencia,
            mascara_area,
            mascara_referencia,
        )
        salida = np.full(area.shape, np.nan, dtype=np.float32)
        rango = max_val - min_val
        if rango <= 1e-6:
            salida[valid] = 0.0
            return salida
        normalizada = (area[valid] - min_val) / rango
        salida[valid] = np.clip(100.0 - normalizada * 100.0, 0.0, 100.0)
        return salida
    @staticmethod
    def _otsu_threshold(values_uint8):
        values = np.asarray(values_uint8, dtype=np.uint8).ravel()
        if values.size == 0:
            return 127
        hist = np.bincount(values, minlength=256).astype(np.float64)
        total = hist.sum()
        sum_total = float(np.dot(np.arange(256, dtype=np.float64), hist))
        sum_b = 0.0
        weight_b = 0.0
        best_var = -1.0
        best_t = 127
        for t in range(256):
            weight_b += hist[t]
            if weight_b <= 0:
                continue
            weight_f = total - weight_b
            if weight_f <= 0:
                break
            sum_b += t * hist[t]
            mean_b = sum_b / weight_b
            mean_f = (sum_total - sum_b) / weight_f
            between = weight_b * weight_f * (mean_b - mean_f) ** 2
            if between > best_var:
                best_var = between
                best_t = t
        return int(best_t)

    def analizar_sombra_fotografica(
        self,
        area_gris,
        area_referencia,
        mascara_area=None,
        mascara_referencia=None,
        threshold_ratio_bounds=(0.55, 0.92),
    ):
        """Separa cobertura geométrica e intensidad óptica de sombra.

        La referencia debe representar, idealmente, la misma superficie o una
        superficie comparable bajo iluminación directa. Los niveles de gris de
        una fotografía *no son irradiancia radiométrica*, por lo que la
        transmitancia obtenida es una estimación fotométrica relativa.

        Devuelve:
        - ``coverage_pct``: fracción de píxeles válidos clasificados como sombra.
        - ``attenuation_pct``: atenuación mediana dentro de los píxeles sombra.
        - ``shadow_transmittance``: transmitancia relativa mediana de la sombra.
        - ``effective_transmittance``: transmitancia media del área completa.
        - ``shadow_mask``: máscara booleana sombra/sol (NaN fuera de ROI).
        - ``local_transmittance_map``: transmitancia relativa local para Tmrt.

        La clasificación usa Otsu sobre la razón I/I_ref y restringe el umbral
        a un intervalo físicamente interpretable para evitar que ruido de una
        referencia casi uniforme genere falsas sombras. El umbral efectivo se
        registra siempre en el resultado para reproducibilidad.
        """
        if area_referencia is None or np.asarray(area_referencia).size == 0:
            raise ValueError(
                "Se necesita un área de referencia iluminada para separar cobertura e intensidad de sombra."
            )
        area, valid = self._validos(area_gris, mascara_area)
        ref, valid_ref = self._validos(area_referencia, mascara_referencia)
        if not np.any(valid):
            raise ValueError("El área de cálculo no contiene píxeles válidos.")
        if not np.any(valid_ref):
            raise ValueError("El área de referencia no contiene píxeles válidos.")

        ref_values = ref[valid_ref]
        ref_level = float(np.median(ref_values))
        if ref_level <= 1e-6:
            raise ValueError("El área de referencia es demasiado oscura para calibrar la sombra.")

        # Razón fotométrica relativa a la referencia. Valores >1 son posibles
        # por reflejos/exposición y se consideran iluminados (tau=1).
        ratio_map = np.full(area.shape, np.nan, dtype=np.float32)
        ratio_map[valid] = area[valid] / ref_level
        ratios = ratio_map[valid]
        finite_ratios = ratios[np.isfinite(ratios)]
        if finite_ratios.size == 0:
            raise ValueError("No hay datos fotográficos válidos para analizar.")

        lo, hi = map(float, threshold_ratio_bounds)
        if not (0.0 < lo < hi <= 1.0):
            raise ValueError("threshold_ratio_bounds debe cumplir 0 < mínimo < máximo <= 1.")

        median_ratio = float(np.median(finite_ratios))
        robust_spread = float(1.4826 * np.median(np.abs(finite_ratios - median_ratio)))

        # Otsu se aplica en una escala fija 0..1.20 para que el umbral sea
        # comparable entre fotografías. Se limita luego a [lo, hi].
        ratio_scale_max = 1.20
        scaled = np.clip(finite_ratios / ratio_scale_max, 0.0, 1.0)
        otsu_u8 = self._otsu_threshold(np.rint(scaled * 255.0).astype(np.uint8))
        threshold_ratio = (otsu_u8 / 255.0) * ratio_scale_max

        # Una referencia ruidosa exige más contraste para declarar sombra.
        ref_median = ref_level
        ref_mad = float(1.4826 * np.median(np.abs(ref_values - ref_median)))
        ref_noise_guard = 1.0 - min(0.25, 2.5 * ref_mad / max(ref_median, 1e-6))
        upper_effective = min(hi, max(lo, ref_noise_guard))
        threshold_ratio = float(np.clip(threshold_ratio, lo, upper_effective))

        # En áreas casi uniformes Otsu puede partir ruido sin significado.
        # Se resuelve como una clase única según su relación con la referencia.
        low_contrast = robust_spread < 0.025
        shadow_bool = np.zeros(area.shape, dtype=bool)
        if low_contrast:
            if median_ratio < threshold_ratio:
                shadow_bool[valid] = True
        else:
            shadow_bool[valid] = ratio_map[valid] <= threshold_ratio

        n_valid = int(np.count_nonzero(valid))
        n_shadow = int(np.count_nonzero(shadow_bool & valid))
        coverage = 100.0 * n_shadow / n_valid if n_valid else 0.0

        tau_map = np.full(area.shape, np.nan, dtype=np.float32)
        tau_map[valid] = 1.0
        if n_shadow:
            # La transmitancia local se limita para evitar que un píxel negro
            # aislado se convierta en radiación cero absoluta.
            local_tau_shadow = np.clip(ratio_map[shadow_bool], 0.05, 1.0)
            tau_map[shadow_bool] = local_tau_shadow
            tau_shadow = float(np.median(local_tau_shadow))
            attenuation = 100.0 * (1.0 - tau_shadow)
        else:
            tau_shadow = 1.0
            attenuation = 0.0

        effective_tau = float(np.mean(tau_map[valid]))
        effective_attenuation = 100.0 * (1.0 - effective_tau)

        shadow_mask_float = np.full(area.shape, np.nan, dtype=np.float32)
        shadow_mask_float[valid] = shadow_bool[valid].astype(np.float32)
        attenuation_map = np.full(area.shape, np.nan, dtype=np.float32)
        attenuation_map[valid] = 100.0 * (1.0 - tau_map[valid])

        return {
            "algorithm": "photo-shadow-v2-coverage-attenuation",
            "coverage_pct": float(np.clip(coverage, 0.0, 100.0)),
            "attenuation_pct": float(np.clip(attenuation, 0.0, 100.0)),
            "shadow_transmittance": float(np.clip(tau_shadow, 0.0, 1.0)),
            "effective_transmittance": float(np.clip(effective_tau, 0.0, 1.0)),
            "effective_attenuation_pct": float(np.clip(effective_attenuation, 0.0, 100.0)),
            "threshold_ratio": threshold_ratio,
            "threshold_gray": threshold_ratio * ref_level,
            "reference_gray": ref_level,
            "low_contrast": bool(low_contrast),
            "valid_pixels": n_valid,
            "shadow_pixels": n_shadow,
            "shadow_mask": shadow_mask_float,
            "local_transmittance_map": tau_map,
            "local_attenuation_map": attenuation_map,
            "ratio_map": ratio_map,
            # Compatibilidad/diagnóstico: índice continuo histórico.
            "legacy_shadow_index_pct": self.calcular_indice_sombra(
                area_gris, area_referencia, mascara_area, mascara_referencia
            ),
        }

    def calcular_cobertura_sombra(
        self, area_gris, area_referencia, mascara_area=None, mascara_referencia=None
    ):
        """Cobertura de sombra (%) según clasificación fotográfica v2."""
        return self.analizar_sombra_fotografica(
            area_gris, area_referencia, mascara_area, mascara_referencia
        )["coverage_pct"]

    def calcular_atenuacion_sombra(
        self, area_gris, area_referencia, mascara_area=None, mascara_referencia=None
    ):
        """Atenuación óptica relativa (%) dentro de la sombra clasificada."""
        return self.analizar_sombra_fotografica(
            area_gris, area_referencia, mascara_area, mascara_referencia
        )["attenuation_pct"]

