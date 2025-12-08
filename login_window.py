import tkinter as tk
from tkinter import messagebox
from admin_panel import AdminPanel

class LoginWindow:
    def __init__(self, root, db_manager):
        self.root = root
        self.db_manager = db_manager
        self.root.title("Login")
        self.root.configure(bg="#f3f4f6")
        self.root.geometry("360x260")

        """ tk.Label(root, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(root)
        self.username_entry.pack(pady=5) """
        container = tk.Frame(root, bg="#f3f4f6", padx=20, pady=20)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        """ tk.Label(root, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.pack(pady=5)
         """
        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=20, pady=20)
        card.pack(fill="both", expand=True)

        """ tk.Button(root, text="Login", command=self.login).pack(pady=5)
        tk.Button(root, text="Recover Password", command=self.recover_password).pack(pady=5) """
        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=24, pady=22)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        header = tk.Label(card, text="Bienvenido", font=("Helvetica", 16, "bold"), bg="white", fg="#1f2937")
        header.grid(row=0, column=0, pady=(0, 12))

        tk.Label(card, text="Usuario", font=("Helvetica", 11), bg="white", fg="#4b5563").grid(row=1, column=0, pady=(0, 5))
        self.username_entry = tk.Entry(card, width=28, relief="flat", highlightbackground="#d1d5db", highlightthickness=1, bd=0)
        self.username_entry.grid(row=2, column=0, pady=(0, 12), ipady=6, sticky="ew")

        tk.Label(card, text="Contraseña", font=("Helvetica", 11), bg="white", fg="#4b5563").grid(row=3, column=0, pady=(0, 5))
        self.password_entry = tk.Entry(card, show="*", width=28, relief="flat", highlightbackground="#d1d5db", highlightthickness=1, bd=0)
        self.password_entry.grid(row=4, column=0, pady=(0, 14), ipady=6, sticky="ew")

        login_btn = tk.Button(card, text="Ingresar", command=self.login, bg="#2563eb", fg="white", activebackground="#1d4ed8", relief="flat", padx=14, pady=8, cursor="hand2")
        login_btn.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        recover_btn = tk.Button(card, text="Recuperar contraseña", command=self.recover_password, bg="#e5e7eb", fg="#1f2937", activebackground="#d1d5db", relief="flat", padx=14, pady=8, cursor="hand2")
        recover_btn.grid(row=6, column=0, sticky="ew")

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
