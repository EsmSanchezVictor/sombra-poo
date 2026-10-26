"""Contrato actual del Panel 2; v26 reemplazó el relleno vertical de v25."""
from types import SimpleNamespace
from ui.app_ui import SombraApp
from ui import panels


class Var:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


def build_panel(monkeypatch):
    import ui.app_ui as module
    children=[]
    class Widget:
        def __init__(self,parent,**kwargs):
            self.parent=parent;self.options=kwargs;self.geometry=None;children.append(self)
        def pack(self,**kwargs):self.geometry=('pack',kwargs)
        def grid(self,**kwargs):self.geometry=('grid',kwargs)
        def config(self,**kwargs):self.options.update(kwargs)
    for name in ('Button','Checkbutton','Label'):monkeypatch.setattr(module.tk,name,Widget)
    monkeypatch.setattr(module.ttk,'Combobox',Widget)
    panel=SimpleNamespace(cget=lambda _: 'white')
    noop=lambda:None
    app=SimpleNamespace(panel_frames=[None,panel],panel2_advanced_mode=Var(False),shadow_detector_enabled=Var(False),
        matriz_size=Var(320),cargar_imagen=noop,shape_selector=SimpleNamespace(select_area_calculo=noop,select_area_referencia=noop),
        editar_exclusiones_fotograficas=noop,confirmar_seleccion=noop,mostrar_mascara_sombra=noop,mostrar_curvas_nivel=noop,save_dataset=noop)
    app._toggle_panel2_advanced=lambda:panels._toggle_panel2_advanced(app)
    SombraApp.setup_panel_2(app)
    return app,panel,children


def test_panel2_current_layout_has_no_mixed_geometry_managers(monkeypatch):
    app,panel,children=build_panel(monkeypatch)
    assert children and all(w.parent is panel for w in children)
    assert len({w.geometry[0] for w in children})==1
    for name in ('area_calc_button','area_ref_button','confirm_button','curve_button','save_dataset_button'):
        assert getattr(app,name).options['state']=='disabled'


def test_panel2_resolution_controls_respect_simple_and_advanced_modes(monkeypatch):
    app,_,_=build_panel(monkeypatch)
    assert app.matriz_size.get()==128 and app.matrix_size_combo.options['state']=='disabled'
    app.panel2_advanced_mode.set(True);app._toggle_panel2_advanced()
    assert app.matrix_size_combo.options['state']=='readonly'
