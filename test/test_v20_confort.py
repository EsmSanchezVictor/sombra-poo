import numpy as np
import pytest

from core import thermal_comfort as tc
from core.scenario import mapa_estres
from image_processor import (
    DEFAULT_MATRIX_SIZE,
    MATRIX_SIZE_MAX,
    MATRIX_SIZE_MIN,
    MATRIX_SIZE_OPTIONS,
    MATRIX_SIZE_STEP,
    normalize_matrix_size,
)


class _FakeUTCIResult:
    def __init__(self, values):
        self.utci = values


def test_resoluciones_v20_rango_y_default():
    assert DEFAULT_MATRIX_SIZE == 128
    assert MATRIX_SIZE_MIN == 64
    assert MATRIX_SIZE_MAX == 640
    assert MATRIX_SIZE_STEP == 32
    assert MATRIX_SIZE_OPTIONS[0] == 64
    assert MATRIX_SIZE_OPTIONS[-1] == 640
    assert 128 in MATRIX_SIZE_OPTIONS
    assert all((b - a) == 32 for a, b in zip(MATRIX_SIZE_OPTIONS, MATRIX_SIZE_OPTIONS[1:]))


def test_normalize_matrix_size_limita_y_aproxima():
    assert normalize_matrix_size(10) == 64
    assert normalize_matrix_size(999) == 640
    assert normalize_matrix_size(128) == 128
    assert normalize_matrix_size(130) == 128
    assert normalize_matrix_size(145) == 160
    assert normalize_matrix_size(None) == 128


def test_utci_array_hace_una_sola_llamada_vectorizada(monkeypatch):
    llamadas = []

    def fake_utci(*, tdb, tr, v, rh):
        arr = np.asarray(tr, dtype=np.float32)
        llamadas.append(arr.shape)
        # Devuelve algo que conserva forma y permite verificar resultado.
        return _FakeUTCIResult(arr + np.float32(1.5))

    monkeypatch.setattr(tc, "_utci_pkg", fake_utci)
    mapa = np.arange(16, dtype=np.float32).reshape(4, 4) + 20.0
    out = tc.utci_array(25.0, mapa, 1.0, 60.0)

    assert llamadas == [(4, 4)]
    assert out.shape == mapa.shape
    assert out.dtype == np.float32
    assert np.allclose(out, mapa + 1.5)


def test_mapa_estres_utci_clasifica_vectorizado(monkeypatch):
    llamadas = []

    def fake_utci(*, tdb, tr, v, rh):
        arr = np.asarray(tr, dtype=np.float32)
        llamadas.append(arr.shape)
        # Usamos Tmrt como UTCI sintético para probar solo clasificación.
        return _FakeUTCIResult(arr)

    monkeypatch.setattr(tc, "_utci_pkg", fake_utci)

    # Como core.scenario importó la función utci_array, esta sigue leyendo
    # tc._utci_pkg al ejecutarse; no hay una llamada escalar por píxel.
    mapa = np.array([[20.0, 28.0], [34.0, 48.0]], dtype=np.float32)
    res = mapa_estres(mapa, ta=25.0, rh=60.0, indice="utci", v_ms=1.0)

    assert llamadas == [(4,)]
    assert res["n_pixeles"] == 4
    assert res["por_area"] == {
        "Sin estrés térmico": 25.0,
        "Estrés de calor moderado": 25.0,
        "Estrés de calor fuerte": 25.0,
        "Estrés de calor extremo": 25.0,
    }


def test_utci_array_sin_dependencia_devuelve_none(monkeypatch):
    monkeypatch.setattr(tc, "_utci_pkg", None)
    assert tc.utci_array(25.0, np.ones((2, 2), dtype=np.float32), 1.0, 60.0) is None
