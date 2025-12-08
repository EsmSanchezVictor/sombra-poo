import tkinter as tk
from tkinter import messagebox


class AddUserWindow:
    def __init__(self, root, db_manager, main_app):
        self.root = root
        self.db_manager = db_manager
        self.main_app = main_app

        self.window = tk.Toplevel(root)
        self.window.title("Agregar Usuario")

        self.fields = {
            "Username": tk.Entry(self.window),
            "Password": tk.Entry(self.window),
            "Es Admin (1 o 0)": tk.Entry(self.window),
            "Nombre": tk.Entry(self.window),
            "Apellido": tk.Entry(self.window),
            "DNI": tk.Entry(self.window),
            "Email": tk.Entry(self.window),
            "Teléfono": tk.Entry(self.window),
            "Calle": tk.Entry(self.window),
            "Número": tk.Entry(self.window),
            "Ciudad": tk.Entry(self.window)
        
        }

        for idx, (label, entry) in enumerate(self.fields.items()):
            tk.Label(self.window, text=label).grid(row=idx, column=0, pady=5, padx=5)
            entry.grid(row=idx, column=1, pady=5, padx=5)

        tk.Button(self.window, text="Guardar", command=self.save_user).grid(row=len(self.fields), column=0, columnspan=2, pady=10)

    def save_user(self):
        values = [entry.get() for entry in self.fields.values()]
        #self.db_manager.add_user(*values[:2], int(values[10]), *values[2:10])
        self.db_manager.add_user(values[0], values[1], int(values[2]), values[3], values[4], values[5], values[6], values[7], values[8], values[9], values[10])

        messagebox.showinfo("Éxito", "Usuario agregado correctamente.")
        self.window.destroy()
        self.main_app.open_user_management()