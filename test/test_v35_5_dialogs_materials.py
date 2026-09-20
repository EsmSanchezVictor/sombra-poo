import unicodedata

import diseno
from modelo_con_excel import (
    MATERIAL_CHOICES,
    MATERIALES_LOWER,
    material_display_name,
    materiales,
)


def _norm(text):
    raw = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).casefold()


def test_material_catalog_visible_is_unique_and_legacy_alias_is_preserved():
    assert len(MATERIAL_CHOICES) == len({_norm(x) for x in MATERIAL_CHOICES})
    assert "concreto translucido" not in materiales
    assert MATERIALES_LOWER["concreto translucido"] is materiales["Concreto Translúcido"]
    assert material_display_name("concreto translucido") == "Concreto Translúcido"


def test_material_catalog_keeps_distinct_polycarbonate_variants():
    assert "Policarbonato" in MATERIAL_CHOICES
    assert "Policarbonato (paneles)" in MATERIAL_CHOICES


def test_single_dialog_guard_reuses_existing_window(monkeypatch):
    created = []

    class FakeTop:
        def __init__(self, *_args, **_kwargs):
            self.exists = True
            created.append(self)
        def winfo_exists(self): return self.exists
        def deiconify(self): pass
        def lift(self): pass
        def focus_force(self): pass
        def title(self, _v): pass
        def resizable(self, *_v): pass
        def transient(self, *_v): pass
        def protocol(self, *_v): pass
        def bind(self, *_v): pass
        def after_idle(self, *_v): pass
        def grab_set(self): pass
        def grab_release(self): pass
        def destroy(self): self.exists = False

    monkeypatch.setattr(diseno.tk, "Toplevel", FakeTop)

    class App:
        root = None

    app = App()
    first, close_first = diseno._crear_dialogo_unico(app, "_dialogo_arbol", "Nuevo Árbol")
    second, close_second = diseno._crear_dialogo_unico(app, "_dialogo_arbol", "Nuevo Árbol")

    assert first is created[0]
    assert second is None and close_second is None
    assert len(created) == 1

    close_first()
    third, _ = diseno._crear_dialogo_unico(app, "_dialogo_arbol", "Nuevo Árbol")
    assert third is created[1]
    assert len(created) == 2
