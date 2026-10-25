import re
import tkinter as tk
from tkinter import ttk, messagebox
from ui.modal_style import prepare_dialog
from core.auth_policy import password_error, username_error


class AddUserWindow:
    def __init__(self, root, db_manager, main_app):
        self.root = root
        self.db_manager = db_manager
        self.main_app = main_app

        self.window = tk.Toplevel(root)
        prepare_dialog(self.window, root, modal=True, resizable=False, minsize=(520, 620))
        self.window.title("Nuevo usuario")
        self.window.configure(bg="#ffffff")
        self.window.transient(root)
        self.window.grab_set()
        self.window.resizable(False, False)

        outer = tk.Frame(self.window, bg="#ffffff", padx=18, pady=18)
        outer.grid(row=0, column=0, sticky="nsew")
        card = tk.Frame(outer, bg="white", bd=1, relief="solid", padx=20, pady=18)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        tk.Label(card, text="Nuevo usuario", font=("Segoe UI", 13, "bold"), bg="white", fg="#1f2937").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.password2 = tk.StringVar()
        self.role = tk.StringVar(value="Usuario")
        self.first_name = tk.StringVar()
        self.last_name = tk.StringVar()
        self.dni = tk.StringVar()
        self.email = tk.StringVar()
        self.phone = tk.StringVar()
        self.street = tk.StringVar()
        self.number = tk.StringVar()
        self.city = tk.StringVar()

        row = 1
        row = self._section(card, row, "Cuenta")
        row = self._entry(card, row, "Usuario", self.username)
        row = self._entry(card, row, "Contraseña", self.password, show="*")
        row = self._entry(card, row, "Repetir contraseña", self.password2, show="*")
        tk.Label(card, text="Rol", bg="white", fg="#4b5563").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(card, textvariable=self.role, values=("Usuario", "Administrador"), state="readonly", width=28).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        row += 1

        row = self._section(card, row, "Datos personales")
        row = self._entry(card, row, "Nombre", self.first_name)
        row = self._entry(card, row, "Apellido", self.last_name)
        row = self._entry(card, row, "DNI", self.dni)

        row = self._section(card, row, "Contacto")
        row = self._entry(card, row, "Email", self.email)
        row = self._entry(card, row, "Teléfono", self.phone)
        row = self._entry(card, row, "Calle", self.street)
        row = self._entry(card, row, "Número", self.number)
        row = self._entry(card, row, "Ciudad", self.city)

        buttons = tk.Frame(card, bg="white")
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        buttons.grid_columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(buttons, text="Cancelar", command=self.window.destroy).grid(
            row=0, column=0, padx=(0, 6), sticky="ew")
        ttk.Button(buttons, text="Guardar usuario", command=self.save_user, style="DialogPrimary.TButton").grid(
            row=0, column=1, padx=(6, 0), sticky="ew")

        self.window.update_idletasks()
        w = max(520, self.window.winfo_reqwidth())
        h = max(620, self.window.winfo_reqheight())
        sw, sh = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.window.geometry(f"{w}x{h}+{(sw-w)//2}+{max(20, (sh-h)//2)}")

    @staticmethod
    def _section(parent, row, text):
        tk.Label(parent, text=text, font=("Helvetica", 10, "bold"), bg="white", fg="#1f2937").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10 if row > 1 else 0, 4)
        )
        return row + 1

    @staticmethod
    def _entry(parent, row, label, variable, show=None):
        tk.Label(parent, text=label, bg="white", fg="#4b5563").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )
        tk.Entry(parent, textvariable=variable, show=show or "", relief="solid", bd=1, width=30).grid(
            row=row, column=1, sticky="ew", pady=5, ipady=4
        )
        return row + 1

    def _validate(self):
        username = self.username.get().strip()
        if not username:
            return "Ingresá un nombre de usuario."
        if len(username) < 3:
            return "El nombre de usuario debe tener al menos 3 caracteres."
        error = username_error(username) or password_error(self.password.get())
        if error:
            return error
        if self.password.get() != self.password2.get():
            return "Las contraseñas no coinciden."
        email = self.email.get().strip()
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return "El email no tiene un formato válido."
        return None

    def save_user(self):
        error = self._validate()
        if error:
            messagebox.showerror("Datos incompletos", error, parent=self.window)
            return

        ok = self.db_manager.add_user(
            self.username.get().strip(),
            self.password.get(),
            1 if self.role.get() == "Administrador" else 0,
            self.first_name.get().strip(), self.last_name.get().strip(),
            self.dni.get().strip(), self.email.get().strip(), self.phone.get().strip(),
            self.street.get().strip(), self.number.get().strip(), self.city.get().strip(),
        )
        if not ok:
            messagebox.showerror("No se pudo guardar", "Ya existe un usuario con ese nombre.", parent=self.window)
            return
        messagebox.showinfo("Usuario creado", "El usuario se guardó correctamente.", parent=self.window)
        self.window.destroy()
        if hasattr(self.main_app, "refresh_user_management"):
            self.main_app.refresh_user_management()
