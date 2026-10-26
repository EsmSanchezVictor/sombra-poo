"""Diálogos de campaña, calibración y validación; sin alterar los modelos."""
from __future__ import annotations
import os
import shutil
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.effective_scenario import effective_model
from core.model_registry import TMRT_MODELS
from core.validation import evaluar_modelos, exportar_reporte_validacion, guardar_plantilla_csv, leer_csv_mediciones
from ui.modal_style import prepare_dialog


class ValidationDialogsMixin:
    def _dialogo_validar_csv(self):
        """Calibración/validación científica Estándar vs Avanzado.

        La partición del CSV se respeta si existe ``conjunto``. En caso
        contrario se usa un holdout interno reproducible, claramente marcado
        como diagnóstico interno y no como validación independiente.
        """
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(820, 650))
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
            model = TMRT_MODELS["advanced"]["label"] if model == "Avanzado v1" else model
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
            ax.scatter(obs[mask], adv[mask], alpha=0.72, s=32, marker="^", label=TMRT_MODELS["advanced"]["label"])
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


    def _validar_aplicar_k(self, aplicar_btn, dlg):
        return self._validar_aplicar_k_v10(dlg)


