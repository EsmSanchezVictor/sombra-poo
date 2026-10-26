"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from ui.modal_style import prepare_dialog
from core import thermal_comfort
from core.validation import k_factor_desde_mediciones

class CalibrationDialogsMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def _dialogo_calibrar_k_factor(self):
        """Asistente de calibración: ingresa mediciones de campo
        (temperatura de globo o Tmrt, temperatura de aire, radiación,
        viento), ajusta k_factor por mínimos cuadrados y lo persiste en
        settings.json para que todo el modelo lo use."""
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(560, 420))
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
