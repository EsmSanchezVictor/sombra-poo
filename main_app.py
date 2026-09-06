from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from ui.app_ui import SombraApp
from add_user_window import AddUserWindow
from modify_user_window import ModifyUserWindow

class MainApp:
    def __init__(self, root, db_manager):
        
        self.root = root
        self.login_root = root  # Ventana de login (root)
        self.db_manager = db_manager
        self.current_user = None
        self.current_user_id = None
        self.current_session_id = None
        self.workspace_root = None
        self._session_closed = True
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

    def _end_current_session(self):
        """Cierra de forma idempotente la sesión autenticada actual."""
        if self._session_closed or not self.current_session_id:
            return
        try:
            self.db_manager.end_session(self.current_session_id)
        finally:
            self._session_closed = True

    def on_close(self):
        self._end_current_session()
        try:
            if self.workspace_root is not None and self.workspace_root.winfo_exists():
                self.workspace_root.destroy()
        except tk.TclError:
            pass
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass

    def _on_workspace_exit(self):
        """Callback de SombraApp al cerrar la ventana de trabajo."""
        self._end_current_session()
        try:
            if self.login_root.winfo_exists():
                self.login_root.destroy()
        except tk.TclError:
            pass
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
        self._end_current_session()
        self.root.destroy()
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        # FIX (seguridad): antes se comparaba user[2] == password en texto
        # plano, y con el esquema nuevo de hash (PBKDF2+salt) el índice [2]
        # ya no es la contraseña. authenticate() verifica el hash.
        if self.db_manager.authenticate(username, password):
            user = self.db_manager.get_user(username)
            self.current_user = username
            self.current_user_id = int(user[0])
            self.connection_start = datetime.now()
            self.current_session_id = self.db_manager.start_session(username)
            self._session_closed = False
            if user[4] == 1:  # Columna is_admin del esquema con hash
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
        self.center_window(520, 470)
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
            text="Historial de sesiones",
            command=self.open_session_history,
            bg="#e0f2fe",
            fg="#0f172a",
            activebackground="#bae6fd",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
        ).grid(row=2, column=0, pady=(0, 10), sticky="ew")

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
        ).grid(row=3, column=0, sticky="ew")

    def open_main_app(self):
        root_2 = tk.Toplevel(self.root)
        self.workspace_root = root_2
        # La identidad y el session_id se pasan ANTES de construir la UI,
        # para que la barra de estado y los hooks de proyecto nazcan correctos.
        SombraApp(
            root_2,
            db_manager=self.db_manager,
            username=getattr(self, "current_user", "Usuario"),
            session_id=self.current_session_id,
            connection_start=getattr(self, "connection_start", datetime.now()),
            on_session_exit=self._on_workspace_exit,
        )
        self.root.withdraw()  # Oculta la ventana de login

    @staticmethod
    def _format_session_time(value):
        if not value:
            return "—"
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            return str(value)

    def open_session_history(self):
        """Muestra la trazabilidad usuario → sesión → proyecto."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.attributes("-fullscreen", True)
        self.db_manager.touch_session(self.current_session_id)

        container = tk.Frame(self.root, bg="#f3f4f6", padx=18, pady=18)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=18, pady=18)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        tk.Label(
            card, text="Historial de sesiones", font=("Helvetica", 16, "bold"),
            bg="white", fg="#1f2937"
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            card,
            text="Cada fila corresponde a un período de trabajo en un proyecto. "
                 "Las sesiones sin proyecto también quedan registradas.",
            font=("Helvetica", 10), bg="white", fg="#6b7280",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        table_frame = tk.Frame(card, bg="white")
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = (
            "session", "usuario", "login", "logout", "proyecto",
            "accion", "inicio_proyecto", "fin_proyecto", "ruta"
        )
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "session": "Sesión", "usuario": "Usuario", "login": "Ingreso",
            "logout": "Salida", "proyecto": "Proyecto", "accion": "Acción",
            "inicio_proyecto": "Inicio proyecto", "fin_proyecto": "Fin proyecto",
            "ruta": "Ruta del proyecto",
        }
        widths = {
            "session": 70, "usuario": 120, "login": 150, "logout": 150,
            "proyecto": 160, "accion": 95, "inicio_proyecto": 150,
            "fin_proyecto": 150, "ruta": 360,
        }
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], minwidth=60, anchor="w")

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        for row in self.db_manager.fetch_session_history(limit=1000):
            (session_id, _user_id, username, login_at, logout_at, _last_activity,
             _period_id, project_name, project_root, _state_path, action,
             started_at, ended_at, _project_last_activity) = row
            action_label = {
                "created": "Creado",
                "opened": "Abierto",
                "save_as": "Guardar como",
                "duplicated": "Duplicado",
                "imported": "Importado",
            }.get(action, action or "—")
            tree.insert("", "end", values=(
                session_id,
                username,
                self._format_session_time(login_at),
                self._format_session_time(logout_at),
                project_name or "—",
                action_label,
                self._format_session_time(started_at),
                self._format_session_time(ended_at),
                project_root or "—",
            ))

        footer = tk.Frame(card, bg="white")
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        tk.Button(
            footer, text="Volver", command=self.back_to_admin,
            bg="#fef9c3", fg="#111827", relief="flat", padx=18, pady=9,
            cursor="hand2",
        ).pack(side="left")

    def open_user_management(self):
        """Gestión administrativa con proyección segura y selección de filas."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.attributes("-fullscreen", True)
        self.db_manager.touch_session(self.current_session_id)

        container = tk.Frame(self.root, bg="#f3f4f6", padx=18, pady=18)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        card = tk.Frame(container, bg="white", bd=1, relief="solid", padx=18, pady=18)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_rowconfigure(3, weight=1)
        card.grid_columnconfigure(0, weight=1)

        title_row = tk.Frame(card, bg="white")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)
        tk.Label(
            title_row, text="Gestión de Usuarios",
            font=("Helvetica", 16, "bold"), bg="white", fg="#1f2937",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            title_row,
            text="Las credenciales sensibles no se muestran en esta pantalla.",
            font=("Helvetica", 9), bg="white", fg="#6b7280",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        filters = tk.Frame(card, bg="white")
        filters.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        filters.grid_columnconfigure(1, weight=1)
        tk.Label(filters, text="Buscar", bg="white", fg="#4b5563").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.user_search_var = tk.StringVar()
        search_entry = tk.Entry(filters, textvariable=self.user_search_var, relief="solid", bd=1)
        search_entry.grid(row=0, column=1, sticky="ew", ipady=5, padx=(0, 12))

        tk.Label(filters, text="Rol", bg="white", fg="#4b5563").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.user_role_filter = tk.StringVar(value="Todos")
        role_combo = ttk.Combobox(
            filters, textvariable=self.user_role_filter,
            values=("Todos", "Administradores", "Usuarios"), state="readonly", width=16,
        )
        role_combo.grid(row=0, column=3, padx=(0, 12))

        tk.Label(filters, text="Estado", bg="white", fg="#4b5563").grid(row=0, column=4, sticky="w", padx=(0, 6))
        self.user_status_filter = tk.StringVar(value="Todos")
        status_combo = ttk.Combobox(
            filters, textvariable=self.user_status_filter,
            values=("Todos", "Activos", "Inactivos"), state="readonly", width=12,
        )
        status_combo.grid(row=0, column=5)

        info = tk.Label(
            card, text="Seleccioná una fila para editar, cambiar estado, restablecer contraseña o eliminar.",
            font=("Helvetica", 9), bg="white", fg="#6b7280",
        )
        info.grid(row=2, column=0, sticky="w", pady=(0, 8))

        table_frame = tk.Frame(card, bg="white")
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("usuario", "nombre", "rol", "dni", "email", "telefono", "ciudad", "estado", "ultimo")
        self.user_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "usuario": "Usuario", "nombre": "Nombre y apellido", "rol": "Rol",
            "dni": "DNI", "email": "Email", "telefono": "Teléfono", "ciudad": "Ciudad",
            "estado": "Estado", "ultimo": "Último ingreso",
        }
        widths = {
            "usuario": 120, "nombre": 190, "rol": 110, "dni": 100,
            "email": 220, "telefono": 130, "ciudad": 130,
            "estado": 90, "ultimo": 150,
        }
        for col in columns:
            self.user_tree.heading(col, text=headings[col])
            self.user_tree.column(col, width=widths[col], minwidth=70, anchor="w", stretch=True)

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.user_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.user_tree.xview)
        self.user_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.user_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.user_tree.bind("<Double-1>", lambda _e: self.modify_user())

        actions = tk.Frame(card, bg="white")
        actions.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        for c in range(5):
            actions.grid_columnconfigure(c, weight=1, uniform="user_actions")

        buttons = [
            ("Nuevo usuario", self.add_user, "#2563eb", "white"),
            ("Editar", self.modify_user, "#fef9c3", "#111827"),
            ("Restablecer contraseña", self.reset_user_password, "#e0f2fe", "#0f172a"),
            ("Activar / Desactivar", self.toggle_user_active, "#e5e7eb", "#111827"),
            ("Eliminar", self.delete_user, "#ef4444", "white"),
        ]
        for idx, (text, command, bg, fg) in enumerate(buttons):
            tk.Button(
                actions, text=text, command=command, bg=bg, fg=fg,
                relief="flat", padx=8, pady=8, cursor="hand2",
            ).grid(row=0, column=idx, padx=4, sticky="ew")

        footer = tk.Frame(card, bg="white")
        footer.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        tk.Button(
            footer, text="Volver", command=self.back_to_admin,
            bg="#fef9c3", fg="#111827", relief="flat", padx=18, pady=9,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            footer, text="Salir", command=self.exit_program,
            bg="#ef4444", fg="white", relief="flat", padx=18, pady=9,
            cursor="hand2",
        ).pack(side="right")

        self.user_search_var.trace_add("write", lambda *_: self.refresh_user_management())
        role_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_user_management())
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_user_management())
        self.refresh_user_management()
        search_entry.focus_set()

    def refresh_user_management(self):
        tree = getattr(self, "user_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        selected = tree.selection()
        selected_id = selected[0] if selected else None
        for item in tree.get_children():
            tree.delete(item)

        rows = self.db_manager.fetch_users_for_management(
            getattr(self, "user_search_var", tk.StringVar(value="")).get(),
            getattr(self, "user_role_filter", tk.StringVar(value="Todos")).get(),
            getattr(self, "user_status_filter", tk.StringVar(value="Todos")).get(),
        )
        for row in rows:
            full_name = " ".join(part for part in (row["first_name"], row["last_name"]) if part).strip() or "—"
            role = "Administrador" if row["is_admin"] else "Usuario"
            status = "Activo" if row["is_active"] else "Inactivo"
            iid = str(row["id"])
            tree.insert(
                "", "end", iid=iid,
                values=(
                    row["username"], full_name, role, row["dni"] or "—",
                    row["email"] or "—", row["phone"] or "—", row["city"] or "—",
                    status, self._format_session_time(row["last_login"]),
                ),
            )
        if selected_id and tree.exists(selected_id):
            tree.selection_set(selected_id)
            tree.focus(selected_id)

    def _selected_user_id(self):
        tree = getattr(self, "user_tree", None)
        if tree is None or not tree.winfo_exists():
            return None
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Seleccionar usuario", "Seleccioná primero un usuario de la tabla.")
            return None
        return int(selection[0])

    def add_user(self):
        AddUserWindow(self.root, self.db_manager, self)

    def modify_user(self):
        user_id = self._selected_user_id()
        if user_id is None:
            return
        ModifyUserWindow(self.root, self.db_manager, self, user_id)

    def reset_user_password(self):
        user_id = self._selected_user_id()
        if user_id is None:
            return
        user = self.db_manager.get_user_by_id(user_id)
        if user is None:
            self.refresh_user_management()
            return
        p1 = simpledialog.askstring(
            "Restablecer contraseña", f"Nueva contraseña para {user['username']}:",
            show="*", parent=self.root,
        )
        if p1 is None:
            return
        if len(p1) < 8:
            messagebox.showerror("Contraseña débil", "La contraseña debe tener al menos 8 caracteres.")
            return
        p2 = simpledialog.askstring("Confirmar contraseña", "Repetí la nueva contraseña:", show="*", parent=self.root)
        if p2 != p1:
            messagebox.showerror("No coincide", "Las contraseñas no coinciden.")
            return
        self.db_manager.update_password(user_id, p1)
        self.db_manager.touch_session(self.current_session_id)
        messagebox.showinfo("Contraseña actualizada", "La contraseña se actualizó correctamente.")
        self.refresh_user_management()

    def toggle_user_active(self):
        user_id = self._selected_user_id()
        if user_id is None:
            return
        user = self.db_manager.get_user_by_id(user_id)
        if user is None:
            self.refresh_user_management()
            return
        if user_id == self.current_user_id and bool(user["is_active"]):
            messagebox.showerror("Operación no permitida", "No podés desactivar la cuenta con la que estás conectado.")
            return
        target = not bool(user["is_active"])
        ok, error = self.db_manager.set_user_active(user_id, target)
        if not ok:
            messagebox.showerror("Operación no permitida", error or "No se pudo cambiar el estado.")
            return
        self.db_manager.touch_session(self.current_session_id)
        messagebox.showinfo("Estado actualizado", f"Usuario {'activado' if target else 'desactivado'} correctamente.")
        self.refresh_user_management()

    def delete_user(self):
        user_id = self._selected_user_id()
        if user_id is None:
            return
        user = self.db_manager.get_user_by_id(user_id)
        if user is None:
            self.refresh_user_management()
            return
        if not messagebox.askyesno(
            "Eliminar usuario",
            f"¿Eliminar definitivamente al usuario '{user['username']}'?\n\n"
            "El historial de sesiones se conservará, pero la cuenta dejará de existir.",
            parent=self.root,
        ):
            return
        ok, error = self.db_manager.delete_user_safe(user_id, actor_user_id=self.current_user_id)
        if not ok:
            messagebox.showerror("No se puede eliminar", error or "No se pudo eliminar el usuario.")
            return
        self.db_manager.touch_session(self.current_session_id)
        messagebox.showinfo("Usuario eliminado", "El usuario fue eliminado correctamente.")
        self.refresh_user_management()
