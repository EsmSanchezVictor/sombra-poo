import tkinter as tk  # Asegúrate de usar el alias correcto
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class MouseHoverPixelValueWithTooltip:
    def __init__(self, app, canvas_image, canvas_contour, img_rgb, area_seleccionada):
        """
        Inicializa la clase que maneja la visualización de los valores de los píxeles con un tooltip cerca del mouse.
        :param app: Instancia de la aplicación principal.
        :param canvas_image: Canvas de la imagen cargada.
        :param canvas_contour: Canvas de la imagen de curvas de nivel.
        :param img_rgb: Imagen cargada (RGB).
        :param area_seleccionada: Matriz del área seleccionada para las curvas de nivel.
        """
        self.app = app
        self.canvas_image = canvas_image
        self.canvas_contour = canvas_contour
        self.img_rgb = img_rgb
        self.area_seleccionada = area_seleccionada
     

        # Conectar eventos de movimiento del mouse
        self.canvas_image.mpl_connect('motion_notify_event', self.on_mouse_move_image)
        self.canvas_contour.mpl_connect('motion_notify_event', self.on_mouse_move_contour)

        # Crear una etiqueta de Tkinter que seguirá el mouse
        self.tooltip = tk.Label(self.app.root, text="", bg="white", font=("Arial", 10), bd=1, relief=tk.SOLID)
        self.tooltip.place_forget()  # Ocultarla inicialmente

    def on_mouse_move_image(self, event):
        """Mostrar el valor del píxel sobre la imagen cargada y mover el tooltip cerca del mouse."""
        if event.inaxes:  # Solo si el mouse está dentro de los ejes de la imagen
            x, y = int(event.xdata), int(event.ydata)  # Obtener las coordenadas del gráfico
            x2, y2 = int(event.xdata), int(event.ydata)  # Obtener las coordenadas del gráfico
            if 0 <= x < self.img_rgb.shape[1] and 0 <= y < self.img_rgb.shape[0]:
                pixel_value = self.img_rgb[y, x]
                # Actualizar el texto del tooltip con el valor del píxel
                self.tooltip.config(text=f"(R,G,B): {x,y}")#text=f"(R,G,B): {pixel_value}")
                # Mover el tooltip cerca del puntero del mouse
          
          
          
                self.tooltip.place(x=100+event.x,y=100+event.y/3)
            else:
                self.tooltip.place_forget()  # Ocultar si está fuera de los límites
        else:
            self.tooltip.place_forget()  # Ocultar si el mouse está fuera de los ejes

    def on_mouse_move_contour(self, event):
        """Mostrar el valor del píxel sobre las curvas de nivel y mover el tooltip cerca del mouse."""
        if self.app.curvas_nivel_creadas:  # Solo ejecutar si las curvas de nivel han sido creadas
            if event.inaxes:  # Solo si el mouse está dentro de los ejes
                x, y = int(event.xdata), int(event.ydata)  # Obtener las coordenadas del gráfico
                x2, y2 = int(event.xdata), int(event.ydata)  # Obtener las coordenadas del gráfico
                if 0 <= x < self.area_seleccionada.shape[1] and 0 <= y < self.area_seleccionada.shape[0]:
                    pixel_value = self.area_seleccionada[y, x]
                    # Actualizar el texto del tooltip con el valor del píxel
                    self.tooltip.config(text=f"Valor:{x,y}")# {pixel_value:.2f}
                    # Mover el tooltip cerca del puntero del mouse
                    
                    
                    self.tooltip.place(x=750+event.x, y=100+event.y/3)
                else:
                    self.tooltip.place_forget()  # Ocultar si está fuera de los límites
            else:
                self.tooltip.place_forget()  # Ocultar si el mouse está fuera de los ejes
 