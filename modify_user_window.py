import re
import tkinter as tk
from tkinter import ttk, messagebox
from ui.modal_style import prepare_dialog


class ModifyUserWindow:
    def __init__(self, root, db_manager, main_app, user_id):
        self.root = root
        self.db_manager = db_manager
        self.main_app = main_app
        self.user_id = int(user_id)
        user = self.db_manager.get_user_by_id(self.user_id)
        if user is None:
            messagebox.showerror("Error", "El usuario ya no existe.", parent=root)
            return

        self.window = tk.Toplevel(root)
        prepare_dialog(self.window, root, modal=True, resizable=False, minsize=(520, 610))
        self.window.title("Editar usuario")
        self.window.configure(bg="#ffffff")
        self.window.transient(root)
        self.window.grab_set()
        self.window.resizable(False, False)

        outer = tk.Frame(self.window, bg="#ffffff", padx=18, pady=18)
        outer.grid(row=0, column=0, sticky="nsew")
        card = tk.Frame(outer, bg="white", bd=1, relief="solid", padx=20, pady=18)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        tk.Label(card, text="Editar usuario", font=("Segoe UI", 13, "bold"), bg="white", fg="#1f2937").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )

        self.username = tk.StringVar(value=user["username"] or "")
        self.role = tk.StringVar(value="Administrador" if user["is_admin"] else "Usuario")
        self.active = tk.BooleanVar(value=bool(user["is_active"]))
        self.first_name = tk.StringVar(value=user["first_name"] or "")
        self.last_name = tk.StringVar(value=user["last_name"] or "")
        self.dni = tk.StringVar(value=user["dni"] or "")
        self.email = tk.StringVar(value=user["email"] or "")
        self.phone = tk.StringVar(value=user["phone"] or "")
        self.street = tk.StringVar(value=user["street"] or "")
        self.number = tk.StringVar(value=user["number"] or "")
        self.city = tk.StringVar(value=user["city"] or "")

        row = 1
        row = self._section(card, row, "Cuenta")
        row = self._entry(card, row, "Usuario", self.username)
        tk.Label(card, text="Rol", bg="white", fg="#4b5563").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(card, textvariable=self.role, values=("Usuario", "Administrador"), state="readonly", width=28).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        row += 1
        tk.Label(card, text="Estado", bg="white", fg="#4b5563").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        tk.Checkbutton(card, text="Usuario activo", variable=self.active, bg="white", activebackground="white").grid(
            row=row, column=1, sticky="w", pady=5
        )
        row += 1

        row = self._section(card, row, "Datos personales")
        row = self._entry(card, row, "Nombre", self.first_name)
        row = self._entry(card, row, "Apellido", self.last_name)
        row = self._entry(card, row, "DNI", self.dni)

        row = self._section(card, row, "Contacto y domicilio")
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
        ttk.Button(buttons, text="Guardar cambios", command=self.save_changes, style="DialogPrimary.TButton").grid(
            row=0, column=1, padx=(6, 0), sticky="ew")

        self.window.update_idletasks()
        w = max(520, self.window.winfo_reqwidth())
        h = max(610, self.window.winfo_reqheight())
        sw, sh = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.window.geometry(f"{w}x{h}+{(sw-w)//2}+{max(20, (sh-h)//2)}")

    @staticmethod
    def _section(parent, row, text):
        tk.Label(parent, text=text, font=("Helvetica", 10, "bold"), bg="white", fg="#1f2937").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10 if row > 1 else 0, 4)
        )
        return row + 1

    @staticmethod
    def _entry(parent, row, label, variable):
        tk.Label(parent, text=label, bg="white", fg="#4b5563").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )
        tk.Entry(parent, textvariable=variable, relief="solid", bd=1, width=30).grid(
            row=row, column=1, sticky="ew", pady=5, ipady=4
        )
        return row + 1

    def save_changes(self):
        username = self.username.get().strip()
        if not username:
            messagebox.showerror("Datos incompletos", "El nombre de usuario no puede quedar vacío.", parent=self.window)
            return
        email = self.email.get().strip()
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            messagebox.showerror("Email inválido", "El email no tiene un formato válido.", parent=self.window)
            return

        ok, error = self.db_manager.update_user_management(
            self.user_id, username,
            1 if self.role.get() == "Administrador" else 0,
            1 if self.active.get() else 0,
            self.first_name.get().strip(), self.last_name.get().strip(),
            self.dni.get().strip(), email, self.phone.get().strip(),
            self.street.get().strip(), self.number.get().strip(), self.city.get().strip(),
        )
        if not ok:
            messagebox.showerror("No se pudo guardar", error or "No fue posible modificar el usuario.", parent=self.window)
            return
        messagebox.showinfo("Usuario actualizado", "Los cambios se guardaron correctamente.", parent=self.window)
        self.window.destroy()
        if hasattr(self.main_app, "refresh_user_management"):
            self.main_app.refresh_user_management()
