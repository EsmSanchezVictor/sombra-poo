import tkinter as tk
from tkinter import ttk
from add_user_window import AddUserWindow
from ui.modal_style import prepare_dialog

class AdminPanel:
    def __init__(self, root, db_manager):
        self.root = root
        self.db_manager = db_manager
        self.panel = tk.Toplevel(root)
        prepare_dialog(self.panel, root, modal=False, resizable=False, minsize=(360, 200))
        self.panel.title("Panel de Administración")
        self.center_window(320, 180)
        body = ttk.Frame(self.panel, padding=(18, 16, 18, 16))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Administración", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(body, text="Gestión de usuarios del sistema.", style="Muted.TLabel").pack(anchor="w", pady=(2, 14))
        ttk.Button(body, text="Agregar usuario", command=self.add_user, style="DialogPrimary.TButton").pack(anchor="e")
        # Puedes agregar más botones para modificar/eliminar usuarios
    def center_window(self, width, height):
        self.panel.update_idletasks()
        screen_width = self.panel.winfo_screenwidth()
        screen_height = self.panel.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.panel.geometry(f"{width}x{height}+{x}+{y}")

    def add_user(self):
        AddUserWindow(self.panel, self.db_manager, self)
