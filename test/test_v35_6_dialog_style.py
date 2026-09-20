import inspect

import diseno
import modelo_con_excel as modelo
from ui import dialogs
from ui import modal_style


def test_editors_use_common_dialog_language():
    src_d = inspect.getsource(diseno.mostrar_dialogo_edicion)
    src_m = inspect.getsource(modelo.editar_elemento)
    assert "Editar árbol" in src_d and "Editar estructura" in src_d
    assert "DialogPrimary.TButton" in src_d
    assert "prepare_dialog" in src_m
    assert "DialogPrimary.TButton" in src_m


def test_project_name_uses_styled_prompt():
    src = inspect.getsource(dialogs.ask_project_name)
    assert "ask_text" in src
    assert "simpledialog.askstring" not in src


def test_common_modal_helpers_exist():
    assert callable(modal_style.prepare_dialog)
    assert callable(modal_style.dialog_container)
    assert callable(modal_style.dialog_header)
    assert callable(modal_style.ask_text)
    assert callable(modal_style.ask_password_pair)
