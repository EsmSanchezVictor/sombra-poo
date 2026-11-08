"""Presentación del acceso a Sombra; la autenticación queda en MainApp."""
import tkinter as tk

from ui.startup import brand_photo, load_brand

from ui.theme import PALETA

BG = PALETA["background"]
INK = PALETA["texto"]
MUTED = PALETA["texto_suave"]
PURPLE = PALETA["primario"]
BORDER = PALETA["border"]


class LoginScreen(tk.Frame):
    def __init__(self, root, on_login, on_close):
        super().__init__(root, bg=BG)
        self.root = root
        self._resize_job = None
        self._logo_size = None
        self._project = load_brand("proyecto.png", trim=True)
        self._brand = load_brand("marca.png", trim=True)
        self._project_photo = self._brand_photo = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        exit_button = tk.Button(self, text="Salir", command=on_close, bg=BG, fg=INK,
                                activebackground="#eadff2", activeforeground=INK,
                                font=("Segoe UI", 10), relief="flat", padx=13, pady=4,
                                highlightthickness=1, highlightcolor=PURPLE,
                                highlightbackground=BG, cursor="hand2")
        exit_button.grid(row=0, column=0, sticky="e", padx=18, pady=(10, 0))
        stack = tk.Frame(self, bg=BG)
        stack.grid(row=1, column=0, pady=(0, 12))
        self.project_label = tk.Label(stack, text="Proyecto Sombra", bg=BG, fg=INK,
                                      font=("Segoe UI", 25, "bold"), borderwidth=0)
        self.project_label.pack(pady=(0, 14))

        card = tk.Frame(stack, bg="white", padx=24, pady=16, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack()
        card.columnconfigure(0, weight=1)
        tk.Label(card, text="Iniciar sesión", bg="white", fg=INK,
                 font=("Segoe UI", 17, "bold")).grid(row=0, column=0, pady=(0, 9))

        def field(label, row, **kwargs):
            tk.Label(card, text=label, bg="white", fg=INK, anchor="w",
                     font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
            entry = tk.Entry(card, width=29, font=("Segoe UI", 11), fg=INK, bg="#fdfbff",
                             insertbackground=INK, relief="flat", highlightthickness=1,
                             highlightcolor=PURPLE, highlightbackground=BORDER, **kwargs)
            entry.grid(row=row+1, column=0, sticky="ew", ipady=5, pady=(2, 8))
            entry.bind("<Return>", lambda _event: (on_login(), "break")[1])
            return entry

        self.username_entry = field("Usuario", 1)
        self.password_entry = field("Contraseña", 3, show="*")
        login_button = tk.Button(card, text="Ingresar", command=on_login, bg=PURPLE, fg="white",
                                 activebackground="#54206f", activeforeground="white",
                                 font=("Segoe UI", 11, "bold"), relief="flat", pady=7,
                                 highlightthickness=1, highlightbackground="white",
                                 highlightcolor=PURPLE, cursor="hand2")
        login_button.grid(row=5, column=0, sticky="ew", pady=(3, 0))
        tk.Label(stack, text="Desarrollado por", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(pady=(13, 3))
        self.brand_label = tk.Label(stack, text="3Esfera", bg=BG, fg=PURPLE,
                                    font=("Segoe UI", 14, "bold"), borderwidth=0)
        self.brand_label.pack()
        for widget in (self.username_entry, self.password_entry, login_button, exit_button):
            widget.bind("<Escape>", self._windowed)
            widget.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Configure>", self._schedule_logos)
        self.bind("<Destroy>", self._cancel_resize)
        self._resize_logos(root.winfo_screenwidth(), root.winfo_screenheight())
        self.username_entry.focus_set()

    def _windowed(self, _event=None):
        self.root.attributes("-fullscreen", False)
        return "break"

    def _toggle_fullscreen(self, _event=None):
        current = self.root.tk.getboolean(self.root.attributes("-fullscreen"))
        self.root.attributes("-fullscreen", not current)
        return "break"

    def _cancel_resize(self, event=None):
        if (event is None or event.widget is self) and self._resize_job is not None:
            self.after_cancel(self._resize_job)
            self._resize_job = None

    def _schedule_logos(self, event):
        self._cancel_resize()
        self._resize_job = self.after(60, self._resize_logos, event.width, event.height)

    def _resize_logos(self, width, height):
        self._resize_job = None
        if width < 100 or height < 100:
            return
        dimensions = (min(520, int(width*.76)), min(188, max(60, int(height*.23))),
                      min(165, int(width*.4)), min(48, max(24, int(height*.07))))
        if dimensions == self._logo_size:
            return
        self._logo_size = dimensions
        self._project_photo = brand_photo(self._project, self, *dimensions[:2])
        self._brand_photo = brand_photo(self._brand, self, *dimensions[2:])
        if self._project_photo is not None:
            self.project_label.configure(image=self._project_photo)
        if self._brand_photo is not None:
            self.brand_label.configure(image=self._brand_photo)
