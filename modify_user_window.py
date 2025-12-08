import tkinter as tk
from tkinter import messagebox


class ModifyUserWindow:
    def __init__(self, root, db_manager, main_app):
        self.root = root
        self.db_manager = db_manager

        self.window = tk.Toplevel(root)
        self.window.title("Modificar Usuario")

        # Entrada para el ID del usuario
        tk.Label(self.window, text="ID del Usuario:").grid(row=0, column=0, pady=5, padx=5)
        self.id_entry = tk.Entry(self.window)
        self.id_entry.grid(row=0, column=1, pady=5, padx=5)

        tk.Button(self.window, text="Cargar Usuario", command=self.load_user).grid(row=0, column=2, pady=5, padx=5)

        self.fields = {
            "Nombre": tk.Entry(self.window),
            "Apellido": tk.Entry(self.window),
            "DNI": tk.Entry(self.window),
            "Email": tk.Entry(self.window),
            "Teléfono": tk.Entry(self.window),
            "Calle": tk.Entry(self.window),
            "Número": tk.Entry(self.window),
            "Ciudad": tk.Entry(self.window),
        }

        # Crear campos pero inicialmente deshabilitarlos hasta que se cargue el usuario
        for idx, (label, entry) in enumerate(self.fields.items(), start=1):
            tk.Label(self.window, text=label).grid(row=idx, column=0, pady=5, padx=5)
            entry.grid(row=idx, column=1, pady=5, padx=5)
            entry.config(state="disabled")

        tk.Button(self.window, text="Guardar Cambios", command=self.save_changes).grid(row=len(self.fields) + 1, column=0, columnspan=2, pady=10)

    def load_user(self):
        user_id = self.id_entry.get()
        if not user_id.isdigit():
            messagebox.showerror("Error", "Por favor, ingresa un ID válido.")
            return

        user = self.db_manager.get_user_by_id(int(user_id))
        if not user:
            messagebox.showerror("Error", "No se encontró un usuario con ese ID.")
            return

        # Cargar datos en los campos
        field_values = user[4:]  # Excluir id, username, password, is_admin
        for entry, value in zip(self.fields.values(), field_values):
            entry.config(state="normal")  # Habilitar los campos
            entry.delete(0, tk.END)  # Limpiar el contenido actual
            entry.insert(0, value)  # Cargar el valor del usuario

        self.current_user_id = int(user_id)

    def save_changes(self):
        if not hasattr(self, "current_user_id"):
            messagebox.showerror("Error", "Primero carga un usuario.")
            return

        updated_values = [entry.get() for entry in self.fields.values()]
        self.db_manager.update_user(
            self.current_user_id,
            updated_values[0],  # first_name
            updated_values[1],  # last_name
            updated_values[2],  # dni
            updated_values[3],  # email
            updated_values[4],  # phone
            updated_values[5],  # street
            updated_values[6],  # number
            updated_values[7],  # city
        )
        messagebox.showinfo("Éxito", "Usuario modificado correctamente.")
        self.window.destroy()
