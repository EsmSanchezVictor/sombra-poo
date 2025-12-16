import tkinter as tk
from add_user_window import AddUserWindow

class AdminPanel:
    def __init__(self, root, db_manager):
        self.root = root
        self.db_manager = db_manager
        self.panel = tk.Toplevel(root)
        self.panel.title("Panel de Administración")
        self.center_window(320, 180)
        tk.Button(self.panel, text="Agregar Usuario", command=self.add_user).pack(pady=5)
        # Puedes agregar más botones para modificar/eliminar usuarios
    def center_window(self, width, height):
        self.panel.update_idletasks()
        screen_width = self.panel.winfo_screenwidth()
        screen_height = self.panel.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.panel.geometry(f"{width}x{height}+{x}+{y}")

    def add_user(self):
        AddUserWindow(self.panel, self.db_manager)
