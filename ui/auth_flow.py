"""Alta inicial y sustitución obligatoria de la clave histórica."""
import tkinter as tk
from tkinter import ttk, messagebox
from core.auth_policy import MIN_PASSWORD_LENGTH, password_error, username_error
from ui.modal_style import prepare_dialog, dialog_container, dialog_header, ask_password_pair


def setup_first_admin(parent, db):
    result = {"created": False}
    window = tk.Toplevel(parent)
    window.title("Primer administrador")
    prepare_dialog(window, parent, modal=True, resizable=False)
    body = dialog_container(window)
    dialog_header(body, "Primer administrador", "Creá tu cuenta para comenzar a usar Proyecto Sombra.")
    values = {key: tk.StringVar() for key in ("username", "first_name", "last_name", "password", "confirm")}
    form = ttk.Frame(body)
    form.pack(fill="both", expand=True)
    form.columnconfigure(1, weight=1)
    for row, (key, label) in enumerate((("username", "Usuario"), ("first_name", "Nombre"),
                                       ("last_name", "Apellido"), ("password", "Contraseña"),
                                       ("confirm", "Repetir contraseña"))):
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(form, textvariable=values[key], show="*" if key in ("password", "confirm") else "", width=32).grid(
            row=row, column=1, sticky="ew", pady=6)
    ttk.Label(body, text=f"Contraseña: al menos {MIN_PASSWORD_LENGTH} caracteres.").pack(anchor="w", pady=(10, 0))

    def create():
        data = {key: value.get() for key, value in values.items()}
        error = username_error(data["username"]) or password_error(data["password"])
        if data["password"] != data["confirm"]:
            error = "Las contraseñas no coinciden."
        if error:
            messagebox.showerror("Datos de la cuenta", error, parent=window)
            return
        if not db.create_initial_admin(data["username"], data["password"], data["first_name"], data["last_name"]):
            messagebox.showerror("Cuenta", "No se pudo crear la cuenta. Revisá el nombre de usuario.", parent=window)
            return
        result["created"] = True
        window.destroy()

    buttons = ttk.Frame(body)
    buttons.pack(fill="x", pady=(16, 0))
    ttk.Button(buttons, text="Salir", command=window.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Crear administrador", command=create, style="DialogPrimary.TButton").pack(side="right")
    window.wait_window()
    return result["created"]


def authenticate_with_required_change(parent, db, username, password):
    row = db.get_user(username)
    if row is not None and row["requires_password_change"]:
        if not db.legacy_password_matches(username, password):
            return False
        messagebox.showinfo("Actualizar contraseña", "La contraseña inicial debe reemplazarse antes de ingresar.", parent=parent)
        new, _ = ask_password_pair(parent, "Actualizar contraseña inicial", min_length=MIN_PASSWORD_LENGTH)
        if new is None or not db.replace_legacy_password(username, password, new):
            return False
        password = new
    return db.authenticate(username, password)
