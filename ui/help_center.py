"""Ventana de créditos y documentos locales de Proyecto Sombra."""
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from core.app_version import APP_RELEASE
from core.runtime_paths import resource_path
from ui.modal_style import prepare_dialog
from ui.startup import brand_photo, load_brand
from ui.theme import FONT, PALETA


COMPLETE_MANUAL = "MANUAL_SOMBRA.html"
QUICK_MANUAL = "GUIA_RAPIDA_SOMBRA.html"
PILOT_LICENSE = "LICENCIA_PROYECTO_SOMBRA.txt"
AUTHOR = "Víctor Daniel Sánchez"


def open_document(root: tk.Misc, filename: str) -> None:
    path: Path = resource_path("docs", filename)
    if not path.is_file():
        messagebox.showwarning("Ayuda de Proyecto Sombra",
                               f"No se encontró el documento en:\n{path}", parent=root)
        return
    try:
        if webbrowser.open(path.as_uri()):
            return
    except (OSError, webbrowser.Error):
        pass
    messagebox.showinfo("Ayuda de Proyecto Sombra",
                        f"Abrí este archivo con tu navegador:\n{path}", parent=root)


def show_about(app) -> None:
    current = getattr(app, "_about_window", None)
    if current is not None and current.winfo_exists():
        current.deiconify()
        current.lift()
        return

    window = tk.Toplevel(app.root)
    app._about_window = window
    window.title("Acerca de Proyecto Sombra")
    prepare_dialog(window, app.root, resizable=False)
    window.configure(bg=PALETA["background"])
    card = ttk.Frame(window, padding=(24, 18))
    card.pack(fill="both", expand=True, padx=12, pady=12)

    logo = brand_photo(load_brand("proyecto.png", trim=True), window, 270, 92)
    if logo:
        window.project_logo = logo
        ttk.Label(card, image=logo).pack(anchor="w", pady=(0, 8))
    ttk.Label(card, text="Proyecto Sombra", style="Heading.TLabel").pack(anchor="w")
    ttk.Label(card, text=f"{APP_RELEASE} · Edición piloto",
              style="DialogSection.TLabel").pack(anchor="w", pady=(4, 8))
    ttk.Label(card, text="Simulación de sombra y microclima urbano para comparar "
              "escenarios con arbolado y estructuras, mediante fotografías y vistas 2D y 3D.",
              wraplength=420, justify="left").pack(anchor="w")
    ttk.Separator(card).pack(fill="x", pady=(13, 11))
    ttk.Label(card, text=f"Autor y titular de los componentes propios: {AUTHOR}",
              font=(FONT, 9, "bold"), wraplength=420, justify="left").pack(anchor="w")
    ttk.Label(card, text="Técnico Universitario · © 2026. Todos los derechos reservados.",
              style="Muted.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(3, 11))

    scope = tk.Frame(card, bg=PALETA["accent"], padx=12, pady=9)
    scope.pack(fill="x")
    tk.Label(scope, text="Validación de campo pendiente", bg=PALETA["accent"],
             fg=PALETA["primario"], font=(FONT, 9, "bold")).pack(anchor="w")
    tk.Label(scope, text="Resultados estimados para evaluación, docencia e investigación. "
             "Contrastá con mediciones antes de basar una decisión técnica en ellos.",
             bg=PALETA["accent"], fg=PALETA["texto"], justify="left",
             wraplength=396).pack(anchor="w", pady=(4, 0))

    actions = ttk.Frame(card)
    actions.pack(fill="x", pady=(14, 7))
    ttk.Button(actions, text="Guía rápida", style="DialogPrimary.TButton",
               command=lambda: open_document(window, QUICK_MANUAL)).pack(side="left", padx=(0, 7))
    ttk.Button(actions, text="Manual completo",
               command=lambda: open_document(window, COMPLETE_MANUAL)).pack(side="left")
    footer = ttk.Frame(card)
    footer.pack(fill="x")
    ttk.Button(footer, text="Licencia piloto",
               command=lambda: open_document(window, PILOT_LICENSE)).pack(side="left")
    close = ttk.Button(footer, text="Cerrar", command=window.destroy)
    close.pack(side="right")
    close.focus_set()
