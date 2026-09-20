from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from core.crown_shapes import CANOPY_SHAPES, DEFAULT_CANOPY_SHAPE, normalize_canopy_shape
from core.excel_scene import load_scene_excel, save_scene_excel
from core.scene_objects import adaptar_objetos_escena
from core.app_state import AppState
from modelo_con_excel import Arbol
from ui.canopy_rendering import draw_canopy_2d, draw_canopy_3d_mpl


def test_canopy_shape_catalog_and_aliases():
    assert CANOPY_SHAPES == (
        "Esférica", "Cónica", "Columnar", "Piramidal", "Extendida", "Irregular", "Llora"
    )
    assert normalize_canopy_shape("esferica") == "Esférica"
    assert normalize_canopy_shape("cónica") == "Cónica"
    assert normalize_canopy_shape("llorona") == "Llora"
    assert normalize_canopy_shape("desconocida") == DEFAULT_CANOPY_SHAPE


def test_arbol_shape_default_and_scene_adapter():
    arbol = Arbol(10, 20, 8, 0.8, 3)
    assert arbol.forma_copa == "Esférica"
    arbol.forma_copa = "Piramidal"
    arbol.especie = "Pino (Pinus sp.)"
    obj = adaptar_objetos_escena([arbol], [])[0]
    assert obj.forma_copa == "Piramidal"
    assert obj.especie == "Pino (Pinus sp.)"
    assert obj.rho_copa == 0.8


def test_excel_roundtrip_persists_canopy_shape(tmp_path: Path):
    trees = [
        Arbol(10, 20, 8, 0.8, 3, forma_copa="Cónica", especie="Pino (Pinus sp.)"),
        Arbol(30, 25, 7, 0.7, 4, forma_copa="Llora", especie=""),
    ]
    path = tmp_path / "scene.xlsx"
    save_scene_excel(path, trees, [], {}, calculation_mode="advanced", origin="test")
    book = load_scene_excel(path)
    assert list(book.arboles["Forma_copa"]) == ["Cónica", "Llora"]
    assert list(book.arboles["Especie"]) == ["Pino (Pinus sp.)", ""]


def test_legacy_excel_without_canopy_shape_defaults_to_spherical(tmp_path: Path):
    path = tmp_path / "legacy.xlsx"
    df = pd.DataFrame([{
        "X": 1, "Y": 2, "Altura (m)": 5,
        "Densidad_copa (0-1)": 0.8, "Radio_copa (m)": 2,
        "Especie": "",
    }])
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Árboles", index=False)
    book = load_scene_excel(path)
    assert book.arboles.iloc[0]["Forma_copa"] == "Esférica"



def test_project_scene_serialization_keeps_canopy_shape_and_species():
    state = AppState(SimpleNamespace())
    tree = Arbol(4, 5, 9, 0.75, 2.8, forma_copa="Extendida", especie="Pino (Pinus sp.)")
    obj = state._arbol_to_scene_obj(tree)
    payload = state.scene_object_to_dict(obj)
    assert payload["forma_copa"] == "Extendida"
    assert payload["especie"] == "Pino (Pinus sp.)"
    restored_obj = state.scene_object_from_dict(payload)
    restored = state._scene_obj_to_arbol(restored_obj)
    assert restored.forma_copa == "Extendida"
    assert restored.especie == "Pino (Pinus sp.)"

def test_all_canopy_shapes_render_in_2d_and_3d_matplotlib():
    fig2, ax2 = plt.subplots()
    fig3 = plt.figure()
    ax3 = fig3.add_subplot(111, projection="3d")
    try:
        for idx, shape in enumerate(CANOPY_SHAPES):
            tree = Arbol(idx * 4.0, 0.0, 8.0, 0.8, 2.0, forma_copa=shape)
            artists = draw_canopy_2d(ax2, tree)
            assert artists
            draw_canopy_3d_mpl(ax3, tree)
    finally:
        plt.close(fig2)
        plt.close(fig3)
