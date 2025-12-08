import tkinter as tk
from add_user_window import AddUserWindow

class AdminPanel:
    def __init__(self, root, db_manager):
        self.root = root
        self.db_manager = db_manager
        self.panel = tk.Toplevel(root)
        self.panel.title("Panel de Administración")

        tk.Button(self.panel, text="Agregar Usuario", command=self.add_user).pack(pady=5)
        # Puedes agregar más botones para modificar/eliminar usuarios

    def add_user(self):
        AddUserWindow(self.panel, self.db_manager)
