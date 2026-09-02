import numpy as np
from image_processor import ImageProcessor


def test_uniform_area_returns_zero():
    assert ImageProcessor().calcular_porcentaje_sombra(np.full((4, 4), 50), None) == 0.0


def test_reference_cannot_produce_out_of_range_percentage():
    area = np.array([[10, 100], [200, 250]], dtype=np.uint8)
    result = ImageProcessor().calcular_porcentaje_sombra(area, np.full((2, 2), 50))
    assert 0 <= result <= 100


def test_invalid_black_pixels_are_ignored_by_mask():
    proc = ImageProcessor()
    area = np.array([
        [0, 0, 0, 0],
        [0, 80, 90, 0],
        [0, 100, 110, 0],
        [0, 0, 0, 0],
    ], dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1:3, 1:3] = True
    ref = np.full((4, 4), 180, dtype=np.uint8)
    ref_mask = np.ones((4, 4), dtype=bool)

    con_mascara = proc.calcular_indice_sombra(area, ref, mask, ref_mask)
    solo_crop = proc.calcular_indice_sombra(area[1:3, 1:3], ref[1:3, 1:3])
    assert con_mascara == pytest.approx(solo_crop, abs=1e-6)


def test_map_outside_mask_is_nan():
    proc = ImageProcessor()
    area = np.arange(16, dtype=np.uint8).reshape(4, 4) * 10
    mask = np.zeros((4, 4), dtype=bool)
    mask[1:3, 1:3] = True
    mapa = proc.calcular_mapa_sombra(area, np.full((4, 4), 200), mascara_area=mask)
    assert np.isnan(mapa[0, 0])
    assert np.isfinite(mapa[1, 1])


# pytest se importa al final para mantener los imports de producción mínimos.
import pytest


def test_photo_analysis_separates_coverage_and_attenuation():
    proc = ImageProcessor()
    # Mitad iluminada como referencia (200), mitad sombra con 50% de transmisión (100).
    area = np.array([
        [200, 200, 100, 100],
        [200, 200, 100, 100],
    ], dtype=np.uint8)
    ref = np.full((2, 4), 200, dtype=np.uint8)
    result = proc.analizar_sombra_fotografica(area, ref)

    assert result["coverage_pct"] == pytest.approx(50.0, abs=1.0)
    assert result["shadow_transmittance"] == pytest.approx(0.5, abs=0.03)
    assert result["attenuation_pct"] == pytest.approx(50.0, abs=3.0)
    assert result["effective_transmittance"] == pytest.approx(0.75, abs=0.03)


def test_photo_analysis_all_sun_has_zero_coverage():
    proc = ImageProcessor()
    area = np.full((8, 8), 200, dtype=np.uint8)
    ref = np.full((8, 8), 200, dtype=np.uint8)
    result = proc.analizar_sombra_fotografica(area, ref)
    assert result["coverage_pct"] == pytest.approx(0.0)
    assert result["attenuation_pct"] == pytest.approx(0.0)
    assert result["effective_transmittance"] == pytest.approx(1.0)


def test_photo_analysis_all_shadow_preserves_optical_attenuation():
    proc = ImageProcessor()
    area = np.full((8, 8), 100, dtype=np.uint8)
    ref = np.full((8, 8), 200, dtype=np.uint8)
    result = proc.analizar_sombra_fotografica(area, ref)
    assert result["coverage_pct"] == pytest.approx(100.0)
    assert result["shadow_transmittance"] == pytest.approx(0.5, abs=0.01)
    assert result["attenuation_pct"] == pytest.approx(50.0, abs=1.0)


def test_photo_analysis_mask_ignores_invalid_black_border():
    proc = ImageProcessor()
    area = np.array([
        [0, 0, 0, 0],
        [0, 200, 100, 0],
        [0, 200, 100, 0],
        [0, 0, 0, 0],
    ], dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1:3, 1:3] = True
    ref = np.full((4, 4), 200, dtype=np.uint8)
    result = proc.analizar_sombra_fotografica(area, ref, mascara_area=mask)
    assert result["coverage_pct"] == pytest.approx(50.0, abs=1.0)
    assert np.isnan(result["shadow_mask"][0, 0])
