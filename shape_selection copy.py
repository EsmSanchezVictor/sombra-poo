
import numpy as np
from matplotlib.patches import Rectangle, Circle

class ShapeSelector:
    def __init__(self, app):
        self.app = app
        self.start_point = None
        self.end_point = None
        self.area_seleccionada = None
        self.area_referencia = None
        self.shape_patch_calculo = None
        self.shape_patch_referencia = None

    def on_mouse_press(self, event):
        """Maneja el evento de clic del ratón para iniciar la selección del área."""
        if self.app.img is not None and event.inaxes == self.app.ax1:
            self.start_point = (event.xdata, event.ydata)

    def on_mouse_move(self, event):
        """Actualiza el área seleccionada mientras el ratón se mueve."""
        if self.start_point is not None and event.inaxes == self.app.ax1:
            self.end_point = (event.xdata, event.ydata)
            self.update_selection()

    def on_mouse_release(self, event):
        """Completa la selección cuando el ratón se suelta."""
        if self.start_point is not None and event.inaxes == self.app.ax1:
            self.end_point = (event.xdata, event.ydata)
            if self.app.drawing_mode == "calculo":
                # Selección de área de cálculo
                self.area_seleccionada = self.select_area()
                self.app.area_calculo_done = True

                # Actualizar las dimensiones del área de cálculo en la interfaz
                x1, y1 = int(self.start_point[0]), int(self.start_point[1])
                x2, y2 = int(self.end_point[0]), int(self.end_point[1])
                width, height = abs(x2 - x1), abs(y2 - y1)
                self.app.lbl_dimensiones_calculo.config(text=f"Dimensiones del Área de Cálculo: {width}x{height}")

                # Habilitar selección de área de referencia
                self.app.area_ref_button.config(state='normal')

            elif self.app.drawing_mode == "referencia":
                # Selección de área de referencia
                self.area_referencia = self.select_area()
                self.app.area_referencia_done = True

                # Actualizar las dimensiones del área de referencia en la interfaz
                x1, y1 = int(self.start_point[0]), int(self.start_point[1])
                x2, y2 = int(self.end_point[0]), int(self.end_point[1])
                width, height = abs(x2 - x1), abs(y2 - y1)
                self.app.lbl_dimensiones_referencia.config(text=f"Dimensiones del Área de Referencia: {width}x{height}")

                # Calcular y mostrar el promedio de gris del área de referencia
                promedio_referencia = np.mean(self.area_referencia)
                self.app.lbl_promedio_referencia.config(text=f"Promedio Gris Referencia: {promedio_referencia:.2f}")

            # Redibujar la imagen con las áreas seleccionadas
            self.redraw_selection()

            # Habilitar el botón de confirmación si ambas áreas están seleccionadas
            if self.app.area_calculo_done and self.app.area_referencia_done:
                self.app.confirm_button.config(state='normal')
                print(self.app.area_calculo_done," ",self.app.area_referencia_done)
            # Reiniciar los puntos para la próxima selección
            self.start_point = None
            self.end_point = None

    def select_area(self):
        """Selecciona el área (rectángulo o círculo) según el tipo de selección."""
        if self.app.selection_type.get() == "Rectángulo":
            return self.select_rectangular_area()
        elif self.app.selection_type.get() == "Círculo":
            return self.select_circular_area()

    def select_rectangular_area(self):
        """Selecciona y devuelve un área rectangular basada en los puntos seleccionados."""
        x1, y1 = int(self.start_point[0]), int(self.start_point[1])
        x2, y2 = int(self.end_point[0]), int(self.end_point[1])
        area = self.app.img_rgb[min(y1, y2):max(y1, y2), min(x1, x2):max(x1, x2)]
        return self.app.image_processor.convertir_a_grises(area, self.app.matriz_size.get())

    def select_circular_area(self):
        """Selecciona y devuelve un área circular basada en los puntos seleccionados."""
        center_x, center_y = int(self.start_point[0]), int(self.start_point[1])
        radius = int(np.sqrt((self.end_point[0] - self.start_point[0])**2 + (self.end_point[1] - self.start_point[1])**2))

        # Crear una máscara circular y aplicarla a la imagen
        mask = np.zeros(self.app.img_rgb.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), radius, 1, thickness=-1)
        area = cv2.bitwise_and(self.app.img_rgb, self.app.img_rgb, mask=mask)
        return self.app.image_processor.convertir_a_grises(area, self.app.matriz_size.get())

    def update_selection(self):
        """Dibuja el área seleccionada en la imagen mientras el ratón se mueve."""
        color = 'blue' if self.app.drawing_mode == "calculo" else 'red'

        # Elimina la figura anterior si existe
        if self.app.drawing_mode == "calculo" and self.shape_patch_calculo:
            self.shape_patch_calculo.remove()
        elif self.app.drawing_mode == "referencia" and self.shape_patch_referencia:
            self.shape_patch_referencia.remove()

        # Crea una nueva figura (rectángulo o círculo) mientras el ratón se mueve
        if self.app.selection_type.get() == "Rectángulo":
            width = self.end_point[0] - self.start_point[0]
            height = self.end_point[1] - self.start_point[1]
            shape_patch = Rectangle(self.start_point, width, height, edgecolor=color, facecolor='none', linewidth=2)
        elif self.app.selection_type.get() == "Círculo":
            radius = np.sqrt((self.end_point[0] - self.start_point[0])**2 + (self.end_point[1] - self.start_point[1])**2)
            shape_patch = Circle(self.start_point, radius, edgecolor=color, facecolor='none', linewidth=2)

        # Almacenar la figura creada
        if self.app.drawing_mode == "calculo":
            self.shape_patch_calculo = shape_patch
        else:
            self.shape_patch_referencia = shape_patch

        self.app.ax1.add_patch(shape_patch)
        self.app.canvas1.draw()

    def redraw_selection(self):
        """Redibuja la imagen con las áreas seleccionadas."""
        self.app.ax1.clear()
        self.app.ax1.imshow(self.app.img_rgb)

        if self.shape_patch_calculo:
            self.app.ax1.add_patch(self.shape_patch_calculo)

        if self.shape_patch_referencia:
            self.app.ax1.add_patch(self.shape_patch_referencia)

        self.app.canvas1.draw()

    def enable_calculo_button(self):
        """Habilita el botón para seleccionar el área de cálculo."""
        self.app.area_calc_button.config(state='normal')
        

    def select_area_calculo(self):
        """Cambia al modo de selección del área de cálculo."""
        self.app.drawing_mode = "calculo"

    def select_area_referencia(self):
        """Cambia al modo de selección del área de referencia."""
        self.app.drawing_mode = "referencia"
