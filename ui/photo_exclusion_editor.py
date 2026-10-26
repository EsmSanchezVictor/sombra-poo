"""Editor manual de exclusiones sobre la rejilla del análisis, sin alterar la foto."""
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import Image,ImageTk
from core.photo_exclusions import add_rectangle,exclusion_mask
from ui.modal_style import prepare_dialog


class PhotoExclusionEditor:
    def __init__(self,parent,area,valid,initial,on_apply,on_discard=None):
        self.area=np.asarray(area,dtype=float);self.valid=np.asarray(valid,dtype=bool)
        self.mask=exclusion_mask(initial,self.area.shape);self.history=[];self.on_apply=on_apply
        self.on_discard=on_discard
        self.top=tk.Toplevel(parent);self.top.title('Excluir materiales del análisis')
        prepare_dialog(self.top,parent,modal=True,resizable=False,minsize=(500,500))
        ttk.Label(self.top,text='Arrastre rectángulos sobre zonas que no correspondan a la superficie comparada.\n'
            'Rojo = excluido. La referencia iluminada se conserva.',justify='left',wraplength=520).pack(padx=12,pady=10)
        height,width=self.area.shape;scale=min(520/width,360/height)
        self.size=(max(1,int(width*scale)),max(1,int(height*scale)))
        self.canvas=tk.Canvas(self.top,width=self.size[0],height=self.size[1],highlightthickness=0,borderwidth=0)
        self.canvas.pack(padx=12)
        self.status=ttk.Label(self.top);self.status.pack(padx=12,pady=8)
        self.error=ttk.Label(self.top,foreground='#a02020',wraplength=500);self.error.pack(padx=12)
        buttons=ttk.Frame(self.top);buttons.pack(fill='x',padx=12,pady=12)
        ttk.Button(buttons,text='Deshacer',command=self.undo).pack(side='left')
        ttk.Button(buttons,text='Limpiar',command=self.clear).pack(side='left',padx=5)
        if on_discard is not None:ttk.Button(buttons,text='Restaurar guardado',command=self.discard).pack(side='left',padx=5)
        ttk.Button(buttons,text='Cancelar',command=self.close).pack(side='right')
        ttk.Button(buttons,text='Aplicar',command=self.apply).pack(side='right',padx=5)
        ttk.Label(self.top,text='Después de aplicar, genere la curva para actualizar los resultados.',wraplength=500).pack(pady=(0,10))
        self.origin=None;self.preview=None;self.photo=None
        self.canvas.bind('<ButtonPress-1>',self.start)
        self.canvas.bind('<B1-Motion>',self.drag)
        self.canvas.bind('<ButtonRelease-1>',self.finish)
        self.top.protocol('WM_DELETE_WINDOW',self.close);self.draw()

    def draw(self):
        gray=np.clip(np.nan_to_num(self.area,nan=0),0,255).astype(np.uint8)
        rgb=np.repeat(gray[...,None],3,axis=2)
        rgb[~self.valid]=[100,100,100]
        chosen=self.mask & self.valid
        rgb[chosen]=(rgb[chosen].astype(float)*.35+np.array([255,40,40])*.65).astype(np.uint8)
        im=Image.fromarray(rgb).resize(self.size,Image.Resampling.NEAREST)
        self.photo=ImageTk.PhotoImage(im);self.canvas.delete('all')
        self.canvas.create_image(0,0,anchor='nw',image=self.photo);self.preview=None
        self.status.config(text=f'Excluidos: {int(chosen.sum())} · Conservados: {int((self.valid & ~self.mask).sum())} píxeles de la rejilla')

    def start(self,event):self.origin=(event.x,event.y)

    def drag(self,event):
        if self.origin is None:return
        if self.preview is not None:self.canvas.delete(self.preview)
        self.preview=self.canvas.create_rectangle(*self.origin,event.x,event.y,outline='red',width=2)

    def finish(self,event):
        if self.origin is None:return
        self.history.append(self.mask.copy());self.history=self.history[-20:]
        self.mask=add_rectangle(self.mask,(*self.origin,event.x,event.y),self.size) & self.valid
        self.origin=None;self.error.config(text='');self.draw()

    def undo(self):
        if self.history:self.mask=self.history.pop();self.draw()

    def clear(self):
        self.history.append(self.mask.copy());self.history=self.history[-20:]
        self.mask[:]=False;self.draw()

    def apply(self):
        if not np.any(self.valid & ~self.mask):
            self.error.config(text='Debe conservar al menos un píxel válido de la superficie.');return
        try:self.on_apply(self.mask.copy())
        except ValueError as exc:self.error.config(text=str(exc));return
        self.close()

    def discard(self):
        try:self.on_discard()
        except ValueError as exc:self.error.config(text=str(exc));return
        self.close()

    def close(self):
        self.photo=None;self.history.clear();self.top.destroy()
