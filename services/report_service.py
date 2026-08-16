"""Informe PDF completo del proyecto.

A diferencia de save_pdf.py (que arma un reporte de UN elemento
puntual), esto consolida TODO el proyecto: resumen estadístico, tabla
de todos los elementos analizados, el gráfico comparativo entre ellos,
la curva de sensibilidad del modelo, y los últimos artefactos visuales
disponibles (curva de nivel e histograma).

NOTA TÉCNICA: FPDF (la librería que ya usa save_pdf.py) con sus fuentes
core solo soporta latin-1 — los caracteres "Δ" y "σ" rompen la
generación. Los gráficos (donde sí se ven "Δ"/"σ"/"°" sin problema,
porque los renderiza matplotlib) los evitan reemplazándolos por
"Delta"/"desvio" en el texto plano del PDF.
"""
from __future__ import annotations

import os
from datetime import datetime

from services import analysis_service


def _fmt(value, unidad=""):
    if value is None:
        return "N/D"
    return f"{value:.2f}{unidad}"


def generar_informe_proyecto(app, project, output_path: str) -> str:
    """Arma el PDF completo y lo guarda en output_path. Devuelve la
    ruta final (puede diferir si output_path ya existía y se versionó)."""
    from fpdf import FPDF
    from core.file_versioning import safe_path

    snapshots = getattr(app, "snapshots", []) or []
    resumen = analysis_service.resumen_estadistico(snapshots)

    analisis_dir = os.path.join(project.root_path, "resultados", "analisis")
    os.makedirs(analisis_dir, exist_ok=True)

    comparativo_path = None
    if resumen["porcentaje_sombra"]["n"]:
        comparativo_path = analysis_service.grafico_comparativo(
            snapshots, os.path.join(analisis_dir, "comparativo_elementos.png"),
        )

    dispersion_path, pendiente, r2 = analysis_service.dispersión_sombra_tmrt(
        snapshots, os.path.join(analisis_dir, "dispersion_sombra_tmrt.png"),
    )

    # NUEVO: tabla también en Excel, junto al PDF en la misma carpeta.
    if snapshots:
        try:
            analysis_service.exportar_tabla_excel(
                snapshots, os.path.join(analisis_dir, "elementos_proyecto.xlsx"),
            )
        except Exception as exc:
            print(f"[informe] No se pudo exportar la tabla a Excel: {exc}")

    sensibilidad_path = None
    try:
        from shadow_temp import Temperatura
        temp_ambient, hora, fecha, lat, lon = app._leer_parametros_tmrt()
        calculador = Temperatura(lat, lon)
        sensibilidad_path, _, _ = analysis_service.curva_sensibilidad(
            calculador, temp_ambient, fecha, hora,
            os.path.join(analisis_dir, "sensibilidad_sombra.png"),
        )
    except Exception as exc:
        print(f"[informe] No se pudo generar la curva de sensibilidad: {exc}")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Portada ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 15, txt=f"Informe de análisis - {project.name}", ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, txt=f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    loc = getattr(app, "current_location", None) or {}
    if loc:
        pdf.cell(
            0, 8,
            txt=f"Ubicacion: {loc.get('city', 'N/D')} ({loc.get('lat', 'N/D')}, {loc.get('lon', 'N/D')})",
            ln=True, align="C",
        )
    pdf.ln(6)

    # --- Resumen estadístico ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, txt="Resumen estadistico del proyecto", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, txt=f"Elementos analizados: {resumen['n_elementos']}", ln=True)

    s = resumen["porcentaje_sombra"]
    if s["n"]:
        pdf.cell(
            0, 7,
            txt=f"% de sombra -- media {s['media']:.1f}% | min {s['min']:.1f}% | "
                f"max {s['max']:.1f}% | desvio {s['desvio']:.1f}%",
            ln=True,
        )
    d = resumen["delta_tmrt"]
    if d["n"]:
        pdf.cell(
            0, 7,
            txt=f"Delta Tmrt -- media {d['media']:.2f} C | min {d['min']:.2f} C | "
                f"max {d['max']:.2f} C | desvio {d['desvio']:.2f} C",
            ln=True,
        )
    if not s["n"] and not d["n"]:
        pdf.cell(0, 7, txt="Todavia no hay elementos con datos calculados en este proyecto.", ln=True)

    # --- Gráfico comparativo ---
    if comparativo_path and os.path.exists(comparativo_path):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Comparacion entre elementos del proyecto", ln=True)
        pdf.image(comparativo_path, x=10, y=None, w=180)

    # --- Dispersión real (datos del proyecto) ---
    if dispersion_path and os.path.exists(dispersion_path):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Dispersion real: % de sombra vs. Delta Tmrt", ln=True)
        if pendiente is not None and r2 is not None:
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, txt=f"Tendencia lineal: pendiente {pendiente:.3f}  |  R2 {r2:.2f}", ln=True)
        pdf.image(dispersion_path, x=25, y=None, w=150)

    # --- Curva de sensibilidad ---
    if sensibilidad_path and os.path.exists(sensibilidad_path):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Sensibilidad del modelo: Tmrt vs. % de sombra", ln=True)
        pdf.image(sensibilidad_path, x=25, y=None, w=150)

    # --- Tabla de elementos ---
    if snapshots:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Detalle de elementos analizados", ln=True)
        pdf.set_font("Arial", "B", 9)
        headers = ["Elemento", "% sombra", "Tmrt sol", "Tmrt sombra", "Delta Tmrt", "Fecha"]
        widths = [45, 25, 28, 30, 28, 34]
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, txt=h, border=1, align="C")
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for entry in snapshots:
            fila = [
                str(entry.get("label", "N/D"))[:22],
                _fmt(entry.get("porcentaje_sombra"), "%"),
                _fmt(entry.get("tmrt_sol"), " C"),
                _fmt(entry.get("tmrt_sombra"), " C"),
                _fmt(entry.get("delta_tmrt"), " C"),
                str(entry.get("timestamp", "N/D"))[:16],
            ]
            for valor, w in zip(fila, widths):
                pdf.cell(w, 8, txt=valor, border=1, align="C")
            pdf.ln()

    # --- Últimos artefactos visuales ---
    curve_path = getattr(app, "last_curve_path", None)
    histogram_path = getattr(app, "last_histogram_path", None)
    if (curve_path and os.path.exists(curve_path)) or (histogram_path and os.path.exists(histogram_path)):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Ultimo elemento procesado", ln=True)
        if curve_path and os.path.exists(curve_path):
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, txt="Curva de temperatura en sombra:", ln=True)
            pdf.image(curve_path, x=10, y=None, w=180)
        if histogram_path and os.path.exists(histogram_path):
            pdf.add_page()
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, txt="Histograma:", ln=True)
            pdf.image(histogram_path, x=10, y=None, w=180)

    final_path = safe_path(os.path.dirname(output_path), os.path.basename(output_path))
    pdf.output(str(final_path))
    return str(final_path)
