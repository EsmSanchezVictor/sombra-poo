"""Diálogos de herramientas de análisis térmico, extraídos de SombraApp
(ui/app_ui.py) — refactor por controladores (README_CAMBIOS.md §6).

`HerramientasDialogs` recibe la app en el constructor y opera sobre
`self.app.<atributo>`; SombraApp conserva los seis métodos `_dialogo_*`
como bound methods (asignados en __init__) para que menú, ribbon y
Panel 4 no cambien.
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core import scenario as scenario_tools
from core import thermal_comfort
from core.climate_profile import viento_categoria_a_ms
from core.species import (
    eliminar_especie, guardar_especie, nombres_especies,
    propiedades_especie, validar_especie,
)
from core.validation import k_factor_desde_mediciones, leer_csv_mediciones, metricas
from shadow_temp import Temperatura


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


class HerramientasDialogs:
    def __init__(self, app):
        self.app = app

    # ---------------------------------------------------------------- calibrador

    def _dialogo_calibrar_k_factor(self):
        """Asistente de calibración: ingresa mediciones de campo
        (temperatura de globo o Tmrt, temperatura de aire, radiación,
        viento), ajusta k_factor por mínimos cuadrados y lo persiste en
        settings.json para que todo el modelo lo use."""
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Asistente de calibración de k_factor")
        dlg.geometry("640x520")
        dlg.transient(self.app.root)

        intro = ("k_factor convierte la radiación efectiva en elevación de Tmrt "
                 "(Tmrt = Ta + k·GHI). Ingresá mediciones de campo y el asistente "
                 "ajusta k por mínimos cuadrados. Los cambios se aplican a todo el modelo.")
        tk.Label(dlg, text=intro, wraplength=600, justify="left").pack(padx=12, pady=8)

        cuerpo = tk.Frame(dlg)
        cuerpo.pack(fill="both", expand=True, padx=12)
        cuerpo.grid_columnconfigure(1, weight=1)

        entradas = {}
        fila = 0
        for i, (texto, clave, por_defecto) in enumerate([
            ("Tg globo (°C)", "tg", ""),
            ("Ta aire (°C)", "ta", "30.0"),
            ("Radiación (W/m²)", "rad", "750.0"),
            ("Viento (m/s)", "v", "0.5"),
        ]):
            tk.Label(cuerpo, text=texto).grid(row=fila, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=por_defecto)
            entradas[clave] = var
            tk.Entry(cuerpo, textvariable=var).grid(row=fila, column=1, sticky="ew", pady=2)
            fila += 1

        botones = tk.Frame(cuerpo)
        botones.grid(row=fila, column=0, columnspan=2, sticky="ew", pady=6)
        tk.Button(botones, text="Agregar medición",
                  command=lambda: self._calibrador_agregar(entradas, lista, error_lbl)).pack(side="left")
        tk.Button(botones, text="Quitar seleccionada",
                  command=lambda: self._calibrador_quitar(lista, error_lbl)).pack(side="left", padx=6)
        tk.Button(botones, text="Calcular",
                  command=lambda: self._calibrador_calcular(lista, resultado, error_lbl)).pack(side="right")
        fila += 1

        lista = tk.Listbox(cuerpo, height=6)
        lista.grid(row=fila, column=0, columnspan=2, sticky="nsew", pady=4)
        cuerpo.grid_rowconfigure(fila, weight=1)
        fila += 1

        error_lbl = tk.Label(cuerpo, text="", fg="red", justify="left", anchor="w")
        error_lbl.grid(row=fila, column=0, columnspan=2, sticky="ew")
        fila += 1

        resultado = tk.Label(cuerpo, text="", justify="left", anchor="w", fg="#1565C0")
        resultado.grid(row=fila, column=0, columnspan=2, sticky="ew", pady=4)
        fila += 1

        pie = tk.Frame(dlg)
        pie.pack(fill="x", padx=12, pady=8)
        k_actual = f"k_factor actual: {self.app.k_factor:.4f}"
        if self.app.k_factor_info:
            k_actual += f"  (calibrado {self.app.k_factor_info})"
        tk.Label(pie, text=k_actual).pack(side="left")
        tk.Button(pie, text="Aplicar y guardar",
                  command=lambda: self._calibrador_aplicar(resultado, dlg)).pack(side="right")
        tk.Button(pie, text="Cerrar", command=dlg.destroy).pack(side="right", padx=6)

    def _calibrador_agregar(self, entradas, lista, error_lbl):
        error_lbl.config(text="")
        try:
            fila = {k: float(entradas[k].get().replace(",", ".").strip())
                    for k in ("tg", "ta", "rad", "v")}
        except ValueError:
            error_lbl.config(text="Completá los 4 campos con números válidos.")
            return
        if fila["rad"] <= 0:
            error_lbl.config(text="La radiación debe ser mayor a 0 W/m².")
            return
        if fila["tg"] <= fila["ta"]:
            error_lbl.config(text="Tg debe ser mayor que Ta (el globo se calienta por radiación).")
            return
        lista.insert("end",
                     f"Tg={fila['tg']:.1f}°C  Ta={fila['ta']:.1f}°C  "
                     f"rad={fila['rad']:.0f} W/m²  v={fila['v']:.1f} m/s")

    def _calibrador_quitar(self, lista, error_lbl):
        error_lbl.config(text="")
        sel = lista.curselection()
        if not sel:
            error_lbl.config(text="Seleccioná una medición de la lista para quitar.")
            return
        lista.delete(sel[0])

    def _calibrador_calcular(self, lista, resultado, error_lbl):
        error_lbl.config(text="")
        if lista.size() < 2:
            error_lbl.config(text="Agregá al menos 2 mediciones para ajustar k_factor.")
            return
        import re
        filas = []
        for i in range(lista.size()):
            valores = {k.lower(): float(v) for k, v in
                       re.findall(r"([A-Za-z]+)=(-?[\d.]+)", lista.get(i))}
            try:
                tg, ta, rad, v = valores["tg"], valores["ta"], valores["rad"], valores["v"]
            except KeyError:
                error_lbl.config(text="La lista de mediciones está corrupta; quitá y volvé a agregar.")
                return
            tmrt = thermal_comfort.globo_negro_a_tmrt(tg, ta, v)
            filas.append({"tmrt_medido": tmrt, "ta": ta, "rad": rad, "v": v, "tg": tg})
        ajuste = k_factor_desde_mediciones(filas)
        texto = (f"k_factor ajustado: {ajuste['k_factor']:.5f}  "
                 f"R²: {ajuste['r2']:.3f}  RMSE: {ajuste['rmse']:.2f} °C  "
                 f"(n={ajuste['n']})")
        texto += "\nTmrt del globo por medición: " + ", ".join(
            f"{f['tmrt_medido']:.1f}" for f in filas)
        resultado.config(text=texto)
        # el dict se guarda en el propio widget para aplicarlo después
        resultado.ajuste = ajuste

    def _calibrador_aplicar(self, resultado, dlg):
        ajuste = getattr(resultado, "ajuste", None)
        if not ajuste:
            messagebox.showwarning("Sin resultados", "Calculá primero el ajuste.")
            return
        self.app.k_factor = ajuste["k_factor"]
        self.app.settings["k_factor"] = ajuste["k_factor"]
        self.app.settings["k_factor_info"] = (
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}, n={ajuste['n']}")
        self.app.settings_manager.write(self.app.settings)
        messagebox.showinfo(
            "Calibrado",
            f"k_factor = {ajuste['k_factor']:.5f}\n"
            f"R² = {ajuste['r2']:.3f} · RMSE = {ajuste['rmse']:.2f} °C\n\n"
            "Se guardó en settings.json y se aplicó a todo el modelo.\n"
            "Ejecutá el modelo de nuevo (F5) para ver el efecto.")
        dlg.destroy()

    # ---------------------------------------------------------------- confort

    def _dialogo_confort(self):
        """Índices de confort para las condiciones actuales: Heat Index
        (NWS/Rothfusz), Temperatura Aparente (Steadman) y UTCI oficial
        (si pythermalcomfort está instalada), en sol y en sombra, más la
        clasificación de estrés del mapa de Tmrt si el modelo ya se
        ejecutó."""
        temp_ambient, hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        rh = float(self.app.simple_rh.get() or 60.0)
        if rh < 0 or rh > 100:
            messagebox.showwarning("Humedad", "La humedad relativa debe estar entre 0 y 100.")
            return
        v_ms = viento_categoria_a_ms(self.app.vars_modelo["viento"].get())
        calculador = Temperatura(lat, lon, k_factor=self.app.k_factor)
        doy = fecha.timetuple().tm_yday
        elev = calculador.solar_altitude(doy, hora)
        ghi = calculador.clear_sky_radiation(elev)
        sombra_pct = 50.0
        if self.app.last_shadow is not None:
            sombra_pct = (1 - np.asarray(self.app.last_shadow, dtype=float)).mean() * 100

        tau = calculador.shadow_transmittance(sombra_pct, "tree")
        tmrt_sol = temp_ambient + self.app.k_factor * ghi
        tmrt_sombra = temp_ambient + self.app.k_factor * ghi * tau
        hi_sol = thermal_comfort.indice_calor(max(tmrt_sol, temp_ambient), rh)
        hi_sombra = thermal_comfort.indice_calor(max(tmrt_sombra, temp_ambient), rh)
        at_sol = thermal_comfort.temperatura_aparente(tmrt_sol, rh, v_ms)
        at_sombra = thermal_comfort.temperatura_aparente(tmrt_sombra, rh, v_ms)

        lineas = [
            f"Condiciones: Ta={temp_ambient:.1f}°C · RH={rh:.0f}% · viento={v_ms:.1f} m/s "
            f"· GHI={ghi:.0f} W/m² · % sombra={sombra_pct:.0f}%",
            "",
            f"Tmrt sol = {tmrt_sol:.1f} °C     Tmrt sombra = {tmrt_sombra:.1f} °C",
            f"Heat Index sol = {hi_sol:.1f} °C ({thermal_comfort.categoria_estres(hi_sol, 'heat')})",
            f"Heat Index sombra = {hi_sombra:.1f} °C ({thermal_comfort.categoria_estres(hi_sombra, 'heat')})",
            f"T. aparente sol = {at_sol:.1f} °C ({thermal_comfort.categoria_estres(at_sol, 'at')})",
            f"T. aparente sombra = {at_sombra:.1f} °C ({thermal_comfort.categoria_estres(at_sombra, 'at')})",
        ]
        if thermal_comfort.UTCI_DISPONIBLE:
            utci_sol = thermal_comfort.utci(temp_ambient, tmrt_sol, v_ms, rh)
            utci_sombra = thermal_comfort.utci(temp_ambient, tmrt_sombra, v_ms, rh)
            lineas += [
                f"UTCI sol = {utci_sol:.1f} °C ({thermal_comfort.categoria_utci(utci_sol)})",
                f"UTCI sombra = {utci_sombra:.1f} °C ({thermal_comfort.categoria_utci(utci_sombra)})",
            ]
        else:
            lineas += [
                "UTCI: no disponible — falta la librería pythermalcomfort "
                "(pip install pythermalcomfort).",
            ]
        if self.app.last_T is not None:
            try:
                mapa = scenario_tools.mapa_estres(
                    np.asarray(self.app.last_T, dtype=float), temp_ambient, rh)
                por_area = ", ".join(f"{k}: {v}%" for k, v in mapa["por_area"].items())
                lineas += ["", f"Mapa de Tmrt (modelo ya ejecutado): {por_area}"]
            except ValueError:
                pass
        lineas += [
            "",
            "Heat Index: índice operativo del NWS (Rothfusz 1990), válido "
            "para Ta ≥ 26.7 °C. Temperatura Aparente: Steadman (1984). "
            "UTCI: Bröde et al. (2012), modelo de Fiala vía pythermalcomfort.",
        ]
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Confort térmico")
        dlg.geometry("560x420")
        dlg.transient(self.app.root)
        tk.Label(dlg, text="\n".join(lineas), justify="left", anchor="w").pack(
            fill="both", expand=True, padx=14, pady=12)
        tk.Button(dlg, text="Cerrar", command=dlg.destroy).pack(pady=8)

    # ---------------------------------------------------------------- escenario A/B

    def _dialogo_escenario_ab(self):
        """Escenario A/B horario: comparar dos % de sombra (p. ej. línea
        base vs. propuesta de arbolado) a lo largo del día, con curvas de
        Heat Index, Tmrt, banda de incertidumbre de k ±20% y resumen de
        grados-hora de estrés."""
        temp_ambient, _hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Escenario A/B horario (sombra vs. propuesta)")
        dlg.geometry("720x640")
        dlg.transient(self.app.root)

        form = tk.Frame(dlg)
        form.pack(fill="x", padx=12, pady=8)
        form.grid_columnconfigure(1, weight=1)
        defaults = {
            "hora_ini": "8", "hora_fin": "18",
            "ta_min": "20", "ta_max": str(round(temp_ambient, 1)),
            "rh": str(self.app.simple_rh.get() or 60),
            "sombra_a": "20", "sombra_b": "60",
        }
        vars_ab = {}
        fila = 0
        for texto, clave, ancho in [
            ("Hora inicio", "hora_ini", 8), ("Hora fin", "hora_fin", 8),
            ("Ta mín (°C)", "ta_min", 8), ("Ta máx (°C)", "ta_max", 8),
            ("Humedad (%)", "rh", 8), ("Sombra A (%)", "sombra_a", 8),
            ("Sombra B (%)", "sombra_b", 8),
        ]:
            tk.Label(form, text=texto).grid(row=fila // 2, column=(fila % 2) * 2, sticky="w", padx=(0, 4), pady=2)
            var = tk.StringVar(value=defaults[clave])
            vars_ab[clave] = var
            tk.Entry(form, textvariable=var, width=ancho).grid(
                row=fila // 2, column=(fila % 2) * 2 + 1, sticky="ew", pady=2)
            fila += 1

        tk.Label(form, text="Viento:", justify="left").grid(row=4, column=0, sticky="w", padx=(0, 4))
        viento_var = tk.StringVar(value=self.app.vars_modelo["viento"].get())
        ttk.Combobox(form, textvariable=viento_var, values=["nulo", "moderado", "fuerte"],
                     width=8, state="readonly").grid(row=4, column=1, sticky="w")

        fig = plt.Figure(figsize=(6.6, 3.6), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12)

        resumen_txt = tk.Label(dlg, text="", justify="left", anchor="w", font=("Consolas", 8))
        resumen_txt.pack(fill="x", padx=12)

        def calcular():
            try:
                datos = {k: float(v.get().replace(",", ".").strip()) for k, v in vars_ab.items()}
                datos["viento"] = viento_categoria_a_ms(viento_var.get())
            except ValueError:
                messagebox.showwarning("Entrada", "Revisá los valores numéricos.", parent=dlg)
                return
            horas = [float(h) for h in
                     np.arange(datos["hora_ini"], datos["hora_fin"] + 1)]
            calc = Temperatura(lat, lon, k_factor=self.app.k_factor)
            esc_a = scenario_tools.escenario_horario(
                calc, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_a"])
            esc_b = scenario_tools.escenario_horario(
                calc, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"])
            cmp = scenario_tools.comparar_escenarios(esc_a, esc_b)
            # banda de incertidumbre: k ± 20% (sensibilidad típica del
            # coeficiente de calibración; si se calibró con CSV se
            # reporta también el RMSE del ajuste en el resumen)
            k_lo = self.app.k_factor * 0.8
            k_hi = self.app.k_factor * 1.2
            calc_lo = Temperatura(lat, lon, k_factor=k_lo)
            calc_hi = Temperatura(lat, lon, k_factor=k_hi)
            esc_b_lo = scenario_tools.escenario_horario(
                calc_lo, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"])
            esc_b_hi = scenario_tools.escenario_horario(
                calc_hi, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"])
            hi_lo = [r["hi_sombra"] for r in esc_b_lo]
            hi_hi = [r["hi_sombra"] for r in esc_b_hi]
            ax.clear()
            ax.plot(horas, [r["hi_sombra"] for r in esc_a], "o-", color="#E53935",
                    label=f"HI sombra A ({datos['sombra_a']:.0f}%)")
            ax.plot(horas, [r["hi_sombra"] for r in esc_b], "s-", color="#1E88E5",
                    label=f"HI sombra B ({datos['sombra_b']:.0f}%)")
            ax.fill_between(horas, hi_lo, hi_hi, color="#1E88E5", alpha=0.15,
                            label=f"incertidumbre k ±20% ({k_lo:.4f}–{k_hi:.4f})")
            ax.plot(horas, [r["hi_sol"] for r in esc_a], "--", color="#FB8C00",
                    label="HI pleno sol")
            ax.axhline(scenario_tools.UMBRAL_HI, color="gray", linestyle=":")
            ax.text(horas[0], scenario_tools.UMBRAL_HI + 0.3,
                    f"umbral estrés {scenario_tools.UMBRAL_HI:.1f} °C", fontsize=7)
            ax.set_xlabel("Hora")
            ax.set_ylabel("Heat Index (°C)")
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            canvas.draw()
            r = cmp["propuesto"]
            ancho_banda = max(hi_hi) - max(hi_lo)
            k_info = f" · calibrado {self.app.k_factor_info}" if self.app.k_factor_info else ""
            utci_linea = ""
            if r["utci_max_sombra"] is not None:
                utci_linea = (f"\nUTCI: pico sol {r['utci_max_sol']:.1f} °C "
                              f"({r['utci_categoria_sol']}) · sombra "
                              f"{r['utci_max_sombra']:.1f} °C ({r['utci_categoria_sombra']})")
            resumen_txt.config(text=(
                f"A: pico HI {r['hi_max_sombra']:.1f} °C · grados-hora (HI>{scenario_tools.UMBRAL_HI:.0f}) "
                f"{r['grados_hora_hi_sombra']:.1f} °C·h · categoría: {r['categoria_pico_sombra']}\n"
                f"Δ al pasar de A a B: HI pico {cmp['delta_hi_max']:+.1f} °C · "
                f"grados-hora {cmp['delta_grados_hora_hi']:+.1f} °C·h · "
                f"ΔTmrt máx {r['delta_tmrt_max']:.1f} °C\n"
                f"Incertidumbre k ±20%: banda de {ancho_banda:.1f} °C en el pico{k_info}"
                f"{utci_linea}"))

        botones = tk.Frame(dlg)
        botones.pack(fill="x", padx=12, pady=8)
        tk.Button(botones, text="Calcular", command=calcular, bg="#4CAF50", fg="white",
                  font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(botones, text="Cerrar", command=dlg.destroy).pack(side="right")
        calcular()

    # ---------------------------------------------------------------- validación CSV

    def _dialogo_validar_csv(self):
        """Valida el modelo contra mediciones de campo en CSV (tg o tmrt,
        ta, rad, v) y opcionalmente recalibra k_factor desde el archivo."""
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Validación contra mediciones (CSV)")
        dlg.geometry("640x560")
        dlg.transient(self.app.root)

        top = tk.Frame(dlg)
        top.pack(fill="x", padx=12, pady=8)
        tk.Label(top, text="Archivo:").pack(side="left")
        archivo_lbl = tk.Label(top, text="(ninguno)", fg="gray")
        archivo_lbl.pack(side="left", padx=6)
        tk.Button(top, text="Seleccionar CSV…",
                  command=lambda: self._validar_cargar(archivo_lbl, resumen_txt, fig, canvas,
                                                       aplicar_btn, dlg)).pack(side="right")

        fig = plt.Figure(figsize=(6.4, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12)

        resumen_txt = tk.Label(dlg, text="", justify="left", anchor="w", font=("Consolas", 8))
        resumen_txt.pack(fill="x", padx=12)

        aplicar_btn = tk.Button(dlg, text="Aplicar k_factor sugerido",
                                state="disabled", bg="#2196F3", fg="white")
        aplicar_btn.pack(pady=6)
        aplicar_btn.config(command=lambda: self._validar_aplicar_k(aplicar_btn, dlg))
        tk.Button(dlg, text="Cerrar", command=dlg.destroy).pack(pady=4)

    def _validar_cargar(self, archivo_lbl, resumen_txt, fig, canvas, aplicar_btn, dlg):
        path = filedialog.askopenfilename(
            parent=dlg,
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            title="Seleccionar mediciones de campo")
        if not path:
            return
        try:
            filas = leer_csv_mediciones(path)
        except (ValueError, FileNotFoundError) as e:
            messagebox.showerror("CSV inválido",
                                 f"{e}\n\nColumnas esperadas: tg (o tmrt), ta, rad, "
                                 "v (opcional), hora (opcional).", parent=dlg)
            return
        obs = np.array([f["tmrt_medido"] for f in filas], dtype=float)
        pred = np.array([f["ta"] + self.app.k_factor * f["rad"] for f in filas], dtype=float)
        met = metricas(obs, pred)
        archivo_lbl.config(text=os.path.basename(path), fg="black")
        resumen_txt.config(text=(
            f"n={met['n']} · RMSE={met['rmse']:.2f} °C · MAE={met['mae']:.2f} °C · "
            f"bias={met['bias']:+.2f} °C · R²={met['r2']:.3f}  (k_factor actual {self.app.k_factor:.4f})"))
        try:
            ajuste = k_factor_desde_mediciones(filas)
            resumen_txt.config(text=resumen_txt.cget("text") +
                               f"\nk_factor sugerido por el CSV: {ajuste['k_factor']:.5f} "
                               f"(R²={ajuste['r2']:.3f}, RMSE={ajuste['rmse']:.2f} °C)")
            aplicar_btn.config(state="normal")
            aplicar_btn.sugerido = ajuste["k_factor"]
        except ValueError as e:
            aplicar_btn.config(state="disabled")
            messagebox.showwarning("Calibración", str(e), parent=dlg)
        ax = fig.axes[0]
        ax.clear()
        ax.scatter(obs, pred, alpha=0.7, s=28)
        lim = [min(float(obs.min()), float(pred.min())) - 1,
               max(float(obs.max()), float(pred.max())) + 1]
        ax.plot(lim, lim, "--", color="gray", label="1:1")
        ax.set_xlabel("Tmrt medida (°C)")
        ax.set_ylabel("Tmrt modelo (°C)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        canvas.draw()

    def _validar_aplicar_k(self, aplicar_btn, dlg):
        k = getattr(aplicar_btn, "sugerido", None)
        if k is None:
            return
        self.app.k_factor = k
        self.app.settings["k_factor"] = k
        self.app.settings["k_factor_info"] = "CSV de validación"
        self.app.settings_manager.write(self.app.settings)
        messagebox.showinfo("Calibrado", f"k_factor = {k:.5f} aplicado y guardado.", parent=dlg)

    # ---------------------------------------------------------------- especies y ranking

    def _dialogo_especies(self):
        """Biblioteca de especies con propiedades térmicas (transmitancia
        de copa, densidad, caducidad) y su referencia bibliográfica."""
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Biblioteca de especies")
        dlg.geometry("560x520")
        dlg.transient(self.app.root)
        tk.Label(dlg, text="Propiedades térmicas por especie (literatura de biometeorología urbana):",
                 anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        contenedor = tk.Frame(dlg)
        contenedor.pack(fill="both", expand=True, padx=12)
        canvas = tk.Canvas(contenedor, highlightthickness=0)
        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        interior = tk.Frame(canvas)
        interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        fila = 0
        for nombre in nombres_especies():
            p = propiedades_especie(nombre)
            frame = tk.LabelFrame(interior, text=nombre, padx=8, pady=4)
            frame.grid(row=fila, column=0, sticky="ew", pady=3)
            interior.grid_columnconfigure(0, weight=1)
            tk.Label(frame, justify="left", anchor="w", font=("Consolas", 8), text=(
                f"Densidad de copa: {p['rho_copa']:.2f}  Transmitancia: {p['transmitancia']:.2f}\n"
                f"Caducifolio: {'sí' if p['caducifolio'] else 'no'}  Albedo copa: {p['albedo_copa']:.2f}\n"
                f"Altura típica: {p['altura_tipica']:.0f} m  Radio copa: {p['radio_copa_tipico']:.0f} m\n"
                f"Ref.: {p['ref']}")).pack(anchor="w")
            fila += 1
        pie = tk.Frame(dlg)
        pie.pack(fill="x", padx=12, pady=8)
        tk.Button(pie, text="Editar base de especies…",
                  command=lambda: self._dialogo_editar_especies()).pack(side="right")
        tk.Button(pie, text="Cerrar", command=dlg.destroy).pack(side="right", padx=6)

    def _dialogo_editar_especies(self):
        """Editor de la base de especies: crear, editar y eliminar.
        Pide todos los campos necesarios (validados en core.species) y
        persiste en data/species_db.json; las vistas 3D y el editor de
        diseño usan la base resultante al instante."""
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Editar base de especies")
        dlg.geometry("740x560")
        dlg.transient(self.app.root)

        tk.Label(dlg, text=(
            "Creá, editá o eliminá especies. Las especies creadas o modificadas "
            "se guardan en data/species_db.json. Editar una especie original "
            "crea un override; eliminarla la restaura a su valor de fábrica."),
            wraplength=700, justify="left").pack(padx=12, pady=(10, 6))

        cuerpo = tk.Frame(dlg)
        cuerpo.pack(fill="both", expand=True, padx=12)

        izq = tk.Frame(cuerpo)
        izq.pack(side="left", fill="both", expand=True)
        tk.Label(izq, text="Especies:", anchor="w").pack(fill="x")
        lista = tk.Listbox(izq, height=18)
        lista.pack(fill="both", expand=True)

        def _refrescar(seleccionar=None):
            lista.delete(0, "end")
            for nombre in nombres_especies():
                lista.insert("end", nombre)
            if seleccionar is not None:
                for i in range(lista.size()):
                    if lista.get(i) == seleccionar:
                        lista.selection_set(i)
                        lista.see(i)
                        break

        _refrescar()
        botones_izq = tk.Frame(izq)
        botones_izq.pack(fill="x", pady=4)
        tk.Button(botones_izq, text="Nuevo", command=lambda: nuevo()).pack(side="left")
        tk.Button(botones_izq, text="Eliminar", command=lambda: eliminar()).pack(side="left", padx=6)

        der = tk.Frame(cuerpo)
        der.pack(side="left", fill="both", expand=True, padx=10)

        campos = [
            ("Nombre de la especie:", "nombre"),
            ("Densidad de copa (0-1):", "rho_copa"),
            ("Transmitancia de copa (0-1):", "transmitancia"),
            ("Caducifolia (pierde hoja en invierno):", "caducifolio"),
            ("Albedo de copa (0-1):", "albedo_copa"),
            ("Altura típica (m):", "altura_tipica"),
            ("Radio de copa típico (m):", "radio_copa_tipico"),
            ("Referencia bibliográfica:", "ref"),
        ]
        vars_form = {}
        fila = 0
        for texto, clave in campos:
            tk.Label(der, text=texto, anchor="w").grid(row=fila, column=0, sticky="w", pady=1)
            if clave == "nombre":
                var = tk.StringVar()
                entry = tk.Entry(der, textvariable=var)
            elif clave == "caducifolio":
                var = tk.StringVar(value="sí")
                entry = ttk.Combobox(der, textvariable=var, values=["sí", "no"],
                                     width=8, state="readonly")
            else:
                var = tk.StringVar()
                entry = tk.Entry(der, textvariable=var, width=16)
            vars_form[clave] = var
            entry.grid(row=fila, column=1, sticky="ew", pady=1)
            fila += 1
        der.grid_columnconfigure(1, weight=1)

        error_lbl = tk.Label(der, text="", fg="red", anchor="w", wraplength=320)
        error_lbl.grid(row=fila, column=0, columnspan=2, sticky="ew")
        fila += 1

        def cargar_seleccion():
            sel = lista.curselection()
            if not sel:
                return
            nombre = lista.get(sel[0])
            p = propiedades_especie(nombre)
            vars_form["nombre"].set(nombre)
            for clave in ("rho_copa", "transmitancia", "albedo_copa",
                          "altura_tipica", "radio_copa_tipico"):
                vars_form[clave].set(str(p[clave]))
            vars_form["caducifolio"].set("sí" if p["caducifolio"] else "no")
            vars_form["ref"].set(p["ref"])
            error_lbl.config(text="")

        lista.bind("<<ListboxSelect>>", lambda _e: cargar_seleccion())

        def nuevo():
            for var in vars_form.values():
                var.set("")
            vars_form["caducifolio"].set("sí")
            vars_form["rho_copa"].set("0.60")
            vars_form["transmitancia"].set("0.30")
            vars_form["albedo_copa"].set("0.18")
            lista.selection_clear(0, "end")
            error_lbl.config(text="")

        def guardar():
            props = {
                "rho_copa": vars_form["rho_copa"].get().replace(",", ".").strip(),
                "transmitancia": vars_form["transmitancia"].get().replace(",", ".").strip(),
                "caducifolio": vars_form["caducifolio"].get() == "sí",
                "albedo_copa": vars_form["albedo_copa"].get().replace(",", ".").strip(),
                "altura_tipica": vars_form["altura_tipica"].get().replace(",", ".").strip(),
                "radio_copa_tipico": vars_form["radio_copa_tipico"].get().replace(",", ".").strip(),
                "ref": vars_form["ref"].get().strip(),
            }
            nombre = vars_form["nombre"].get().strip()
            ok, error = validar_especie(nombre, props)
            if not ok:
                error_lbl.config(text=error)
                return
            guardar_especie(nombre, props)
            _refrescar(seleccionar=nombre)
            error_lbl.config(text="")
            messagebox.showinfo("Guardado",
                                f"“{nombre}” guardada en la base de especies.", parent=dlg)

        def eliminar():
            sel = lista.curselection()
            if not sel:
                return
            nombre = lista.get(sel[0])
            if not messagebox.askyesno("Eliminar",
                                       f"¿Eliminar “{nombre}” de la base de especies?",
                                       parent=dlg):
                return
            if eliminar_especie(nombre):
                _refrescar()
                error_lbl.config(text="")
            else:
                messagebox.showinfo(
                    "Especie original",
                    "“%s” es una especie original sin cambios propios; no hay nada que eliminar."
                    % nombre, parent=dlg)

        pie = tk.Frame(dlg)
        pie.pack(fill="x", padx=12, pady=8)
        tk.Button(pie, text="Guardar", bg="#4CAF50", fg="white",
                  command=guardar).pack(side="right")
        tk.Button(pie, text="Cerrar", command=dlg.destroy).pack(side="right", padx=6)

    def _dialogo_ranking_arboles(self):
        """Ranking de efectividad de los árboles de la escena de diseño:
        área de sombra proyectada a la fecha/hora actuales y su aporte a
        la reducción de Tmrt promedio (k·GHI·(1−transmitancia))."""
        arboles = list(self.app.vars.get("arboles") or []) + list(
            self.app.vars_modelo.get("arboles") or [])
        vistos = set()
        unicos = []
        for a in arboles:
            clave = id(a)
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(a)
        if not unicos:
            messagebox.showinfo(
                "Ranking de árboles",
                "No hay árboles en la escena.\n\nAgregalos en el Panel 3 "
                "(Modo diseño) y volvé a intentar.")
            return
        temp_ambient, hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        calc = Temperatura(lat, lon, k_factor=self.app.k_factor)
        ranking = scenario_tools.ranking_arboles(unicos, calc, fecha, hora)

        dlg = tk.Toplevel(self.app.root)
        dlg.title("Efectividad de los árboles de la escena")
        dlg.geometry("700x520")
        dlg.transient(self.app.root)
        info = tk.Label(dlg, justify="left", anchor="w", font=("Consolas", 9), text=(
            f"Fecha {fecha} · hora {hora:.1f} · k_factor {self.app.k_factor:.4f}\n"
            f"Escena: {len(unicos)} árboles — sombra y ΔTmrt promedio calculados "
            "sobre la grilla de 60×60 m."))
        info.pack(fill="x", padx=12, pady=(10, 4))

        fig = plt.Figure(figsize=(6.6, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12)

        nombres = [f"Árbol {i + 1} (especie: {getattr(r['arbol'], 'especie', '—')})"
                   for i, r in enumerate(ranking)]
        ax.barh(range(len(ranking)), [r["delta_tmrt_prom"] for r in ranking],
                color="#1E88E5")
        ax.set_yticks(range(len(ranking)))
        ax.set_yticklabels(nombres, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("ΔTmrt promedio sobre la escena (°C)")
        ax.grid(True, alpha=0.3, axis="x")
        fig.tight_layout()
        canvas.draw()

        lineas = [f"{nombres[i]}: área {r['area_sombra_m2']:.1f} m² · "
                  f"cobertura {r['cobertura_frac'] * 100:.1f}% · "
                  f"ΔTmrt {r['delta_tmrt_prom']:.2f} °C"
                  for i, r in enumerate(ranking)]
        tk.Label(dlg, text="\n".join(lineas), justify="left", anchor="w",
                 font=("Consolas", 8)).pack(fill="x", padx=12)
        tk.Button(dlg, text="Cerrar", command=dlg.destroy).pack(pady=6)