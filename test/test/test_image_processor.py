import numpy as np
from image_processor import ImageProcessor


def test_uniform_area_returns_zero():
    assert ImageProcessor().calcular_porcentaje_sombra(np.full((4, 4), 50), None) == 0.0


def test_reference_cannot_produce_out_of_range_percentage():
    area = np.array([[10, 100], [200, 250]], dtype=np.uint8)
    result = ImageProcessor().calcular_porcentaje_sombra(area, np.full((2, 2), 50))
    assert 0 <= result <= 100