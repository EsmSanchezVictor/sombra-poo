import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from app import App
#from app_copy import App
from add_user_window import AddUserWindow
from modify_user_window import ModifyUserWindow
#from gui_copy import App

class MainApp:
    def __init__(self, root, db_manager):
        
        self.root = root
        self.login_root = root  # Ventana de login (root)
        self.db_manager = db_manager
        self.root.title("Login")
        self.root.configure(bg="#f3f4f6")
        self.root.geometry("480x380")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        """ self.root.attributes('-fullscreen', True)

        tk.Label(root, text="Username:").grid(row=0, column=0, pady=5, padx=5)
        self.username_entry = tk.Entry(root)
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(root, text="Password:").grid(row=1, column=0, pady=5, padx=5)
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)

        tk.Button(root, text="Login", command=self.login).grid(row=2, column=0, columnspan=2, pady=10)
         """
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        container = tk.Frame(root, bg="#f3f4f6", padx=20, pady=20)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=24, pady=22)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        header = tk.Label(
            card,
            text="Bienvenido",
            font=("Helvetica", 16, "bold"),
            bg="white",
            fg="#1f2937",
        )
        header.grid(row=0, column=0, pady=(0, 12))

        tk.Label(
            card,
            text="Usuario",
            font=("Helvetica", 11),
            bg="white",
            fg="#4b5563",
        ).grid(row=1, column=0, pady=(0, 5))
        self.username_entry = tk.Entry(
            card,
            width=28,
            relief="flat",
            highlightbackground="#d1d5db",
            highlightthickness=1,
            bd=0,
        )
        self.username_entry.grid(row=2, column=0, pady=(0, 12), ipady=6, sticky="ew")

        tk.Label(
            card,
            text="Contraseña",
            font=("Helvetica", 11),
            bg="white",
            fg="#4b5563",
        ).grid(row=3, column=0, pady=(0, 5))
        self.password_entry = tk.Entry(
            card,
            show="*",
            width=28,
            relief="flat",
            highlightbackground="#d1d5db",
            highlightthickness=1,
            bd=0,
        )
        self.password_entry.grid(row=4, column=0, pady=(0, 14), ipady=6, sticky="ew")

        login_btn = tk.Button(
            card,
            text="Ingresar",
            command=self.login,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
        )
        login_btn.grid(row=5, column=0, sticky="ew", pady=(0, 8)) 

    def on_close(self):
        self.root.destroy()  # Cierra la ventana actual (root_2)
        self.login_root.destroy()  # Cierra la ventana de login (root)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = self.db_manager.get_user(username)

        if user and user[2] == password:
            if user[3] == 1:  # Admin user
                self.admin_options()
            else:  # Regular user
                self.open_main_app()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

    def admin_options(self):
        for widget in self.root.winfo_children():
            widget.destroy()
 
        tk.Button(self.root, text="Gestión de Usuarios", command=self.open_user_management).grid(row=0, column=0, pady=10, padx=10)
        tk.Button(self.root, text="Acceso al Software", command=self.open_main_app).grid(row=1, column=0, pady=10, padx=10)

    def open_main_app(self):
        #messagebox.showinfo("Acceso", "Bienvenido al software principal.")
        root_2 = tk.Toplevel()
        #app = App(root_2)
        app = App(root_2)  # Pasar self.root como parámetro
        self.root.withdraw()  # Oculta la ventana de login
        
    def open_user_management(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        users = self.db_manager.fetch_all_users()

        tk.Label(self.root, text="Gestión de Usuarios", font=("Arial", 16)).grid(row=0, column=0, columnspan=6, pady=10)

        headers = ["ID", "Username", "Nombre","Admin", "Nombre", "Apellido","DNI", "Email", "Teléfono", "Calle", "Número", "Ciudad"]
        for col, header in enumerate(headers):
            tk.Label(self.root, text=header, font=("Arial", 10, "bold")).grid(row=1, column=col, padx=5, pady=5)

        for row, user in enumerate(users, start=2):
            for col, data in enumerate(user):
                tk.Label(self.root, text=data).grid(row=row, column=col, padx=5, pady=5)

        tk.Button(self.root, text="Agregar Usuario", command=self.add_user).grid(row=len(users) + 2, column=0, pady=10)
        tk.Button(self.root, text="Modificar Usuario", command=self.modify_user).grid(row=len(users) + 2, column=1, pady=10)
        tk.Button(self.root, text="Eliminar Usuario", command=self.delete_user).grid(row=len(users) + 2, column=2, pady=10)

    def add_user(self):
        AddUserWindow(self.root, self.db_manager, self)

    def modify_user(self):
        ModifyUserWindow(self.root, self.db_manager, self)
    

    def delete_user(self):
        user_id = simpledialog.askinteger("Eliminar Usuario", "Ingrese el ID del usuario a eliminar:")
        if user_id:
            self.db_manager.delete_user(user_id)
            messagebox.showinfo("Éxito", "Usuario eliminado correctamente.")
            self.open_user_management()