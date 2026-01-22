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

        self.last_image_pixel = None
        self.last_contour_pixel = None

        # Conectar eventos de movimiento del mouse
        self.canvas_image.mpl_connect('motion_notify_event', self.on_mouse_move_image)
        self.canvas_contour.mpl_connect('motion_notify_event', self.on_mouse_move_contour)

        # Crear una etiqueta de Tkinter que seguirá el mouse
        self.tooltip = tk.Label(self.app.root, text="", bg="white", font=("Arial", 10), bd=1, relief=tk.SOLID)
        self.tooltip.place_forget()  # Ocultarla inicialmente

    def on_mouse_move_image(self, event):
        """Mostrar % sombra sobre la imagen RGB sin redibujar la figura."""
        if not event.inaxes or event.xdata is None or event.ydata is None:
            self.tooltip.place_forget()
            self.last_image_pixel = None
            return

        x, y = int(event.xdata), int(event.ydata)
        if 0 <= x < self.img_rgb.shape[1] and 0 <= y < self.img_rgb.shape[0]:
            if self.last_image_pixel == (x, y):
                return
            self.last_image_pixel = (x, y)

            pixel = self.img_rgb[y, x]
            r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            ref_gray = self.app.ref_gray_mean
            if ref_gray is None or ref_gray <= 0:
                text = "Ref no definida"
            else:
                sombra = (ref_gray - gray) / ref_gray
                sombra = max(0, min(sombra, 1)) * 100
                text = f"% Sombra: {sombra:.2f}%"

            self.tooltip.config(text=text)
            self.tooltip.place(x=100 + event.x, y=100 + event.y / 3)
        else:
            self.tooltip.place_forget()
            self.last_image_pixel = None

    def on_mouse_move_contour(self, event):
        """Mostrar Tmrt y temperatura de aire sobre el mapa sin redibujar."""
        if not self.app.curvas_nivel_creadas:
            return
        if not event.inaxes or event.xdata is None or event.ydata is None:
            self.tooltip.place_forget()
            self.last_contour_pixel = None
            return

        data = self.app.tmrt_map if self.app.tmrt_map is not None else self.area_seleccionada
        if data is None:
            return

        x, y = int(event.xdata), int(event.ydata)
        if 0 <= x < data.shape[1] and 0 <= y < data.shape[0]:
            if self.last_contour_pixel == (x, y):
                return
            self.last_contour_pixel = (x, y)

            tmrt_value = float(data[y, x])
            try:
                temp_air = float(self.app.entry_temp.get().replace('\ufeff', '').strip())
                temp_air_text = f"{temp_air:.2f} °C"
            except (ValueError, AttributeError):
                temp_air_text = "N/A"

            self.tooltip.config(text=f"Tmrt: {tmrt_value:.2f} °C\nTemp aire: {temp_air_text}")
            self.tooltip.place(x=750 + event.x, y=100 + event.y / 3)
        else:
            self.tooltip.place_forget()
            self.last_contour_pixel = None