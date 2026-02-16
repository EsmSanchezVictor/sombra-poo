import numpy as np
import cv2
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.lines import Line2D

class ShapeSelector:
    def __init__(self, app):
        self.app = app
        self.start_point = None
        self.end_point = None
        self.area_seleccionada = None
        self.area_referencia = None
        self.shape_patch_calculo = None
        self.shape_patch_referencia = None
        self.polygon_points = []  # Para almacenar los puntos del polígono
        self.polygon_points_aux = []
        self.temp_line = None     # Línea temporal durante el dibujo
        self.polygon_closed = False  # Indica si el polígono está cerrado
        self.current_polygon_patch = None  # Para el polígono actual en dibujo
        self.selection_enabled = False
        
    def on_mouse_press(self, event):
        """Maneja el evento de clic del ratón para iniciar la selección del área."""
        if not self.selection_enabled or self.app.drawing_mode not in ("calculo", "referencia"):
            return
        if self.app.img is not None and event.inaxes == self.app.ax1:
            if self.app.selection_type.get() == "Polígono":
                if not self.polygon_points:  # Primer punto del polígono
                    self.polygon_points = [(event.xdata, event.ydata)]
                    self.polygon_closed = False
                    # Crear el patch inicial del polígono
                    color = 'blue' if self.app.drawing_mode == "calculo" else 'red'
                    self.current_polygon_patch = Polygon(
                        self.polygon_points,
                        closed=False,
                        edgecolor=color,
                        facecolor='none',
                        linewidth=2
                    )
                    self.app.ax1.add_patch(self.current_polygon_patch)
                else:
                    # Verificar si estamos cerrando el polígono (clic cerca del primer punto)
                    first_point = self.polygon_points[0]
                    distance = np.sqrt((event.xdata - first_point[0])**2 +(event.ydata - first_point[1])**2)
                    if distance < 10 and len(self.polygon_points) > 2:  # Radio de 10 píxeles
                        self.polygon_closed = True
                        self.finalize_polygon_selection()
                    else:
                        self.polygon_points.append((event.xdata, event.ydata))
                        # Actualizar el polígono visual
                        self.current_polygon_patch.set_xy(self.polygon_points)
                self.app.canvas1.draw()
            else:  # Modo rectángulo o círculo
                self.start_point = (event.xdata, event.ydata)
                self.polygon_points = []  # Resetear puntos de polígono si existían
                if self.current_polygon_patch:
                    self.current_polygon_patch.remove()
                    self.current_polygon_patch = None

    def on_mouse_move(self, event):
        """Actualiza el área seleccionada mientras el ratón se mueve."""
        if not self.selection_enabled or self.app.drawing_mode not in ("calculo", "referencia"):
            return
        if self.app.selection_type.get() == "Polígono" and self.polygon_points and not self.polygon_closed:
            # Actualizar línea temporal
            if self.temp_line:
                self.temp_line.remove()
            
            # Crear línea desde el último punto al cursor
            self.temp_line = Line2D(
                [self.polygon_points[-1][0], event.xdata],
                [self.polygon_points[-1][1], event.ydata],
                color='blue' if self.app.drawing_mode == "calculo" else 'red',
                linestyle='--'
            )
            self.app.ax1.add_line(self.temp_line)
            self.app.canvas1.draw()
        elif self.start_point is not None and event.inaxes == self.app.ax1:
            self.end_point = (event.xdata, event.ydata)
            self.update_selection()

    def on_mouse_release(self, event):
        """Completa la selección cuando el ratón se suelta."""
        if not self.selection_enabled or self.app.drawing_mode not in ("calculo", "referencia"):
            return
        if self.app.selection_type.get() != "Polígono" and self.start_point is not None and event.inaxes == self.app.ax1:
            self.end_point = (event.xdata, event.ydata)
            try:
                selected_area = self.select_area()
                if selected_area is None:
                    return
                
                if self.app.drawing_mode == "calculo":
                    self.area_seleccionada = selected_area
                    self.app.area_calculo_done = True
                    
                    # Actualizar dimensiones
                    x1, y1 = int(self.start_point[0]), int(self.start_point[1])
                    x2, y2 = int(self.end_point[0]), int(self.end_point[1])
                    width, height = abs(x2 - x1), abs(y2 - y1)
                    self.app.lbl_dimensiones_calculo.config(text=f"Dimensiones del Área de Cálculo: {width}x{height}")
                    self.app.area_ref_button.config(state='normal')
                elif self.app.drawing_mode == "referencia":
                    self.area_referencia = selected_area
                    self.app.area_referencia_done = True
                    
                    # Actualizar dimensiones
                    x1, y1 = int(self.start_point[0]), int(self.start_point[1])
                    x2, y2 = int(self.end_point[0]), int(self.end_point[1])
                    width, height = abs(x2 - x1), abs(y2 - y1)
                    self.app.lbl_dimensiones_referencia.config(text=f"Dimensiones del Área de Referencia: {width}x{height}")
                    
                    # Calcular promedio
                    promedio_referencia = np.mean(self.area_referencia)
                    self.app.lbl_promedio_referencia.config(text=f"Promedio Gris Referencia: {promedio_referencia:.2f}")
                    self.app.ref_gray_mean = promedio_referencia
                self.redraw_selection()
                
                if self.app.area_calculo_done and self.app.area_referencia_done:
                    self.app.confirm_button.config(state='normal')
                
            except Exception as e:
                print(f"Error al procesar selección: {str(e)}")
            finally:
                self.start_point = None
                self.end_point = None

    def finalize_polygon_selection(self):
        """Finaliza la selección del polígono y procesa el área."""
        if not self.selection_enabled or self.app.drawing_mode not in ("calculo", "referencia"):
            return
        if  self.app.drawing_mode == "calculo":    # aca cambien 
            self.polygon_points_aux=self.polygon_points
        if len(self.polygon_points) < 3:
            return  # No es un polígono válido
            
        # Crear máscara del polígono
        color = 'blue' if self.app.drawing_mode == "calculo" else 'red'
        polygon_patch = Polygon(
            self.polygon_points,
            closed=True,
            edgecolor=color,
            facecolor=color,  # Color semitransparente
            alpha=0.3,
            linewidth=2
        )
        
        # Eliminar el polígono temporal
        if self.current_polygon_patch:
            self.current_polygon_patch.remove()
        if self.temp_line:
            self.temp_line.remove()
            self.temp_line = None
        
        # Almacenar el patch según el modo
        if self.app.drawing_mode == "calculo":
            if self.shape_patch_calculo:
                self.shape_patch_calculo.remove()
            self.shape_patch_calculo = polygon_patch
            self.area_seleccionada = self.select_polygonal_area()
            if self.area_seleccionada is None:
                return
                
            self.app.area_calculo_done = True
            
            # Calcular rectángulo delimitador
            x_coords = [p[0] for p in self.polygon_points]
            y_coords = [p[1] for p in self.polygon_points]
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            width, height = max_x - min_x, max_y - min_y
            
            self.app.lbl_dimensiones_calculo.config(
                text=f"Dimensiones del Área de Cálculo: {int(width)}x{int(height)} (rect. delimitador)"
            )
            self.app.area_ref_button.config(state='normal')
        else:
            if self.shape_patch_referencia:
                self.shape_patch_referencia.remove()
            self.shape_patch_referencia = polygon_patch
            self.area_referencia = self.select_polygonal_area()
            if self.area_referencia is None:
                return
                
            self.app.area_referencia_done = True
            
            # Calcular rectángulo delimitador
            x_coords = [p[0] for p in self.polygon_points]
            y_coords = [p[1] for p in self.polygon_points]
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            width, height = max_x - min_x, max_y - min_y
            
            self.app.lbl_dimensiones_referencia.config(
                text=f"Dimensiones del Área de Referencia: {int(width)}x{int(height)} (rect. delimitador)"
            )
            
            # Calcular promedio
            promedio_referencia = np.mean(self.area_referencia)
            self.app.lbl_promedio_referencia.config(text=f"Promedio Gris Referencia: {promedio_referencia:.2f}")
            self.app.ref_gray_mean = promedio_referencia
            
        self.app.ax1.add_patch(polygon_patch)
        self.app.canvas1.draw()
        
        if self.app.area_calculo_done and self.app.area_referencia_done:
            self.app.confirm_button.config(state='normal')
        
        # Resetear puntos para nueva selección
        self.polygon_points = []
        self.polygon_closed = False
        self.current_polygon_patch = None
        #self.mostrar_puntos_poligono()
    def select_area(self):
        """Selecciona el área según el tipo de selección."""
        try:
            if self.app.selection_type.get() == "Rectángulo":
                return self.select_rectangular_area()
            elif self.app.selection_type.get() == "Círculo":
                return self.select_circular_area()
            elif self.app.selection_type.get() == "Polígono":
                return self.select_polygonal_area()
        except Exception as e:
            print(f"Error al seleccionar área: {str(e)}")
            return None

    def select_rectangular_area(self):
        """Selecciona y devuelve un área rectangular."""
        try:
            x1, y1 = int(self.start_point[0]), int(self.start_point[1])
            x2, y2 = int(self.end_point[0]), int(self.end_point[1])
            
            # Asegurar que las coordenadas estén dentro de los límites
            height, width = self.app.img_rgb.shape[:2]
            x1, x2 = max(0, min(x1, x2)), min(width, max(x1, x2))
            y1, y2 = max(0, min(y1, y2)), min(height, max(y1, y2))
            
            # Verificar que el área no sea cero
            if x1 >= x2 or y1 >= y2:
                print("Advertencia: Área de selección demasiado pequeña o inválida")
                return None
                
            area = self.app.img_rgb[y1:y2, x1:x2]
            
            # Verificar que el área no esté vacía
            if area.size == 0:
                print("Advertencia: Área de selección vacía")
                return None
                
            return self.app.image_processor.convertir_a_grises(area, self.app.matriz_size.get())
        except Exception as e:
            print(f"Error al seleccionar área rectangular: {str(e)}")
            return None

    def select_circular_area(self):
        """Selecciona y devuelve un área circular."""
        try:
            center_x, center_y = int(self.start_point[0]), int(self.start_point[1])
            radius = int(np.sqrt((self.end_point[0] - self.start_point[0])**2 + (self.end_point[1] - self.start_point[1])**2))

            mask = np.zeros(self.app.img_rgb.shape[:2], dtype=np.uint8)
            cv2.circle(mask, (center_x, center_y), radius, 1, thickness=-1)
            area = cv2.bitwise_and(self.app.img_rgb, self.app.img_rgb, mask=mask)
            
            # Verificar que el área no esté vacía
            if area.size == 0:
                print("Advertencia: Área circular vacía")
                return None
                
            return self.app.image_processor.convertir_a_grises(area, self.app.matriz_size.get())
        except Exception as e:
            print(f"Error al seleccionar área circular: {str(e)}")
            return None

    def select_polygonal_area(self):
        """Selecciona y devuelve un área poligonal con su rectángulo delimitador."""
        try:
            if len(self.polygon_points) < 3:
                return None
                
            # Crear máscara del polígono
            mask = np.zeros(self.app.img_rgb.shape[:2], dtype=np.uint8)
            pts = np.array([(int(x), int(y)) for x, y in self.polygon_points], dtype=np.int32)
            cv2.fillPoly(mask, [pts], 1)
            
            # Aplicar máscara a la imagen
            masked_img = cv2.bitwise_and(self.app.img_rgb, self.app.img_rgb, mask=mask)
            
            # Obtener rectángulo delimitador
            x_coords = [p[0] for p in self.polygon_points]
            y_coords = [p[1] for p in self.polygon_points]
            min_x, max_x = int(min(x_coords)), int(max(x_coords))
            min_y, max_y = int(min(y_coords)), int(max(y_coords))
            
            # Asegurar que las coordenadas estén dentro de los límites
            height, width = self.app.img_rgb.shape[:2]
            min_x, max_x = max(0, min_x), min(width, max_x)
            min_y, max_y = max(0, min_y), min(height, max_y)
            
            # Verificar que el área no sea cero
            if min_x >= max_x or min_y >= max_y:
                print("Advertencia: Área poligonal demasiado pequeña o inválida")
                return None
                
            # Extraer región del rectángulo delimitador
            bounded_area = masked_img[min_y:max_y, min_x:max_x]
            
            # Verificar que el área no esté vacía
            if bounded_area.size == 0:
                print("Advertencia: Área poligonal vacía")
                return None
                
            return self.app.image_processor.convertir_a_grises(bounded_area, self.app.matriz_size.get())
        except Exception as e:
            print(f"Error al seleccionar área poligonal: {str(e)}")
            return None

    def update_selection(self):
        """Dibuja el área seleccionada en la imagen mientras el ratón se mueve."""
        color = 'blue' if self.app.drawing_mode == "calculo" else 'red'

        if self.app.drawing_mode == "calculo" and self.shape_patch_calculo:
            self.shape_patch_calculo.remove()
            self.shape_patch_calculo = None
        elif self.app.drawing_mode == "referencia" and self.shape_patch_referencia:
            self.shape_patch_referencia.remove()
            self.shape_patch_referencia = None

        if self.app.selection_type.get() == "Rectángulo":
            width = self.end_point[0] - self.start_point[0]
            height = self.end_point[1] - self.start_point[1]
            shape_patch = Rectangle(self.start_point, width, height,edgecolor=color, facecolor='none', linewidth=2)
        elif self.app.selection_type.get() == "Círculo":
            radius = np.sqrt((self.end_point[0] - self.start_point[0])**2 + (self.end_point[1] - self.start_point[1])**2)
            shape_patch = Circle(self.start_point, radius, 
                                edgecolor=color, facecolor='none', linewidth=2)

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
        self.app._setup_hover_shadow_percent_photo(self.app.ax1, self.app.canvas1, self.app.img_rgb)

        if self.shape_patch_calculo:
            self.app.ax1.add_patch(self.shape_patch_calculo)
        if self.shape_patch_referencia:
            self.app.ax1.add_patch(self.shape_patch_referencia)

        self.app.canvas1.draw()

    def reset_polygon(self):
        """Resetea la selección del polígono."""
        self.polygon_points = []
        self.polygon_closed = False
        if self.temp_line:
            self.temp_line.remove()
            self.temp_line = None
        if self.current_polygon_patch:
            self.current_polygon_patch.remove()
            self.current_polygon_patch = None
        self.redraw_selection()

    def enable_calculo_button(self):
        self.app.area_calc_button.config(state='normal')
        self.app.save_dataset_button.config(state='normal')

    def select_area_calculo(self):
        self.app.selection_mode = "calc"
        self.app.drawing_mode = "calculo"
        self.selection_enabled = True
        self.reset_polygon()

    def select_area_referencia(self):
        self.app.selection_mode = "ref"
        self.app.drawing_mode = "referencia"
        self.selection_enabled = True
        self.reset_polygon()
        

    def disable_selection(self):
        self.selection_enabled = False
        self.app.selection_mode = None
        self.app.drawing_mode = None
        self.start_point = None
        self.end_point = None
        if self.temp_line:
            self.temp_line.remove()
            self.temp_line = None
        if self.current_polygon_patch:
            self.current_polygon_patch.remove()
            self.current_polygon_patch = None
        if hasattr(self.app, "canvas1") and self.app.canvas1 is not None:
            self.app.canvas1.draw_idle()

    def clear_panel2_selection(self):
        self.disable_selection()
        self.area_seleccionada = None
        self.area_referencia = None
        self.polygon_points = []
        self.polygon_points_aux = []
        self.polygon_closed = False
        if self.shape_patch_calculo:
            self.shape_patch_calculo.remove()
            self.shape_patch_calculo = None
        if self.shape_patch_referencia:
            self.shape_patch_referencia.remove()
            self.shape_patch_referencia = None
        
    def mostrar_puntos_poligono(self):
        """Muestra en consola los puntos actuales del polígono con su índice"""
        if not self.polygon_points_aux:
            print("No hay puntos definidos en el polígono")
            return
        
        print("\n=== Puntos del polígono ===")
        print(f"Total de puntos: {len(self.polygon_points_aux)}")
        print("Lista de puntos (x, y):")
        
        for i, (x, y) in enumerate(self.polygon_points_aux, 1):
            print(f"Punto {i}: ({x:.2f}, {y:.2f})")
        
        if self.polygon_closed:
            print("\n⚠ El polígono está CERRADO (primer y último punto conectados)")
        else:
            print("\n⚠ El polígono está ABIERTO (falta conectar el último punto con el primero)")
        
        print("==========================\n")