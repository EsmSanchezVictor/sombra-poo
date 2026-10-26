"""Flujo del diálogo con widgets simulados y gráfico real Agg; no GUI visual."""
from datetime import date
from types import SimpleNamespace
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg
from test.test_stage3_2_tree_ranking import configured_app
from ui import dialogs
from ui import species_dialogs


def test_choose_scene_export_and_invalidate_stale_result(tmp_path,monkeypatch):
    widgets=[];variables=[]
    class Widget:
        def __init__(self,*args,**kwargs):self.options=kwargs;self.bindings={};self.content='';widgets.append(self)
        def pack(self,*a,**k):pass
        def config(self,**kwargs):self.options.update(kwargs)
        def bind(self,name,fn):self.bindings[name]=fn
        def delete(self,*args):self.content=''
        def insert(self,where,text):self.content+=text
        def title(self,*args):pass
        def geometry(self,*args):pass
        def destroy(self):self.bindings['<Destroy>'](SimpleNamespace(widget=self))
    class Variable:
        def __init__(self,*args,value):self.value=value;variables.append(self)
        def get(self):return self.value
        def set(self,value):self.value=value
    class Canvas(FigureCanvasAgg):
        def __init__(self,figure,master):super().__init__(figure);self.widget=Widget()
        def get_tk_widget(self):return self.widget
    for name in ('Toplevel','Frame','Label','Text','Button'):monkeypatch.setattr(dialogs.tk,name,Widget)
    monkeypatch.setattr(dialogs.ttk,'Combobox',Widget)
    monkeypatch.setattr(dialogs.tk,'StringVar',Variable)
    monkeypatch.setattr(species_dialogs,'FigureCanvasTkAgg',Canvas)
    monkeypatch.setattr(species_dialogs,'prepare_dialog',lambda *a,**k:None)
    f=tmp_path/'ranking.json';monkeypatch.setattr(dialogs.filedialog,'asksaveasfilename',lambda **k:str(f))
    obj=configured_app('advanced');obj.root=object()
    dialogs.HerramientasDialogs(obj)._dialogo_ranking_arboles()
    chooser=next(w for w in widgets if 'values' in w.options)
    export=next(w for w in widgets if w.options.get('text')=='Exportar JSON')
    assert chooser.options['values']==['Edición','Modelo'] and export.options['state']=='normal'
    variables[0].set('Modelo');chooser.bindings['<<ComboboxSelected>>'](None)
    export.options['command']()
    stored=json.loads(f.read_text())
    assert stored['scene_name']=='Modelo' and len(stored['rows'])==1
    assert stored['rows'][0]['tree']['radio_copa']==5
    original=f.read_bytes()
    obj._leer_parametros_tmrt=lambda:(30,2.5,date(2024,3,10),40.7,-74)
    obj._timezone_actual=lambda:'America/New_York'
    chooser.bindings['<<ComboboxSelected>>'](None)
    assert export.options['state']=='disabled'
    export.options['command']()
    assert f.read_bytes()==original
    assert any('Hora local inexistente' in w.options.get('text','') for w in widgets)
    widgets[0].destroy()
