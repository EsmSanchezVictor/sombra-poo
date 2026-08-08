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
"""
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from plot_style import CMAP_TEMPERATURA, FONT_ANOTACION, FONT_TITULO


class TemperatureGraph:
    def __init__(self, temp_ambient, temp_shade, frame):
        self.temp_ambient = temp_ambient
        self.temp_shade = temp_shade
        self.frame = frame

    def plot_temperature_scale(self):
        """Genera una barra de escala de temperatura embebida en Tkinter,
        con los valores de sol/sombra marcados sobre la propia barra."""
        vmin = min(self.temp_shade, self.temp_ambient)
        vmax = max(self.temp_shade, self.temp_ambient)
        # Si ambos valores son iguales, se evita un rango de ancho 0
        # (matplotlib fallaría al normalizar).
        if vmax - vmin < 1e-6:
            vmin -= 0.5
            vmax += 0.5

        fig = plt.figure(figsize=(6, 1.4))
        ax_colorbar = fig.add_axes([0.1, 0.45, 0.8, 0.2])
        delta = self.temp_ambient - self.temp_shade
        fig.suptitle(
            f"Escala de temperatura   —   ΔT = {delta:.1f} °C",
            fontsize=FONT_TITULO, y=1.15,
        )

        norm = plt.Normalize(vmin, vmax)
        color_bar = cm.ScalarMappable(cmap=CMAP_TEMPERATURA, norm=norm)
        color_bar.set_array([])

        cbar = fig.colorbar(color_bar, cax=ax_colorbar, orientation="horizontal")
        cbar.set_label("Temperatura (°C)", fontsize=FONT_ANOTACION)
        cbar.ax.tick_params(labelsize=FONT_ANOTACION)

        # Marcadores explícitos de sol / sombra sobre la barra, con el
        # valor numérico — antes había que estimarlo a ojo por posición.
        for valor, etiqueta in (
            (self.temp_ambient, "Sol"),
            (self.temp_shade, "Sombra"),
        ):
            pos = (valor - vmin) / (vmax - vmin)
            ax_colorbar.axvline(pos, color="black", linewidth=1.3, ymin=-0.6, ymax=1.6, clip_on=False)
            ax_colorbar.text(
                pos, 1.9, f"{etiqueta}\n{valor:.1f}°C",
                transform=ax_colorbar.transData,
                ha="center", va="bottom", fontsize=FONT_ANOTACION,
            )

        canvas = FigureCanvasTkAgg(fig, master=self.frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="right", padx=10)
