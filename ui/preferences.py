"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from ui.modal_style import prepare_dialog

class PreferencesMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def open_preferences(self):
        preferences = tk.Toplevel(self.root)
        prepare_dialog(preferences, self.root, modal=False, resizable=False)
        preferences.title("Preferencias")
        preferences.resizable(False, False)
        preferences.configure(bg=self.palette["background"])

        ui_mode_var = tk.StringVar(value=self.settings.get("ui_mode", "simple"))
        temp_unit_var = tk.StringVar(value=self.settings.get("temp_unit", self.settings.get("units", "C")))
        distance_unit_var = tk.StringVar(value=self.settings.get("distance_unit", "m"))
        country_var = tk.StringVar(value=self.settings.get("default_country", "Argentina"))
        city_var = tk.StringVar(value=self.settings.get("default_city", "Paraná"))
        cloudiness_var = tk.StringVar(value=self.settings.get("default_cloudiness", "Despejado"))
        wind_var = tk.StringVar(value=self.settings.get("default_wind", "moderado"))
        tmrt_model_var = tk.StringVar(value=self.settings.get("tmrt_model_mode", "standard"))
        surface_model_var = tk.StringVar(value=self.settings.get("surface_model_mode", "standard"))
        ground_veg_var = tk.StringVar(value=str(self.settings.get("ground_vegetation_fraction", 0.50)))
        water_var = tk.StringVar(value=str(self.settings.get("vegetation_water_availability", 0.75)))
        canopy_water_var = tk.StringVar(value=str(self.settings.get("canopy_water_availability", 0.75)))

        header = ttk.Frame(preferences, padding=(18, 16, 18, 0))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Preferencias", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header, text="Configuración general de interfaz, unidades y modelos.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        card = tk.Frame(preferences, bg="white", padx=18, pady=14, bd=0, relief="flat")
        card.grid(row=1, column=0, padx=18, pady=(8, 16))

        tk.Label(card, text="Unidades", bg="white", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(card, textvariable=temp_unit_var, values=["C", "F", "K"], state="readonly", width=10).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Combobox(
            card, textvariable=distance_unit_var,
            values=["cm", "m", "km", "in", "ft", "yd", "mi"],
            state="readonly", width=10,
        ).grid(row=1, column=1, sticky="w")

        tk.Label(card, text="Modo de interfaz", bg="white", font=("Arial", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(card, text="Simple", variable=ui_mode_var, value="simple", bg="white").grid(
            row=3, column=0, sticky="w"
        )
        tk.Radiobutton(card, text="Detallado", variable=ui_mode_var, value="advanced", bg="white").grid(
            row=3, column=1, sticky="w"
        )

        tk.Label(card, text="Modelo térmico Tmrt", bg="white", font=("Arial", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(
            card, text="Estándar (empírico, predeterminado)",
            variable=tmrt_model_var, value="standard", bg="white",
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado (balance radiativo v2)",
            variable=tmrt_model_var, value="advanced", bg="white",
        ).grid(row=6, column=0, columnspan=2, sticky="w")
        tk.Label(
            card,
            text=("El modelo avanzado usa GHI, DNI y DHI por separado y parámetros "
                  "radiativos humanos. Es más físico, pero todavía requiere validación local."),
            bg="white", fg="#666666", wraplength=380, justify="left", font=("Arial", 7),
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(card, text="Modelo térmico de superficies", bg="white", font=("Arial", 9, "bold")).grid(
            row=8, column=0, sticky="w", pady=(10, 0)
        )
        tk.Radiobutton(
            card, text="Estándar (linealizado, predeterminado)",
            variable=surface_model_var, value="standard", bg="white",
        ).grid(row=9, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado seco (balance energético v1)",
            variable=surface_model_var, value="advanced", bg="white",
        ).grid(row=10, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            card, text="Avanzado vegetación + ET (v2)",
            variable=surface_model_var, value="advanced_vegetation", bg="white",
        ).grid(row=11, column=0, columnspan=2, sticky="w")
        tk.Label(
            card,
            text=("v2 añade evapotranspiración de suelo vegetado mediante FAO-56 Penman-Monteith, "
                  "fenología de caducifolias y diagnóstico separado de transpiración de copa. "
                  "El estándar y el avanzado seco conservan sus resultados anteriores."),
            bg="white", fg="#666666", wraplength=380, justify="left", font=("Arial", 7),
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(card, text="Fracción de suelo vegetado (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=13, column=0, sticky="w", pady=(6, 0)
        )
        tk.Entry(card, textvariable=ground_veg_var, width=10).grid(row=13, column=1, sticky="w")
        tk.Label(card, text="Disponibilidad hídrica suelo (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=14, column=0, sticky="w"
        )
        tk.Entry(card, textvariable=water_var, width=10).grid(row=14, column=1, sticky="w")
        tk.Label(card, text="Disponibilidad hídrica copa (0-1)", bg="white", font=("Arial", 8, "bold")).grid(
            row=15, column=0, sticky="w"
        )
        tk.Entry(card, textvariable=canopy_water_var, width=10).grid(row=15, column=1, sticky="w")

        tk.Label(card, text="País por defecto", bg="white", font=("Arial", 9, "bold")).grid(
            row=16, column=0, sticky="w", pady=(10, 0)
        )
        if self.locations_data:
            country_combo = ttk.Combobox(
                card, textvariable=country_var, values=self.locations_data["countries"], width=22
            )
            country_combo.grid(row=17, column=0, columnspan=2, sticky="w")
        else:
            tk.Entry(card, textvariable=country_var, width=24).grid(row=17, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Ciudad por defecto", bg="white", font=("Arial", 9, "bold")).grid(
            row=18, column=0, sticky="w", pady=(10, 0)
        )
        if self.locations_data:
            city_combo = ttk.Combobox(card, textvariable=city_var, width=22)
            city_combo.grid(row=19, column=0, columnspan=2, sticky="w")
            if country_var.get() in self.locations_data["cities"]:
                city_combo["values"] = self.locations_data["cities"][country_var.get()]

            def update_city_options(*_args):
                cities = self.locations_data["cities"].get(country_var.get(), [])
                city_combo["values"] = cities
                if cities and city_var.get() not in cities:
                    city_var.set(cities[0])

            country_combo.bind("<<ComboboxSelected>>", update_city_options)
        else:
            tk.Entry(card, textvariable=city_var, width=24).grid(row=19, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Nubosidad", bg="white", font=("Arial", 9, "bold")).grid(
            row=20, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Combobox(
            card, textvariable=cloudiness_var, values=["Despejado", "Parcial", "Nublado"], width=22
        ).grid(row=21, column=0, columnspan=2, sticky="w")

        tk.Label(card, text="Viento", bg="white", font=("Arial", 9, "bold")).grid(
            row=22, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Combobox(
            card, textvariable=wind_var, values=["nulo", "moderado", "fuerte"], width=22
        ).grid(row=23, column=0, columnspan=2, sticky="w")

        def save_preferences():
            try:
                ground_veg = float(ground_veg_var.get().replace(",", "."))
                water = float(water_var.get().replace(",", "."))
                canopy_water = float(canopy_water_var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Vegetación", "Las fracciones de vegetación/agua deben ser numéricas.", parent=preferences)
                return
            if not all(0.0 <= v <= 1.0 for v in (ground_veg, water, canopy_water)):
                messagebox.showerror("Vegetación", "Las fracciones de vegetación/agua deben estar entre 0 y 1.", parent=preferences)
                return
            self.settings.update(
                {
                    "ui_mode": ui_mode_var.get(),
                    "units": temp_unit_var.get(),
                    "temp_unit": temp_unit_var.get(),
                    "distance_unit": distance_unit_var.get(),
                    "default_country": country_var.get(),
                    "default_city": city_var.get(),
                    "default_cloudiness": cloudiness_var.get(),
                    "default_wind": wind_var.get(),
                    "tmrt_model_mode": tmrt_model_var.get(),
                    "surface_model_mode": surface_model_var.get(),
                    "ground_vegetation_fraction": ground_veg,
                    "vegetation_water_availability": water,
                    "canopy_water_availability": canopy_water,
                }
            )
            self.settings_manager.write(self.settings)
            self.apply_settings(self.settings)
            preferences.destroy()

        actions = tk.Frame(card, bg="white")
        actions.grid(row=24, column=0, columnspan=2, pady=(12, 0), sticky="e")
        tk.Button(actions, text="Guardar", command=save_preferences).grid(row=0, column=0, padx=(0, 8))
        tk.Button(actions, text="Cancelar", command=preferences.destroy).grid(row=0, column=1)
