"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
from core.effective_scenario import effective_model
import queue
import threading
import time
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.modal_style import prepare_dialog
from core import scenario as scenario_tools
from core import thermal_comfort
from core.climate_profile import viento_categoria_a_ms
from shadow_temp import Temperatura

class ComfortDialogsMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def _dialogo_confort(self):
        """Confort térmico con UTCI espacial vectorizado (v20).

        La ventana se muestra antes del cálculo del mapa. Los índices puntuales
        se obtienen de inmediato y la distribución espacial UTCI se procesa en
        un hilo de trabajo con una única evaluación vectorizada de
        pythermalcomfort, evitando bloquear el event loop de Tkinter.
        """
        temp_ambient, hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        try:
            scenario, solar_data = self.app._resolve_temperature_scenario(temp_ambient, hora, fecha, lat, lon)
        except ValueError as exc:
            messagebox.showwarning("Escenario", str(exc))
            return
        temp_ambient = scenario.air_temp_c
        rh = scenario.rh_pct
        v_ms = scenario.wind_ref_10m_m_s
        calculador = scenario.calculator()
        ghi = scenario.ghi

        sombra_pct = 50.0
        if self.app.porcentaje_sombra is not None:
            sombra_pct = float(self.app.porcentaje_sombra)
        elif self.app.last_shadow is not None:
            sombra_pct = (1 - np.asarray(self.app.last_shadow, dtype=np.float32)).mean() * 100

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
                f"UTCI sol = {thermal_comfort.formato_utci(utci_sol)}",
                f"UTCI sombra = {thermal_comfort.formato_utci(utci_sombra)}",
            ]
        else:
            lineas += [
                "UTCI: no disponible — falta pythermalcomfort (pip install pythermalcomfort).",
            ]

        lineas += [
            "",
            "Nota: Heat Index y Temperatura Aparente no se calculan con Tmrt. "
            "La comparación sol/sombra se realiza con Tmrt y UTCI.",
        ]

        # La ventana se crea ANTES del análisis espacial. Así Confort responde
        # de inmediato aunque haya un mapa de alta resolución.
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(600, 420))
        dlg.title("Confort térmico")
        dlg.geometry("680x500")
        dlg.transient(self.app.root)

        text_var = tk.StringVar(value="\n".join(lineas))
        tk.Label(dlg, textvariable=text_var, justify="left", anchor="nw").pack(
            fill="both", expand=True, padx=14, pady=(12, 4)
        )
        status_var = tk.StringVar(value="")
        status_label = tk.Label(dlg, textvariable=status_var, justify="left", anchor="w", fg="#555555")
        status_label.pack(fill="x", padx=14, pady=(2, 6))
        tk.Button(dlg, text="Cerrar", command=dlg.destroy).pack(pady=(0, 8))
        dlg.update_idletasks()

        if not thermal_comfort.UTCI_DISPONIBLE or self.app.tmrt_map is None:
            return

        # Copia compacta y estable para el worker; como máximo 640x640 en v20
        # (~1.6 MB en float32). No se leen variables Tk desde el hilo.
        tmrt_map = np.asarray(self.app.tmrt_map, dtype=np.float32).copy()
        n_validos = int(np.count_nonzero(np.isfinite(tmrt_map)))
        status_var.set(
            f"Calculando distribución espacial UTCI… {tmrt_map.shape[0]}×{tmrt_map.shape[1]} "
            f"({n_validos:,} celdas)".replace(",", ".")
        )

        result_queue = queue.Queue(maxsize=1)

        def worker():
            inicio = time.perf_counter()
            try:
                mapa = scenario_tools.mapa_estres(
                    tmrt_map,
                    temp_ambient,
                    rh,
                    indice="utci",
                    v_ms=v_ms,
                )
                result_queue.put((mapa, time.perf_counter() - inicio, None))
            except Exception as exc:
                result_queue.put((None, time.perf_counter() - inicio, str(exc)))

        def poll_worker():
            # Solo el hilo principal toca Tk. El worker se limita a NumPy /
            # pythermalcomfort y entrega su resultado mediante Queue.
            try:
                mapa, elapsed, error = result_queue.get_nowait()
            except queue.Empty:
                try:
                    if dlg.winfo_exists():
                        dlg.after(40, poll_worker)
                except tk.TclError:
                    pass
                return

            try:
                if not dlg.winfo_exists():
                    return
                if error is not None:
                    status_var.set(f"No se pudo calcular el mapa UTCI: {error}")
                    return
                por_area = ", ".join(f"{k}: {v}%" for k, v in mapa["por_area"].items())
                text_var.set("\n".join(lineas + ["", f"Mapa UTCI derivado del mapa Tmrt: {por_area}"]))
                status_var.set(
                    f"Distribución espacial calculada con UTCI vectorizado · "
                    f"{mapa['n_pixeles']:,} celdas · {elapsed:.2f} s".replace(",", ".")
                )
            except tk.TclError:
                pass

        threading.Thread(target=worker, name="utci-map-v20", daemon=True).start()
        dlg.after(40, poll_worker)

    def _dialogo_escenario_ab(self):
        """Escenario A/B horario: comparar dos % de sombra (p. ej. línea
        base vs. propuesta de arbolado) a lo largo del día, con curvas de
        Heat Index, Tmrt, banda de incertidumbre de k ±20% y resumen de
        grados-hora de estrés."""
        temp_ambient, _hora, fecha, lat, lon = self.app._leer_parametros_tmrt()
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(640, 520))
        dlg.title("Escenario A/B horario (sombra vs. propuesta)")
        dlg.geometry("720x640")
        dlg.transient(self.app.root)

        form = tk.Frame(dlg)
        form.pack(fill="x", padx=12, pady=8)
        form.grid_columnconfigure(1, weight=1)
        defaults = {
            "hora_ini": "8", "hora_fin": "18",
            "ta_min": "20", "ta_max": str(round(temp_ambient, 1)),
            "rh": str(
                self.app.vars_modelo["humedad"].get()
                if getattr(self.app, "modo_modelo", None) is not None and self.app.modo_modelo.get() == "advanced"
                else (self.app.simple_rh.get() or 60)
            ),
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
            def provider(ta, hour, calculator):
                from dataclasses import replace
                conf, solar = self.app._resolve_temperature_scenario(ta, hour, fecha, lat, lon)
                observed = conf.source_mode == 'observed_series'
                return replace(conf, k_factor=calculator.k_factor,
                               rh_pct=conf.rh_pct if observed and solar.get('rh_pct') is not None else datos['rh'],
                               wind_ref_10m_m_s=conf.wind_ref_10m_m_s if observed and solar.get('wind_m_s') is not None else datos['viento'])
            horas = [float(h) for h in
                     np.arange(datos["hora_ini"], datos["hora_fin"] + 1)]
            calc = Temperatura(
                lat, lon, k_factor=self.app.k_factor,
                model_mode=effective_model(self.app.modo_temperatura.get(), self.app.tmrt_model_mode.get()),
            )
            esc_a = scenario_tools.escenario_horario(
                calc, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_a"], scenario_provider=provider)
            esc_b = scenario_tools.escenario_horario(
                calc, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"], scenario_provider=provider)
            cmp = scenario_tools.comparar_escenarios(esc_a, esc_b)
            # banda de incertidumbre: k ± 20% (sensibilidad típica del
            # coeficiente de calibración; si se calibró con CSV se
            # reporta también el RMSE del ajuste en el resumen)
            k_lo = self.app.k_factor * 0.8
            k_hi = self.app.k_factor * 1.2
            calc_lo = Temperatura(
                lat, lon, k_factor=k_lo, model_mode=effective_model(self.app.modo_temperatura.get(), self.app.tmrt_model_mode.get())
            )
            calc_hi = Temperatura(
                lat, lon, k_factor=k_hi, model_mode=effective_model(self.app.modo_temperatura.get(), self.app.tmrt_model_mode.get())
            )
            esc_b_lo = scenario_tools.escenario_horario(
                calc_lo, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"], scenario_provider=provider)
            esc_b_hi = scenario_tools.escenario_horario(
                calc_hi, fecha, horas, datos["ta_min"], datos["ta_max"],
                datos["rh"], datos["viento"], datos["sombra_b"], scenario_provider=provider)
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
