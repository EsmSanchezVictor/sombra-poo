import tkinter as tk
from tkinter import messagebox
from admin_panel import AdminPanel

class LoginWindow:
    def __init__(self, root, db_manager):
        self.root = root
        self.db_manager = db_manager
        self.root.title("Login")

        tk.Label(root, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(root)
        self.username_entry.pack(pady=5)

        tk.Label(root, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(root, text="Login", command=self.login).pack(pady=5)
        tk.Button(root, text="Recover Password", command=self.recover_password).pack(pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = self.db_manager.get_user(username)

        if user and user[2] == password:
            if user[3] == 1:
                self.open_admin_panel()
            else:
                self.open_main_app()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

    def recover_password(self):
        username = self.username_entry.get()
        user = self.db_manager.get_user(username)

        if user:
            new_password = tk.simpledialog.askstring("Recuperar contraseña", "Introduce una nueva contraseña:")
            if new_password:
                self.db_manager.update_password(username, new_password)
                messagebox.showinfo("Exito", "Contraseña actualizada correctamente.")
        else:
            messagebox.showerror("Error", "Usuario no encontrado.")

    def open_admin_panel(self):
        AdminPanel(self.root, self.db_manager)

    def open_main_app(self):
        # Reemplaza esto con la llamada a tu GUI principal.
        messagebox.showinfo("Login Exitoso", "Bienvenido al software principal.")
