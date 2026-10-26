"""Adaptador Tk para las solicitudes del gestor de proyectos."""
from tkinter import messagebox, filedialog
from ui.dialogs import ask_project_name, ask_project_location
from ui.modal_style import ask_text


class TkProjectInteraction:
    showerror = staticmethod(messagebox.showerror)
    showwarning = staticmethod(messagebox.showwarning)
    showinfo = staticmethod(messagebox.showinfo)
    askyesno = staticmethod(messagebox.askyesno)
    asksaveasfilename = staticmethod(filedialog.asksaveasfilename)
    askopenfilename = staticmethod(filedialog.askopenfilename)
    askdirectory = staticmethod(filedialog.askdirectory)
    ask_text = staticmethod(ask_text)
    ask_project_name = staticmethod(ask_project_name)
    ask_project_location = staticmethod(ask_project_location)
