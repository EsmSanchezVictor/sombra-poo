"""Diálogos de herramientas de análisis térmico, extraídos de SombraApp
(ui/app_ui.py) — refactor por controladores (README_CAMBIOS.md §6).

`HerramientasDialogs` recibe la app en el constructor y opera sobre
`self.app.<atributo>`; SombraApp conserva los seis métodos `_dialogo_*`
como bound methods (asignados en __init__) para que menú, ribbon y
Panel 4 no cambien.
"""
from __future__ import annotations

import os
import shutil
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
from core.scientific_audit import run_scientific_audit, format_audit_text, save_audit_json
from core.validation import (
    evaluar_modelos,
    exportar_reporte_validacion,
    guardar_plantilla_csv,
    k_factor_desde_mediciones,
    leer_csv_mediciones,
    metricas,
)
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
        """Confort térmico con variables físicamente compatibles.

        Heat Index y Temperatura Aparente se calculan con temperatura del aire;
        el efecto radiativo de la sombra se expresa mediante Tmrt y UTCI.
        """
        temp_ambient, hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        rh = float(self.app.simple_rh.get() or 60.0)
        if rh < 0 or rh > 100:
            messagebox.showwarning("Humedad", "La humedad relativa debe estar entre 0 y 100.")
            return
        v_ms = viento_categoria_a_ms(self.app.vars_modelo["viento"].get())
        tz_offset = self.app._offset_timezone(fecha, hora)
        calculador = Temperatura(
            lat, lon, k_factor=self.app.k_factor, tz_offset_hours=tz_offset,
            model_mode=self.app.tmrt_model_mode.get(),
        )
        solar_data = self.app._obtener_datos_solares(lat, lon, fecha, hora)
        ghi = float(solar_data["ghi"])

        sombra_pct = 50.0
        if self.app.porcentaje_sombra is not None:
            sombra_pct = float(self.app.porcentaje_sombra)
        elif self.app.last_shadow is not None:
            sombra_pct = (1 - np.asarray(self.app.last_shadow, dtype=float)).mean() * 100

        result = calculador.calculate_tmrt(
            temp_ambient,
            sombra_pct,
            "tree",
            date_value=fecha,
            time_value=hora,
            radiation_override=ghi,
            solar_altitude_override=solar_data["elevation"],
            dni_override=solar_data.get("dni"),
            dhi_override=solar_data.get("dhi"),
        )
        tmrt_sol = result["Tmrt_sol"]
        tmrt_sombra = result["Tmrt_sombra"]
        hi_air = thermal_comfort.indice_calor(temp_ambient, rh)
        at_air = thermal_comfort.temperatura_aparente(temp_ambient, rh, v_ms)

        lineas = [
            f"Condiciones: Ta={temp_ambient:.1f}°C · RH={rh:.0f}% · viento ref.={v_ms:.1f} m/s "
            f"· GHI={ghi:.0f} W/m² · sombra/índice={sombra_pct:.0f}%",
            f"Fuente solar: {solar_data.get('source', 'fallback')} · zona {solar_data.get('timezone', '')}",
            f"Modelo Tmrt: {result.get('Modelo_Tmrt_label', 'Estándar')}",
            "",
            f"Tmrt sol = {tmrt_sol:.1f} °C     Tmrt sombra = {tmrt_sombra:.1f} °C",
            f"Heat Index (aire) = {hi_air:.1f} °C ({thermal_comfort.categoria_estres(hi_air, 'heat')})",
            f"T. aparente (aire) = {at_air:.1f} °C ({thermal_comfort.categoria_estres(at_air, 'at')})",
        ]
        if thermal_comfort.UTCI_DISPONIBLE:
            utci_sol = thermal_comfort.utci(temp_ambient, tmrt_sol, v_ms, rh)
            utci_sombra = thermal_comfort.utci(temp_ambient, tmrt_sombra, v_ms, rh)
            lineas += [
                f"UTCI sol = {utci_sol:.1f} °C ({thermal_comfort.categoria_utci(utci_sol)})",
                f"UTCI sombra = {utci_sombra:.1f} °C ({thermal_comfort.categoria_utci(utci_sombra)})",
            ]
            if self.app.tmrt_map is not None:
                try:
                    mapa = scenario_tools.mapa_estres(
                        np.asarray(self.app.tmrt_map, dtype=float),
                        temp_ambient,
                        rh,
                        indice="utci",
                        v_ms=v_ms,
                    )
                    por_area = ", ".join(f"{k}: {v}%" for k, v in mapa["por_area"].items())
                    lineas += ["", f"Mapa UTCI derivado del mapa Tmrt: {por_area}"]
                except ValueError:
                    pass
        else:
            lineas += [
                "UTCI: no disponible — falta pythermalcomfort (pip install pythermalcomfort).",
            ]
        lineas += [
            "",
            "Nota: Heat Index y Temperatura Aparente no se calculan con Tmrt. "
            "La comparación sol/sombra se realiza con Tmrt y UTCI.",
        ]
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Confort térmico")
        dlg.geometry("620x460")
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
            calc = Temperatura(
                lat, lon, k_factor=self.app.k_factor,
                model_mode=self.app.tmrt_model_mode.get(),
            )
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
            calc_lo = Temperatura(
                lat, lon, k_factor=k_lo, model_mode=self.app.tmrt_model_mode.get()
            )
            calc_hi = Temperatura(
                lat, lon, k_factor=k_hi, model_mode=self.app.tmrt_model_mode.get()
            )
            esc_b_lo = scenario_tools.escenario_horario(
                calc_lo, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"])
            esc_b_hi = scenario_tools.escenario_horario(
                calc_hi, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"])
            # La sombra no modifica Heat Index si Ta/RH son iguales. Para
            # comparar escenarios se grafica UTCI (si está disponible) o,
            # en su defecto, Tmrt.
            usar_utci = all(r["utci_sombra"] is not None for r in esc_a + esc_b + esc_b_lo + esc_b_hi)
            if usar_utci:
                a_vals = [r["utci_sombra"] for r in esc_a]
                b_vals = [r["utci_sombra"] for r in esc_b]
                sol_vals = [r["utci_sol"] for r in esc_a]
                lo_vals = [r["utci_sombra"] for r in esc_b_lo]
                hi_vals = [r["utci_sombra"] for r in esc_b_hi]
                ylabel = "UTCI (°C)"
                prefijo = "UTCI"
            else:
                a_vals = [r["tmrt_sombra"] for r in esc_a]
                b_vals = [r["tmrt_sombra"] for r in esc_b]
                sol_vals = [r["tmrt_sol"] for r in esc_a]
                lo_vals = [r["tmrt_sombra"] for r in esc_b_lo]
                hi_vals = [r["tmrt_sombra"] for r in esc_b_hi]
                ylabel = "Tmrt estimada (°C)"
                prefijo = "Tmrt"

            ax.clear()
            ax.plot(horas, a_vals, "o-", color="#E53935",
                    label=f"{prefijo} sombra A ({datos['sombra_a']:.0f}%)")
            ax.plot(horas, b_vals, "s-", color="#1E88E5",
                    label=f"{prefijo} sombra B ({datos['sombra_b']:.0f}%)")
            ax.fill_between(horas, lo_vals, hi_vals, color="#1E88E5", alpha=0.15,
                            label=f"sensibilidad k ±20% ({k_lo:.4f}–{k_hi:.4f})")
            ax.plot(horas, sol_vals, "--", color="#FB8C00", label=f"{prefijo} pleno sol")
            if usar_utci:
                ax.axhline(32.0, color="gray", linestyle=":", linewidth=1)
            ax.set_xlabel("Hora")
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            canvas.draw()

            r = cmp["propuesto"]
            ancho_banda = max(hi_vals) - max(lo_vals)
            k_info = f" · calibrado {self.app.k_factor_info}" if self.app.k_factor_info else ""
            hi_nota = (
                f"Heat Index del aire: pico {r['hi_max_air']:.1f} °C "
                f"({r['categoria_pico_air']}); no cambia solo por aumentar sombra."
            )
            if r["utci_max_sombra"] is not None:
                cambio_utci = cmp.get("delta_utci_max")
                cambio_txt = f" · cambio pico A→B {cambio_utci:+.1f} °C" if cambio_utci is not None else ""
                metrica_linea = (
                    f"UTCI B: pico sol {r['utci_max_sol']:.1f} °C ({r['utci_categoria_sol']}) · "
                    f"sombra {r['utci_max_sombra']:.1f} °C ({r['utci_categoria_sombra']}){cambio_txt}"
                )
            else:
                metrica_linea = "UTCI no disponible: el gráfico usa Tmrt estimada."
            resumen_txt.config(text=(
                f"{hi_nota}\n"
                f"{metrica_linea}\n"
                f"Escenario B: reducción máxima sol→sombra en Tmrt {r['delta_tmrt_max']:.1f} °C.\n"
                f"Sensibilidad k ±20%: banda de {ancho_banda:.1f} °C en el pico{k_info}"
            ))

        botones = tk.Frame(dlg)
        botones.pack(fill="x", padx=12, pady=8)
        tk.Button(botones, text="Calcular", command=calcular, bg="#4CAF50", fg="white",
                  font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(botones, text="Cerrar", command=dlg.destroy).pack(side="right")
        calcular()

    # ---------------------------------------------------------------- validación CSV

    def _dialogo_validar_csv(self):
        """Calibración/validación científica Estándar vs Avanzado.

        La partición del CSV se respeta si existe ``conjunto``. En caso
        contrario se usa un holdout interno reproducible, claramente marcado
        como diagnóstico interno y no como validación independiente.
        """
        dlg = tk.Toplevel(self.app.root)
        dlg.title("Calibración y validación científica")
        dlg.geometry("940x760")
        dlg.minsize(820, 650)
        dlg.transient(self.app.root)

        cabecera = ttk.Frame(dlg, padding=(12, 10))
        cabecera.pack(fill="x")
        cabecera.columnconfigure(1, weight=1)

        ttk.Label(cabecera, text="Mediciones de campo:").grid(row=0, column=0, sticky="w")
        archivo_lbl = ttk.Label(cabecera, text="(ningún CSV cargado)")
        archivo_lbl.grid(row=0, column=1, sticky="w", padx=8)

        validation_pct = tk.DoubleVar(value=30.0)
        seed_var = tk.IntVar(value=42)
        ttk.Label(cabecera, text="Holdout interno (%):").grid(row=1, column=0, sticky="w", pady=(7, 0))
        ttk.Spinbox(cabecera, from_=10, to=50, increment=5, width=7,
                    textvariable=validation_pct).grid(row=1, column=1, sticky="w", pady=(7, 0))
        ttk.Label(cabecera, text="Seed:").grid(row=1, column=1, sticky="w", padx=(110, 0), pady=(7, 0))
        ttk.Spinbox(cabecera, from_=0, to=99999, width=8,
                    textvariable=seed_var).grid(row=1, column=1, sticky="w", padx=(155, 0), pady=(7, 0))

        botones_archivo = ttk.Frame(cabecera)
        botones_archivo.grid(row=0, column=2, rowspan=2, sticky="e")

        info = ttk.Label(
            dlg,
            text=(
                "Mínimo: ta + (tmrt o tg) + ghi/rad. Recomendado: sombra_pct, fecha, hora, "
                "lat/lon/timezone, viento, DNI/DHI y ta_local. Si existe la columna conjunto="
                "calibracion/validacion, esa separación tiene prioridad sobre el holdout."
            ),
            justify="left", wraplength=890,
        )
        info.pack(fill="x", padx=12, pady=(0, 8))

        cuerpo = ttk.Panedwindow(dlg, orient="vertical")
        cuerpo.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        superior = ttk.Frame(cuerpo)
        inferior = ttk.Frame(cuerpo)
        cuerpo.add(superior, weight=3)
        cuerpo.add(inferior, weight=2)

        fig = plt.Figure(figsize=(7.4, 3.5), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Tmrt observada (°C)")
        ax.set_ylabel("Tmrt modelada (°C)")
        ax.grid(True, alpha=0.25)
        canvas = FigureCanvasTkAgg(fig, master=superior)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        tabla = ttk.Treeview(
            inferior,
            columns=("modelo", "n", "rmse", "mae", "bias", "r2"),
            show="headings", height=4,
        )
        for key, titulo, ancho in (
            ("modelo", "Modelo", 210), ("n", "n", 55),
            ("rmse", "RMSE °C", 90), ("mae", "MAE °C", 90),
            ("bias", "Sesgo °C", 90), ("r2", "R²", 80),
        ):
            tabla.heading(key, text=titulo)
            tabla.column(key, width=ancho, anchor="center" if key != "modelo" else "w")
        tabla.pack(fill="x", pady=(4, 6))

        resumen_txt = tk.Text(inferior, height=8, wrap="word", font=("Consolas", 9))
        resumen_txt.pack(fill="both", expand=True)
        resumen_txt.configure(state="disabled")

        acciones = ttk.Frame(dlg, padding=(12, 0, 12, 10))
        acciones.pack(fill="x")
        aplicar_k_btn = ttk.Button(acciones, text="Aplicar k calibrado", state="disabled")
        aplicar_k_btn.pack(side="left", padx=(0, 6))
        aplicar_air_btn = ttk.Button(acciones, text="Aplicar Ta local (árbol)", state="disabled")
        aplicar_air_btn.pack(side="left", padx=6)
        exportar_btn = ttk.Button(acciones, text="Exportar validación…", state="disabled")
        exportar_btn.pack(side="left", padx=6)
        ttk.Button(acciones, text="Cerrar", command=dlg.destroy).pack(side="right")

        ttk.Button(
            botones_archivo, text="Seleccionar CSV…",
            command=lambda: self._validar_cargar_v10(
                dlg, archivo_lbl, validation_pct, seed_var, tabla, resumen_txt,
                fig, canvas, aplicar_k_btn, aplicar_air_btn, exportar_btn,
            ),
        ).pack(side="left", padx=4)
        ttk.Button(
            botones_archivo, text="Crear plantilla…",
            command=lambda: self._validar_guardar_plantilla(dlg),
        ).pack(side="left", padx=4)

        aplicar_k_btn.config(command=lambda: self._validar_aplicar_k_v10(dlg))
        aplicar_air_btn.config(command=lambda: self._validar_aplicar_aire_v10(dlg, "tree"))
        exportar_btn.config(command=lambda: self._validar_exportar_v10(dlg))

    def _validar_contexto_actual(self):
        """Contexto de respaldo para filas que no traen ubicación/fecha."""
        try:
            _ta, hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        except Exception:
            return {}
        tz = None
        if getattr(self.app, "current_location", None):
            tz = self.app.current_location.get("tz") or self.app.current_location.get("timezone")
        if not tz and hasattr(self.app, "solar_engine"):
            tz = getattr(self.app.solar_engine, "tz", None)
        return {"hora": hora, "fecha": fecha, "lat": lat, "lon": lon, "timezone": tz}

    def _validar_guardar_plantilla(self, dlg):
        """Crea/actualiza la plantilla dentro de entradas/validacion/."""
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        if project is None:
            messagebox.showwarning("Plantilla", "Abra o cree un proyecto primero.", parent=dlg)
            return
        path = os.path.join(project.layout.validation_inputs_dir, "plantilla_validacion_termica.csv")
        try:
            guardar_plantilla_csv(path)
            self.app.mark_dirty()
        except OSError as exc:
            messagebox.showerror("Plantilla", str(exc), parent=dlg)
            return
        messagebox.showinfo(
            "Plantilla creada",
            "La plantilla se actualizó dentro del proyecto:\n" + path,
            parent=dlg,
        )

    def _validar_cargar_v10(
        self, dlg, archivo_lbl, validation_pct, seed_var, tabla, resumen_txt,
        fig, canvas, aplicar_k_btn, aplicar_air_btn, exportar_btn,
    ):
        path = filedialog.askopenfilename(
            parent=dlg,
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            title="Seleccionar mediciones de campo",
        )
        if not path:
            return
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        if project is not None:
            os.makedirs(project.layout.validation_inputs_dir, exist_ok=True)
            path = project.layout.import_input_file(path, project.layout.validation_inputs_dir)
        try:
            filas = leer_csv_mediciones(path)
            report = evaluar_modelos(
                filas,
                k_actual=self.app.k_factor,
                validation_fraction=float(validation_pct.get()) / 100.0,
                seed=int(seed_var.get()),
                defaults=self._validar_contexto_actual(),
            )
        except (ValueError, FileNotFoundError, OSError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=dlg)
            return

        dlg.validation_report = report
        dlg.validation_source = path
        # Resumen serializable para informe/proyecto. No guardamos arrays ni
        # dataclasses internas del reporte completo.
        self.app.last_validation_summary = {
            "source": path,
            "split_source": report["split"].fuente,
            "k_actual": report.get("k_actual"),
            "k_calibrado": report.get("k_calibrado"),
            "metricas_modelos": report.get("metricas_modelos"),
            "metricas_aire_local": report.get("metricas_aire_local"),
            "advertencias": list(report.get("advertencias", [])),
        }
        if project is not None:
            try:
                exportar_reporte_validacion(project.layout.validation_report, report)
            except Exception as exc:
                print(f"[validacion] No se pudo autoguardar reporte: {exc}")
            self.app.mark_dirty()
        archivo_lbl.config(text=os.path.basename(path))

        for item in tabla.get_children():
            tabla.delete(item)
        for model, met in report["metricas_modelos"].items():
            if met is None:
                vals = (model, "—", "—", "—", "—", "—")
            else:
                vals = (
                    model, met["n"], f"{met['rmse']:.2f}", f"{met['mae']:.2f}",
                    f"{met['bias']:+.2f}", f"{met['r2']:.3f}",
                )
            tabla.insert("", "end", values=vals)

        kfit = report["ajuste_k"]
        split = report["split"]
        lineas = [
            f"Partición: {split.fuente}",
            f"k actual = {report['k_actual']:.5f} | k calibrado = {report['k_calibrado']:.5f} "
            f"(n calibración={kfit['n']})",
            f"Diagnóstico libre: ΔTmrt = {kfit['diagnostico_intercepto_c']:+.2f} + "
            f"{kfit['diagnostico_k_libre']:.5f} · (GHI·tau)",
        ]
        aire = report["ajuste_aire_local"].get("tree")
        if aire:
            lineas.append(
                f"Ta local árbol: coeficiente calibrado={aire['coefficient']:.6f} K/(W/m²), "
                f"tope={aire['max_cooling']:.1f} °C (n={aire['n']})"
            )
            met_air = report["metricas_aire_local"].get("tree")
            if met_air:
                lineas.append(
                    f"Validación Ta local árbol: RMSE={met_air['rmse']:.2f} °C, "
                    f"MAE={met_air['mae']:.2f} °C, sesgo={met_air['bias']:+.2f} °C, R²={met_air['r2']:.3f}"
                )
        else:
            lineas.append("Ta local: se requieren ≥3 observaciones ta_local de un mismo tipo de sombra para calibrar.")

        if report["advertencias"]:
            lineas.append("")
            lineas.append("ADVERTENCIAS / TRAZABILIDAD:")
            lineas.extend(f"• {w}" for w in report["advertencias"])

        resumen_txt.configure(state="normal")
        resumen_txt.delete("1.0", "end")
        resumen_txt.insert("1.0", "\n".join(lineas))
        resumen_txt.configure(state="disabled")

        aplicar_k_btn.config(state="normal" if kfit.get("aplicable") else "disabled")
        aplicar_air_btn.config(state="normal" if aire and aire.get("aplicable") else "disabled")
        exportar_btn.config(state="normal")

        # Gráfico únicamente sobre el conjunto de validación.
        valid = [r for r in report["filas"] if r["grupo_evaluacion"] == "validacion"]
        obs = np.asarray([r["tmrt_medido"] for r in valid], dtype=float)
        ax = fig.axes[0]
        ax.clear()
        ax.scatter(obs, [r["pred_estandar_actual"] for r in valid], alpha=0.72, s=30, label="Estándar actual")
        ax.scatter(obs, [r["pred_estandar_calibrado"] for r in valid], alpha=0.72, s=30, marker="s", label="Estándar calibrado")
        adv = np.asarray([r["pred_avanzado_v1"] for r in valid], dtype=float)
        mask = np.isfinite(obs) & np.isfinite(adv)
        if np.any(mask):
            ax.scatter(obs[mask], adv[mask], alpha=0.72, s=32, marker="^", label="Avanzado v1")
        vals = [float(v) for v in obs if np.isfinite(v)]
        for r in valid:
            for key in ("pred_estandar_actual", "pred_estandar_calibrado", "pred_avanzado_v1"):
                val = r.get(key)
                if val is not None and np.isfinite(val):
                    vals.append(float(val))
        if vals:
            lo, hi = min(vals) - 1.0, max(vals) + 1.0
            ax.plot([lo, hi], [lo, hi], "--", linewidth=1.0, label="1:1")
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
        ax.set_xlabel("Tmrt observada (°C)")
        ax.set_ylabel("Tmrt modelada (°C)")
        ax.set_title("Validación: observado vs modelado")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        canvas.draw_idle()

    def _validar_aplicar_k_v10(self, dlg):
        report = getattr(dlg, "validation_report", None)
        if not report:
            return
        k = float(report["k_calibrado"])
        if not np.isfinite(k) or k <= 0:
            messagebox.showwarning("k_factor", "El k calibrado no es físicamente aplicable.", parent=dlg)
            return
        self.app.k_factor = k
        self.app.settings["k_factor"] = k
        self.app.settings["k_factor_info"] = (
            f"Calibración v10 {datetime.now().strftime('%Y-%m-%d %H:%M')}; "
            f"{report['split'].fuente}; n={report['ajuste_k']['n']}"
        )
        self.app.settings_manager.write(self.app.settings)
        messagebox.showinfo(
            "k_factor aplicado",
            f"k_factor = {k:.6f}\n\nSe aplicará al modelo Estándar en los próximos cálculos. "
            "El modelo Avanzado no usa k_factor.",
            parent=dlg,
        )

    def _validar_aplicar_aire_v10(self, dlg, tipo="tree"):
        report = getattr(dlg, "validation_report", None)
        if not report:
            return
        fit = report["ajuste_aire_local"].get(tipo)
        if not fit:
            return
        prefix = "tree" if tipo == "tree" else "structure"
        self.app.settings[f"local_air_{prefix}_coefficient"] = float(fit["coefficient"])
        self.app.settings[f"local_air_{prefix}_max_cooling"] = float(fit["max_cooling"])
        self.app.settings[f"local_air_{prefix}_calibration_info"] = (
            f"Calibración v10 {datetime.now().strftime('%Y-%m-%d %H:%M')}; n={fit['n']}"
        )
        self.app.settings_manager.write(self.app.settings)
        messagebox.showinfo(
            "Ta local calibrada",
            f"Coeficiente ({prefix}) = {fit['coefficient']:.6f} K/(W/m²)\n"
            f"Tope = {fit['max_cooling']:.1f} °C\n\n"
            "Se utilizará en las próximas curvas de nivel. La variable continúa rotulada como estimada.",
            parent=dlg,
        )

    def _validar_exportar_v10(self, dlg):
        """Actualiza el reporte de validación en su carpeta fija del proyecto."""
        report = getattr(dlg, "validation_report", None)
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        if not report or project is None:
            return
        path = project.layout.validation_report
        try:
            exportar_reporte_validacion(path, report)
        except Exception as exc:
            messagebox.showerror("Validación", str(exc), parent=dlg)
            return
        messagebox.showinfo("Validación", f"Reporte actualizado en:\n{path}", parent=dlg)

    # Métodos históricos conservados como aliases internos para plugins/código
    # que pudiera invocarlos directamente.
    def _validar_aplicar_k(self, aplicar_btn, dlg):
        return self._validar_aplicar_k_v10(dlg)

    def _dialogo_auditoria_cientifica(self):
        """Ejecuta la auditoría interna de preparación científica v16.

        No sustituye una validación de campo: separa fallas internas,
        advertencias metodológicas y evidencia experimental faltante.
        """
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        report = run_scientific_audit(
            project_root=(project.root_path if project else None),
            settings=getattr(self.app, "settings", {}),
            snapshots=getattr(self.app, "snapshots", []),
            validation_summary=getattr(self.app, "last_validation_summary", None),
        )
        self.app.last_scientific_audit = report.to_dict()
        if project is not None:
            os.makedirs(project.layout.validation_results_dir, exist_ok=True)
            save_audit_json(project.layout.audit_json, report)
            with open(project.layout.audit_txt, "w", encoding="utf-8") as handle:
                handle.write(format_audit_text(report))
            self.app.mark_dirty()

        dlg = tk.Toplevel(self.app.root)
        dlg.title("Auditoría científica y preparación para validación")
        dlg.geometry("820x640")
        dlg.transient(self.app.root)

        counts = report.counts
        tk.Label(
            dlg,
            text=report.readiness,
            font=("Arial", 11, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(
            dlg,
            text=(
                f"Release {report.scientific_release} · "
                f"OK {counts.get('pass', 0)} · advertencias {counts.get('warning', 0)} · "
                f"fallas {counts.get('fail', 0)}"
            ),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        text = tk.Text(dlg, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(dlg, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", pady=(0, 8))
        text.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 8))
        text.insert("1.0", format_audit_text(report))
        text.configure(state="disabled")

        pie = tk.Frame(dlg)
        pie.pack(fill="x", padx=12, pady=(0, 10))

        def export_json():
            if project is None:
                return
            save_audit_json(project.layout.audit_json, report)
            messagebox.showinfo("Auditoría", f"Auditoría actualizada en:\n{project.layout.audit_json}", parent=dlg)

        def export_txt():
            if project is None:
                return
            with open(project.layout.audit_txt, "w", encoding="utf-8") as handle:
                handle.write(format_audit_text(report))
            messagebox.showinfo("Auditoría", f"Auditoría actualizada en:\n{project.layout.audit_txt}", parent=dlg)

        tk.Button(pie, text="Guardar JSON", command=export_json).pack(side="left")
        tk.Button(pie, text="Guardar TXT", command=export_txt).pack(side="left", padx=6)
        tk.Button(pie, text="Cerrar", command=dlg.destroy).pack(side="right")

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
                f"LAI típico: {p['lai_tipico']:.2f}  Kc ET: {p['kc_et']:.2f}  Tau sin hojas: {p['transmitancia_sin_hojas']:.2f}\n"
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
            ("LAI típico (0.1-10):", "lai_tipico"),
            ("Coeficiente ET Kc (0.1-2):", "kc_et"),
            ("Transmitancia sin hojas (0-1):", "transmitancia_sin_hojas"),
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
                          "altura_tipica", "radio_copa_tipico", "lai_tipico",
                          "kc_et", "transmitancia_sin_hojas"):
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
            vars_form["lai_tipico"].set("3.0")
            vars_form["kc_et"].set("1.0")
            vars_form["transmitancia_sin_hojas"].set("0.75")
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
                "lai_tipico": vars_form["lai_tipico"].get().replace(",", ".").strip(),
                "kc_et": vars_form["kc_et"].get().replace(",", ".").strip(),
                "transmitancia_sin_hojas": vars_form["transmitancia_sin_hojas"].get().replace(",", ".").strip(),
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