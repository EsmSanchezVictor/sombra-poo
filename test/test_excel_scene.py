import pandas as pd
import pytest

from core.excel_scene import (
    TREE_COLUMNS, STRUCTURE_COLUMNS, load_scene_excel, save_scene_excel,
    apply_parameters_to_vars,
)
from modelo_con_excel import Arbol, Estructura


class Var:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


def base_vars():
    return {
        'T_amb_base': Var(298.15),
        'I_sol_base': Var(950.0),
        'T_min': Var(291.15),
        'T_max': Var(307.15),
        'dia': Var(62),
        'lat': Var(-34.6037),
        'lon': Var(-58.3816),
        'hora': Var(12.0),
        'humedad': Var(45.0),
        'viento': Var('moderado'),
        'timezone': Var('America/Argentina/Buenos_Aires'),
    }


def test_excel_v2_escribe_encabezados_aunque_no_haya_estructuras(tmp_path):
    path = tmp_path / 'sin_estructuras.xlsx'
    arbol = Arbol(10, 20, 8, 0.8, 3)
    save_scene_excel(path, [arbol], [], base_vars(), calculation_mode='advanced', origin='edicion')

    estructura = pd.read_excel(path, sheet_name='Estructuras')
    assert list(estructura.columns) == STRUCTURE_COLUMNS
    assert estructura.empty

    arboles = pd.read_excel(path, sheet_name='Árboles')
    assert list(arboles.columns) == TREE_COLUMNS
    assert len(arboles) == 1


def test_excel_v2_roundtrip_geometria_y_parametros(tmp_path):
    path = tmp_path / 'escena.xlsx'
    arbol = Arbol(10, 20, 8, 0.8, 3)
    arbol.especie = 'Jacarandá'
    pared = Estructura('Pared', 0, 10, 20, 0, altura=4, opacidad=0.9, material='Hormigón')
    vars_in = base_vars()

    save_scene_excel(path, [arbol], [pared], vars_in, calculation_mode='advanced', origin='edicion')
    libro = load_scene_excel(path)

    assert len(libro.arboles) == 1
    assert libro.arboles.iloc[0]['Especie'] == 'Jacarandá'
    assert len(libro.estructuras) == 1
    assert libro.estructuras.iloc[0]['X_inicial'] == pytest.approx(0)
    assert libro.estructuras.iloc[0]['Y_inicial'] == pytest.approx(10)
    assert libro.estructuras.iloc[0]['X_final'] == pytest.approx(20)
    assert libro.estructuras.iloc[0]['Y_final'] == pytest.approx(0)
    assert libro.parametros['timezone'] == 'America/Argentina/Buenos_Aires'
    assert float(libro.parametros['hora_local']) == pytest.approx(12.0)
    assert str(libro.parametros['modo_calculo']) == 'advanced'

    vars_out = base_vars()
    vars_out['hora'].set(7.0)
    vars_out['lat'].set(1.0)
    apply_parameters_to_vars(vars_out, libro.parametros)
    assert vars_out['hora'].get() == pytest.approx(12.0)
    assert vars_out['lat'].get() == pytest.approx(-34.6037)


def test_lector_acepta_hoja_estructuras_vacia_de_version_antigua(tmp_path):
    path = tmp_path / 'antiguo.xlsx'
    arboles = pd.DataFrame([{
        'X': 1, 'Y': 2, 'Altura (m)': 5,
        'Densidad_copa (0-1)': 0.7, 'Radio_copa (m)': 2,
    }])
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        arboles.to_excel(writer, sheet_name='Árboles', index=False)
        # Reproduce el bug histórico: DataFrame vacío sin columnas.
        pd.DataFrame([]).to_excel(writer, sheet_name='Estructuras', index=False)

    libro = load_scene_excel(path)
    assert len(libro.arboles) == 1
    assert libro.estructuras.empty
    assert list(libro.estructuras.columns) == STRUCTURE_COLUMNS
    assert libro.parametros == {}


def test_lector_acepta_archivo_sin_hoja_estructuras(tmp_path):
    path = tmp_path / 'solo_arboles.xlsx'
    pd.DataFrame([{
        'X': 1, 'Y': 2, 'Altura (m)': 5,
        'Densidad_copa (0-1)': 0.7, 'Radio_copa (m)': 2,
    }]).to_excel(path, sheet_name='Árboles', index=False)
    libro = load_scene_excel(path)
    assert len(libro.arboles) == 1
    assert libro.estructuras.empty
