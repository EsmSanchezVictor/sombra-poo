from tkinter import filedialog
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime

class PDFReportGenerator:
    def __init__(self, app):
        self.app = app
    
    def generate_report(self):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Título con fecha y sombra
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=f"Muestra {date_str} sombra", ln=True, align="C")

        # Añadir imagen con las áreas de cálculo y referencia
        self.add_image_with_selection(pdf)

        # Añadir imagen de curvas de nivel
        self.add_contour_image(pdf)

        # Información sobre las áreas y sombra
        self.add_area_info(pdf)

        # Guardar el PDF
        file_name = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_name:
            pdf.output(file_name)
            print(f"Informe guardado en {file_name}")

    def add_image_with_selection(self, pdf):
        # Guardar imagen temporal con las áreas de cálculo y referencia
        temp_img_file = tempfile.mktemp(".png")
        self.app.fig1.savefig(temp_img_file)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Áreas de cálculo y referencia", ln=True)
        pdf.image(temp_img_file, x=10, y=None, w=180)

        os.remove(temp_img_file)  # Eliminar el archivo temporal

    def add_contour_image(self, pdf):
        # Guardar imagen de las curvas de nivel
        temp_img_file = tempfile.mktemp(".png")
        self.app.fig2.savefig(temp_img_file)

        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Curvas de Nivel", ln=True)
        pdf.image(temp_img_file, x=10, y=None, w=180)

        os.remove(temp_img_file)

    def add_area_info(self, pdf):
        # Información de las áreas y porcentaje de sombra
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Información del análisis:", ln=True)

        # Dimensiones de las áreas
        calculo_dims = self.app.lbl_dimensiones_calculo.cget("text")
        referencia_dims = self.app.lbl_dimensiones_referencia.cget("text")
        promedio_referencia = self.app.lbl_promedio_referencia.cget("text")
        porcentaje_sombra = self.app.lbl_porcentaje_sombra.cget("text")
        matriz_size = self.app.matriz_size.get()

        # Escribir información en el PDF
        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 10, txt=calculo_dims, ln=True)
        pdf.cell(200, 10, txt=referencia_dims, ln=True)
        pdf.cell(200, 10, txt=promedio_referencia, ln=True)
        pdf.cell(200, 10, txt=porcentaje_sombra, ln=True)
        pdf.cell(200, 10, txt=f"Tamaño de la matriz: {matriz_size}x{matriz_size}", ln=True)
