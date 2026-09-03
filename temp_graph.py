"""Gráfico de escala de temperatura (sol vs. sombra).

v18 evita registrar esta figura temporal en ``matplotlib.pyplot``. La GUI
conserva una sola instancia y libera explícitamente canvas/figura al
reemplazarla, reduciendo acumulación de RAM en sesiones largas.
"""
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from plot_style import CMAP_TEMPERATURA


class TemperatureGraph:
    def __init__(self, tmrt_sol, tmrt_sombra, frame):
        self.tmrt_sol = tmrt_sol
        self.tmrt_sombra = tmrt_sombra
        self.frame = frame

    def build_figure(self):
        """Construye la figura sin registrarla en ``matplotlib.pyplot``."""
        vmin = min(self.tmrt_sombra, self.tmrt_sol)
        vmax = max(self.tmrt_sombra, self.tmrt_sol)
        if vmax - vmin < 1e-6:
            vmin -= 0.5
            vmax += 0.5

        fig = Figure(figsize=(6, 0.6))
        ax_colorbar = fig.add_axes([0.1, 0.45, 0.8, 0.2])
        delta = self.tmrt_sol - self.tmrt_sombra
        fig.suptitle(
            f"Escala de temperatura   —   ΔT = {delta:.1f} °C",
            fontsize=7, y=0.95,
        )

        norm = Normalize(vmin, vmax)
        color_bar = cm.ScalarMappable(cmap=CMAP_TEMPERATURA, norm=norm)
        color_bar.set_array([])
        cbar = fig.colorbar(color_bar, cax=ax_colorbar, orientation="horizontal")
        cbar.set_label("Temperatura (°C)", fontsize=7)
        cbar.ax.tick_params(labelsize=7)

        for valor, etiqueta in (
            (self.tmrt_sol, "Sol"),
            (self.tmrt_sombra, "Sombra"),
        ):
            pos = float(valor)
            ax_colorbar.axvline(
                pos, color="black", linewidth=1.3,
                ymin=-0.6, ymax=1.6, clip_on=False,
            )
            ax_colorbar.text(
                pos, 1.9, f"{etiqueta}\n{valor:.1f}°C",
                transform=ax_colorbar.transData,
                ha="center", va="bottom", fontsize=7,
            )
        return fig

    def plot_temperature_scale(self):
        """Genera la barra embebida en Tkinter y devuelve figura+canvas."""
        fig = self.build_figure()
        canvas = FigureCanvasTkAgg(fig, master=self.frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="right", padx=10)
        return fig, canvas
