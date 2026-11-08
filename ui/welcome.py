"""Bienvenida del escritorio, antes de que exista un proyecto activo."""
import tkinter as tk
from tkinter import ttk

from ui.startup import brand_photo, load_brand
from ui.theme import FONT


def build_welcome(parent, palette, *, create, open_project, import_project):
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    card = tk.Frame(parent, bg=palette["panel"], highlightthickness=1,
                    highlightbackground=palette["border"])
    card.grid(row=0, column=0, padx=16, pady=16)
    card.columnconfigure(0, weight=1)
    width = min(360, max(220, parent.winfo_screenwidth() - 150))

    logo = brand_photo(load_brand("proyecto.png", trim=True), card, width, 130)
    project = tk.Label(card, image=logo or "", text="" if logo else "Proyecto Sombra",
                       font=(FONT, 24, "bold"), borderwidth=0)
    project.image = logo
    project.grid(row=0, column=0, padx=32, pady=(28, 16))

    ttk.Label(card, text="Empezá con un proyecto", style="Heading.TLabel").grid(row=1, column=0)
    ttk.Label(card, text="Simulá sombra, microclima urbano y confort térmico.",
              style="Muted.TLabel", wraplength=width, justify="center").grid(
        row=2, column=0, padx=20, pady=(5, 20))

    actions = ttk.Frame(card)
    actions.grid(row=3, column=0, padx=28, sticky="ew")
    actions.columnconfigure(0, weight=1, uniform="action")
    actions.columnconfigure(1, weight=1, uniform="action")
    primary = ttk.Button(actions, text="Crear proyecto", style="WelcomePrimary.TButton", command=create)
    primary.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ttk.Button(actions, text="Abrir proyecto", style="WelcomeSecondary.TButton", command=open_project).grid(
        row=0, column=1, sticky="ew", padx=(6, 0))
    ttk.Button(card, text="Importar archivo .3es", command=import_project).grid(row=4, column=0, pady=(12, 20))

    ttk.Separator(card).grid(row=5, column=0, padx=28, sticky="ew")
    brand = brand_photo(load_brand("marca.png", trim=True), card, 118, 34)
    company = tk.Label(card, image=brand or "", text="" if brand else "3Esfera",
                       fg=palette["texto_suave"], borderwidth=0)
    company.image = brand
    company.grid(row=6, column=0, pady=(14, 18))
    return primary
