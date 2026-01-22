import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import cm

class TemperatureGraph:
    def __init__(self, temp_ambient, temp_shade, frame):
        self.temp_ambient = temp_ambient
        self.temp_shade = temp_shade
        self.frame = frame  # Asegurarse de recibir el frame correctamente

    def plot_temperature_scale(self):
        """Genera una gráfica de barra de color embebida en la ventana Tkinter."""
        # Crear un rango de temperaturas desde la sombra hasta la temperatura ambiente
        temperatures = np.linspace(self.temp_shade, self.temp_ambient, 100)

        # Crear una figura y definir un espacio específico para la barra de colores
        fig = plt.figure(figsize=(6, 1))  # Ajustar tamaño de la figura
        
        ax_colorbar = fig.add_axes([0.2, 0.5, 0.6, 0.15])  # Añadir un área para la barra de color
        fig.suptitle("Escala de temperatura", fontsize=9, y=1.08)
        # Crear una barra de color usando 'jet' con un mapa de colores adecuado
        norm = plt.Normalize(self.temp_shade, self.temp_ambient)
        color_bar = cm.ScalarMappable(cmap="jet", norm=norm)
        color_bar.set_array([])

        # Añadir la barra de colores en el área reservada
        cbar = fig.colorbar(color_bar, cax=ax_colorbar, orientation='horizontal')
        cbar.set_label('Temperatura (°C)')

        # Embebemos el gráfico en el frame de Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="right", padx=10)  # Posicionar en el frame a la derecha
