from types import SimpleNamespace

import cv2
import matplotlib.pyplot as plt
import numpy as np

import diseno
from core.memory_utils import current_rss_mb
from image_processor import ImageProcessor
from services.shadow_detector import ShadowDetector
from shape_selection import ShapeSelector
from temp_graph import TemperatureGraph
from ui.app_ui import SombraApp


def test_rgb_loader_keeps_single_application_buffer(tmp_path):
    # Archivo BGR en disco; la API nueva devuelve solo RGB para la GUI.
    bgr = np.zeros((20, 30, 3), dtype=np.uint8)
    bgr[..., 2] = 255
    path = tmp_path / "foto.png"
    assert cv2.imwrite(str(path), bgr)
    rgb = ImageProcessor().load_image_rgb(str(path))
    assert rgb.shape == (20, 30, 3)
    assert rgb.dtype == np.uint8
    assert tuple(rgb[0, 0]) == (255, 0, 0)


def test_shadow_detector_gray_stays_uint8():
    rgb = np.zeros((120, 160, 3), dtype=np.uint8)
    rgb[..., 0] = 200
    gray = ShadowDetector()._to_gray_array(rgb)
    assert gray.shape == rgb.shape[:2]
    assert gray.dtype == np.uint8


def test_temperature_bar_does_not_register_pyplot_figure():
    before = tuple(plt.get_fignums())
    fig = TemperatureGraph(60.0, 45.0, None).build_figure()
    assert tuple(plt.get_fignums()) == before
    fig.clear()


def test_tmrt_contour_display_is_downsampled_but_data_remains_float32():
    full = np.arange(480 * 480, dtype=np.float32).reshape(480, 480)
    xs, ys, display, stride = SombraApp._contour_display_grid(full)
    assert stride == 2
    assert display.shape == (240, 240)
    assert display.dtype == np.float32
    assert xs[-1] == 478
    assert ys[-1] == 478
    # No modifica la matriz científica original.
    assert full.shape == (480, 480)


def test_design_initialization_renders_only_once(monkeypatch):
    calls = []
    sentinel = (object(), object(), object())

    def fake_update(vars_, frame_):
        calls.append((vars_, frame_))
        return sentinel

    monkeypatch.setattr(diseno, "actualizar_grafico", fake_update)
    frame = SimpleNamespace(grid=lambda **kwargs: None)
    vars_ = {}
    app = object()
    assert diseno.crear_area_grafico(vars_, frame, app) == sentinel
    assert len(calls) == 1
    assert vars_["_app_instance"] is app


def test_current_rss_probe_is_nonnegative_when_supported():
    rss = current_rss_mb()
    assert rss is None or rss > 0


def test_shape_selector_uses_rgb_buffer_after_bgr_removal():
    class DummyPatch:
        def set_xy(self, *_args):
            pass

    class DummyAx:
        def add_patch(self, *_args):
            pass

    class DummyCanvas:
        def draw(self):
            pass

    class DummyVar:
        def get(self):
            return "Polígono"

    app = SimpleNamespace(
        img_rgb=np.zeros((10, 10, 3), dtype=np.uint8),
        ax1=DummyAx(),
        canvas1=DummyCanvas(),
        drawing_mode="calculo",
        selection_type=DummyVar(),
    )
    selector = ShapeSelector(app)
    selector.selection_enabled = True
    event = SimpleNamespace(inaxes=app.ax1, xdata=2.0, ydata=3.0)
    selector.on_mouse_press(event)
    assert selector.polygon_points == [(2.0, 3.0)]
