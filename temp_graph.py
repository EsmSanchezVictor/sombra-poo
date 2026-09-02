"""Gráfico de escala de temperatura (sol vs. sombra).

CAMBIOS respecto a la versión original:
1. Paleta "jet" → "RdYlBu_r" (ver `plot_style.py` para el porqué:
   "jet" no es perceptualmente uniforme y es mala práctica estándar en
   visualización científica de temperatura).
2. Antes la barra era un degradé sin ningún valor legible salvo los
   ticks automáticos de matplotlib. Ahora se marcan explícitamente
   los dos valores que le importan al usuario — Tmrt al sol y Tmrt en
   sombra — con una línea y el número al lado, así el gráfico se lee
   sin tener que adivinar la escala.
3. Se agrega el ΔTmrt (diferencia) como texto destacado — es el dato
   que responde la pregunta real ("¿cuánto ayuda la sombra acá?").
4. FIX (inconsistencia detectada): los parámetros se llamaban
   `temp_ambient` / `temp_shade`, pero quien llamaba a esta clase le
   pasaba en realidad la temperatura de AIRE cruda ingresada por el
   usuario (sin el aporte de radiación) como "sol", mientras que el
   label de arriba en pantalla ("Tmrt al sol") mostraba
   `Tmrt_sol = air_temp + k_factor * radiacion` — un valor distinto.
   Resultado: el ΔT del título de este gráfico y el "ΔTmrt (impacto
   sombra)" del label de arriba mostraban números diferentes para lo
   que el usuario esperaba fuera el mismo dato. Se renombran los
   parámetros a `tmrt_sol` / `tmrt_sombra` para que el nombre ya deje
   claro qué se espera recibir acá, y los llamados en ui/app_ui.py se
   actualizaron para pasar `Tmrt_sol` (no la temperatura de aire cruda).
"""
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Ya no es necesario importar FONT_ANOTACION ni FONT_TITULO
from plot_style import CMAP_TEMPERATURA

class TemperatureGraph:
    def __init__(self, tmrt_sol, tmrt_sombra, frame):
        self.tmrt_sol = tmrt_sol
        self.tmrt_sombra = tmrt_sombra
        self.frame = frame

    def plot_temperature_scale(self):
        """Genera una barra de escala de temperatura embebida en Tkinter,
        con los valores de sol/sombra marcados sobre la propia barra."""
        vmin = min(self.tmrt_sombra, self.tmrt_sol)
        vmax = max(self.tmrt_sombra, self.tmrt_sol)
        # Si ambos valores son iguales, se evita un rango de ancho 0
        # (matplotlib fallaría al normalizar).
        if vmax - vmin < 1e-6:
            vmin -= 0.5
            vmax += 0.5

        fig = plt.figure(figsize=(6, 0.6))
        ax_colorbar = fig.add_axes([0.1, 0.45, 0.8, 0.2])
        # ΔT = Tmrt al sol − Tmrt en sombra: ahora coincide con
        # "Delta_Tmrt" (el mismo cálculo que arma shadow_temp.py y que
        # muestra el label "ΔTmrt (impacto sombra)").
        delta = self.tmrt_sol - self.tmrt_sombra
        fig.suptitle(
            f"Escala de temperatura   —   ΔT = {delta:.1f} °C",
            fontsize=7, y=0.95, # TAMAÑO ACTUALIZADO
        )

        norm = plt.Normalize(vmin, vmax)
        color_bar = cm.ScalarMappable(cmap=CMAP_TEMPERATURA, norm=norm)
        color_bar.set_array([])

        cbar = fig.colorbar(color_bar, cax=ax_colorbar, orientation="horizontal")
        cbar.set_label("Temperatura (°C)", fontsize=7) # TAMAÑO ACTUALIZADO
        cbar.ax.tick_params(labelsize=7) # TAMAÑO ACTUALIZADO

        # Marcadores explícitos de sol / sombra sobre la barra, con el
        # valor numérico — antes había que estimarlo a ojo por posición.
        for valor, etiqueta in (
            (self.tmrt_sol, "Sol"),
            (self.tmrt_sombra, "Sombra"),
        ):
            pos = float(valor)
            ax_colorbar.axvline(pos, color="black", linewidth=1.3, ymin=-0.6, ymax=1.6, clip_on=False)
            ax_colorbar.text(
                pos, 1.9, f"{etiqueta}\n{valor:.1f}°C",
                transform=ax_colorbar.transData,
                ha="center", va="bottom", fontsize=7, # TAMAÑO ACTUALIZADO
            )

        canvas = FigureCanvasTkAgg(fig, master=self.frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="right", padx=10)