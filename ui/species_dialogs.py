"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.modal_style import prepare_dialog
from core import scenario as scenario_tools
from core.species import eliminar_especie, guardar_especie, nombres_especies, propiedades_especie, validar_especie

class SpeciesDialogsMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def _dialogo_especies(self):
        """Biblioteca de especies con propiedades térmicas (transmitancia
        de copa, densidad, caducidad) y su referencia bibliográfica."""
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(500, 420))
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
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(680, 500))
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
        """Una escena elegida, con el contexto efectivo del panel Temperatura."""
        from services.tree_ranking_service import rank_app_trees
        from core.model_registry import TMRT_MODELS
        from core.safe_io import atomic_write_json
        available = [name for name, variables in (("Edición", self.app.vars), ("Modelo", self.app.vars_modelo))
                     if variables.get("arboles")]
        if not available:
            messagebox.showinfo("Ranking de árboles", "Agregue árboles en Edición o Modelo para calcular el ranking.")
            return
        dlg = tk.Toplevel(self.app.root)
        prepare_dialog(dlg, self.app.root, modal=False, resizable=True, minsize=(680, 560))
        dlg.title("Potencial individual de los árboles")
        dlg.geometry("820x660")
        head = tk.Frame(dlg)
        head.pack(fill="x", padx=12, pady=10)
        tk.Label(head, text="Escena de árboles:").pack(side="left")
        scene = tk.StringVar(dlg, value=available[0])
        chooser = ttk.Combobox(head, textvariable=scene, values=available, state="readonly", width=12)
        chooser.pack(side="left", padx=8)
        info = tk.Label(dlg, justify="left", anchor="w", wraplength=780)
        info.pack(fill="x", padx=12)
        fig = plt.Figure(figsize=(7, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=dlg)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12)
        details = tk.Text(dlg, height=6, wrap="word")
        details.pack(fill="x", padx=12)
        state = {}

        def recalculate(_event=None):
            state.clear()
            try:
                config, results = rank_app_trees(self.app, scene.get())
            except ValueError as exc:
                ax.clear()
                canvas.draw()
                details.delete("1.0", "end")
                info.config(text=str(exc))
                export_button.config(state="disabled")
                return
            state.update(results=results, scene=scene.get())
            export_button.config(state="normal")
            info.config(text=(f"Contexto de Temperatura: {config.instant_local_iso} · {TMRT_MODELS[config.tmrt_model]['label']}\n"
                              f"{config.source_label} · GHI {config.ghi:.1f} W/m² · Ta {config.air_temp_c:.1f} °C\n"
                              "Cada árbol se evalúa solo en 60×60 m centrados en (0, 0). No representa el aporte marginal en la escena completa."))
            names = [f"Árbol {r['tree_index']} · {getattr(r['arbol'], 'especie', '') or 'sin especie'}" for r in results]
            ax.clear()
            ax.barh(range(len(results)), [r["delta_tmrt_prom"] for r in results], color="#1E88E5")
            ax.set_yticks(range(len(results)))
            ax.set_yticklabels(names, fontsize=8)
            ax.invert_yaxis()
            ax.set_xlabel("Reducción de Tmrt media en el dominio (°C)")
            ax.grid(True, alpha=0.3, axis="x")
            fig.tight_layout()
            canvas.draw()
            details.delete("1.0", "end")
            details.insert("end", "\n".join(f"{names[i]}: área {r['area_sombra_m2']:.1f} m² · cobertura {r['cobertura_frac']*100:.1f}% · ΔTmrt {r['delta_tmrt_prom']:.2f} °C" for i, r in enumerate(results)))

        def export():
            if not state:
                return
            path = filedialog.asksaveasfilename(parent=dlg, title="Guardar ranking con procedencia", defaultextension=".json",
                                              filetypes=[("Ranking JSON", "*.json")])
            if path:
                try:
                    atomic_write_json(path, scenario_tools.ranking_export_payload(state["results"], scene_name=state["scene"]))
                except Exception as exc:
                    messagebox.showerror("Exportar ranking", str(exc), parent=dlg)

        tk.Button(head, text="Recalcular", command=recalculate).pack(side="left")
        export_button = tk.Button(head, text="Exportar JSON", command=export, state="disabled")
        export_button.pack(side="right")
        chooser.bind("<<ComboboxSelected>>", recalculate)
        tk.Button(dlg, text="Cerrar", command=dlg.destroy).pack(pady=8)
        dlg.bind("<Destroy>", lambda event: plt.close(fig) if event.widget is dlg else None)
        recalculate()
