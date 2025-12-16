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
        self.center_window(480, 380)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
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
        
    def center_window(self, width, height):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def exit_fullscreen(self):
        self.root.attributes("-fullscreen", False)

    def back_to_admin(self):
        self.exit_fullscreen()
        self.admin_options()

    def exit_program(self):
        self.root.quit()
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
        self.exit_fullscreen()
        for widget in self.root.winfo_children():
            widget.destroy()
        container = tk.Frame(self.root, bg="#f3f4f6", padx=20, pady=20)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.center_window(520, 420)
        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=24, pady=22)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Menú de administrador",
            font=("Helvetica", 16, "bold"),
            bg="white",
            fg="#1f2937",
        ).grid(row=0, column=0, pady=(0, 16), sticky="ew")

        tk.Button(
            card,
            text="Gestión de Usuarios",
            command=self.open_user_management,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
        ).grid(row=1, column=0, pady=(0, 10), sticky="ew")
        tk.Button(
            card,
            text="Acceso al Software",
            command=self.open_main_app,
            bg="#fef9c3",
            fg="#111827",
            activebackground="#fef08a",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
        ).grid(row=2, column=0, sticky="ew")

    def open_main_app(self):

        root_2 = tk.Toplevel()
        app = App(root_2)  # Pasar self.root como parámetro
        self.root.withdraw()  # Oculta la ventana de login
        
    def open_user_management(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.attributes("-fullscreen", True)

        users = self.db_manager.fetch_all_users()

        container = tk.Frame(self.root, bg="#f3f4f6", padx=18, pady=18)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=18, pady=18)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Gestión de Usuarios",
            font=("Helvetica", 16, "bold"),
            bg="white",
            fg="#1f2937",
        ).grid(row=0, column=0, columnspan=4, pady=(0, 12), sticky="w")

        table = tk.Frame(card, bg="white")
        table.grid(row=1, column=0, columnspan=4, sticky="nsew")
        table.grid_columnconfigure(tuple(range(12)), weight=1)

        headers = [
            "ID",
            "Username",
            "Nombre",
            "Admin",
            "Nombre",
            "Apellido",
            "DNI",
            "Email",
            "Teléfono",
            "Calle",
            "Número",
            "Ciudad",
        ]
        
        
        for col, header in enumerate(headers):
            tk.Label(
                table,
                text=header,
                font=("Helvetica", 10, "bold"),
                bg="#f9fafb",
                fg="#111827",
                padx=6,
                pady=6,
                bd=1,
                relief="solid",
            ).grid(row=0, column=col, sticky="nsew")

        for row, user in enumerate(users, start=1):
            for col, data in enumerate(user):
                tk.Label(
                    table,
                    text=data,
                    font=("Helvetica", 10),
                    bg="white",
                    fg="#1f2937",
                    padx=6,
                    pady=5,
                    bd=1,
                    relief="solid",
                ).grid(row=row, column=col, sticky="nsew")

        actions = tk.Frame(card, bg="white")
        actions.grid(row=2, column=0, columnspan=4, pady=(14, 0), sticky="ew")
        actions.grid_columnconfigure((0, 1, 2), weight=1, uniform="actions")

        tk.Button(
            actions,
            text="Agregar Usuario",
            command=self.add_user,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(
            actions,
            text="Modificar Usuario",
            command=self.modify_user,
            bg="#fef9c3",
            fg="#111827",
            activebackground="#fef08a",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(
            actions,
            text="Eliminar Usuario",
            command=self.delete_user,
            bg="#ef4444",
            fg="white",
            activebackground="#dc2626",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=2, padx=5, sticky="ew")
        
        footer = tk.Frame(card, bg="white")
        footer.grid(row=3, column=0, columnspan=4, pady=(16, 0), sticky="ew")
        footer.grid_columnconfigure((0, 1), weight=1, uniform="footer")

        tk.Button(
            footer,
            text="Volver",
            command=self.back_to_admin,
            bg="#fef9c3",
            fg="#111827",
            activebackground="#d1d5db",
            relief="flat",
            padx=12,
            pady=10,
            cursor="hand2",
        ).grid(row=0, column=0, padx=6, sticky="ew")

        tk.Button(
            footer,
            text="Salir",
            command=self.exit_program,
            bg="#ef4444",
            fg="white",
            activebackground="#dc2626",
            relief="flat",
            padx=12,
            pady=10,
            cursor="hand2",
        ).grid(row=0, column=1, padx=6, sticky="ew")
        
    def add_user(self):
        AddUserWindow(self.root, self.db_manager, self)

    def modify_user(self):
        ModifyUserWindow(self.root, self.db_manager, self)    

    def delete_user(self):
        user_id = simpledialog.askinteger(
            "Eliminar Usuario", "Ingrese el ID del usuario a eliminar:"
        )
        if user_id:
            self.db_manager.delete_user(user_id)
            messagebox.showinfo("Éxito", "Usuario eliminado correctamente.")
            self.open_user_management()