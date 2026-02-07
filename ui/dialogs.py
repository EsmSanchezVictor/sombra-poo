"""Diálogos modales para creación de proyectos."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk


def ask_project_name(root: tk.Tk) -> str | None:
    """Solicita el nombre del proyecto."""
    return simpledialog.askstring("Nuevo proyecto", "Ingrese el nombre del proyecto:", parent=root)


def ask_project_location(root: tk.Tk, locations_data: dict | None) -> dict | None:
    """Solicita la ubicación (país/ciudad) usando combobox con búsqueda."""
    if not locations_data:
        return None

    result: dict | None = None
    dialog = tk.Toplevel(root)
    dialog.title("Ubicación del proyecto")
    dialog.transient(root)
    dialog.grab_set()

    dialog.columnconfigure(1, weight=1)

    tk.Label(dialog, text="País").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
    country_var = tk.StringVar(value=locations_data["countries"][0] if locations_data["countries"] else "")
    country_combo = ttk.Combobox(
        dialog,
        textvariable=country_var,
        values=locations_data["countries"],
        state="readonly",
        width=28,
    )
    country_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))

    tk.Label(dialog, text="Ciudad").grid(row=1, column=0, sticky="w", padx=10, pady=4)
    city_var = tk.StringVar()
    city_combo = ttk.Combobox(dialog, textvariable=city_var, values=[], width=28)
    city_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=4)

    tk.Label(dialog, text="Buscar").grid(row=2, column=0, sticky="w", padx=10, pady=4)
    search_var = tk.StringVar()
    search_entry = tk.Entry(dialog, textvariable=search_var)
    search_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=4)

    def update_cities(*_args):
        country = country_var.get()
        cities = locations_data["cities"].get(country, [])
        city_combo["values"] = cities
        if cities:
            city_var.set(cities[0])

    def filter_cities(*_args):
        country = country_var.get()
        query = search_var.get().lower().strip()
        cities = locations_data["cities"].get(country, [])
        if query:
            filtered = [city for city in cities if query in city.lower()]
        else:
            filtered = cities
        city_combo["values"] = filtered
        if filtered:
            city_var.set(filtered[0])

    def on_accept():
        nonlocal result
        city_label = city_var.get().strip()
        location = locations_data["lookup"].get(city_label)
        if location:
            result = location
            dialog.destroy()

    def on_cancel():
        dialog.destroy()

    country_combo.bind("<<ComboboxSelected>>", lambda _e: update_cities())
    city_combo.bind("<<ComboboxSelected>>", lambda _e: search_var.set(""))
    search_entry.bind("<KeyRelease>", lambda _e: filter_cities())

    update_cities()

    button_frame = tk.Frame(dialog)
    button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 12))
    tk.Button(button_frame, text="Aceptar", command=on_accept, width=12).pack(side=tk.LEFT, padx=6)
    tk.Button(button_frame, text="Cancelar", command=on_cancel, width=12).pack(side=tk.LEFT, padx=6)

    dialog.wait_window()
    return result