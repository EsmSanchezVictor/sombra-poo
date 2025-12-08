import tkinter as tk    
def reset(self):
        """Restablecer todas las selecciones y la interfaz gráfica"""
        self.start_point = None
        self.end_point = None
        self.shape_patch_calculo = None
        self.shape_patch_referencia = None
        self.area_seleccionada = None
        self.area_referencia = None
        self.img = None
        self.area_calculo_done = False
        self.area_referencia_done = False

        # Resetear la interfaz gráfica
        self.ax1.clear()
        self.canvas1.draw()

        self.ax2.clear()
        self.canvas2.draw()

        # Deshabilitar botones y etiquetas
        self.btn_area_calculo.config(state=tk.DISABLED)
        self.btn_area_referencia.config(state=tk.DISABLED)
        self.btn_confirmar.config(state=tk.DISABLED)
        self.btn_curvas.config(state=tk.DISABLED)
        self.btn_exportar.config(state=tk.DISABLED)
        self.btn_guardar.config(state=tk.DISABLED)

        self.lbl_dimensiones_calculo.config(text="Dimensiones del Área de Cálculo: N/A")
        self.lbl_dimensiones_referencia.config(text="Dimensiones del Área de Referencia: N/A")
        self.lbl_porcentaje_sombra.config(text="Porcentaje de sombra: N/A")
        self.lbl_promedio_referencia.config(text="Promedio Gris Referencia: N/A")