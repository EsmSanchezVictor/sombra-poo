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
from core.model_registry import SCIENTIFIC_RELEASE, SCIENTIFIC_SCHEMA


def _fmt(value, unidad=""):
    if value is None:
        return "N/D"
    return f"{value:.2f}{unidad}"


def generar_informe_proyecto(app, project, output_path: str) -> str:
    """Arma el PDF completo y lo guarda en output_path. Devuelve la
    ruta final (puede diferir si output_path ya existía y se versionó)."""
    from fpdf import FPDF

    snapshots = getattr(app, "snapshots", []) or []
    resumen = analysis_service.resumen_estadistico(snapshots)

    analisis_dir = project.layout.project_results_dir
    os.makedirs(analisis_dir, exist_ok=True)

    comparativo_path = None
    if resumen["porcentaje_sombra"]["n"]:
        comparativo_path = analysis_service.grafico_comparativo(
            snapshots, project.layout.comparison_chart,
        )

    dispersion_path, pendiente, r2 = analysis_service.dispersión_sombra_tmrt(
        snapshots, project.layout.scatter_chart,
    )

    # NUEVO: tabla también en Excel, junto al PDF en la misma carpeta.
    if snapshots:
        try:
            analysis_service.exportar_tabla_excel(
                snapshots, project.layout.elements_excel,
            )
        except Exception as exc:
            print(f"[informe] No se pudo exportar la tabla a Excel: {exc}")

    sensibilidad_path = None
    try:
        from shadow_temp import Temperatura
        temp_ambient, hora, fecha, lat, lon = app._leer_parametros_tmrt()
        calculador = Temperatura(
            lat, lon, k_factor=getattr(app, "k_factor", 0.04),
            model_mode=getattr(getattr(app, "tmrt_model_mode", None), "get", lambda: "standard")(),
        )
        sensibilidad_path, _, _ = analysis_service.curva_sensibilidad(
            calculador, temp_ambient, fecha, hora,
            project.layout.sensitivity_chart,
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
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 6, txt=f"Release cientifico: {SCIENTIFIC_RELEASE} | esquema: {SCIENTIFIC_SCHEMA}", ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    loc = getattr(app, "current_location", None) or {}
    if loc:
        pdf.cell(
            0, 8,
            txt=f"Ubicacion: {loc.get('city', 'N/D')} ({loc.get('lat', 'N/D')}, {loc.get('lon', 'N/D')})",
            ln=True, align="C",
        )
    model_mode = getattr(getattr(app, "tmrt_model_mode", None), "get", lambda: "standard")()
    model_name = "Avanzado - balance radiativo v1" if model_mode == "advanced" else "Estandar - empirico calibrable"
    pdf.cell(0, 8, txt=f"Modelo Tmrt activo: {model_name}", ln=True, align="C")
    surface_mode = getattr(getattr(app, "surface_model_mode", None), "get", lambda: "standard")()
    surface_name = ({
        "advanced": "Avanzado seco - balance energetico no lineal v1",
        "advanced_vegetation": "Avanzado vegetacion + ET - balance energetico v2",
    }.get(surface_mode, "Estandar - linealizado legacy"))
    pdf.cell(0, 8, txt=f"Modelo de superficie activo: {surface_name}", ln=True, align="C")
    met = getattr(app, "last_meteorology_data", None) or {}
    source_mode = getattr(getattr(app, "radiation_source_mode", None), "get", lambda: "clear_sky")()
    source_label = met.get("source_label") or {
        "clear_sky": "Cielo despejado modelado",
        "manual_measured": "Medicion puntual ingresada",
        "manual_scenario": "Escenario radiativo manual",
        "observed_series": "Serie meteorologica importada",
    }.get(source_mode, source_mode)
    pdf.cell(0, 8, txt=f"Fuente radiativa: {source_label}", ln=True, align="C")
    if met:
        quality = met.get("quality", "N/D")
        derived = ", ".join(met.get("derived_components", []) or []) or "ninguno"
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, txt=(
            f"Radiacion: GHI={met.get('ghi', 0):.1f} | DNI={met.get('dni', 0):.1f} | DHI={met.get('dhi', 0):.1f} W/m2"
        ), ln=True, align="C")
        pdf.cell(0, 6, txt=f"Calidad/procedencia: {quality} | componentes derivados: {derived}", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
    if surface_mode == "advanced_vegetation":
        settings = getattr(app, "settings", {}) or {}
        pdf.cell(0, 7, txt=(
            f"Vegetacion: suelo={float(settings.get('ground_vegetation_fraction', 0.50)):.2f} | "
            f"agua suelo={float(settings.get('vegetation_water_availability', 0.75)):.2f} | "
            f"agua copa={float(settings.get('canopy_water_availability', 0.75)):.2f}"
        ), ln=True, align="C")
    tmrt_result = getattr(app, "tmrt_result", None) or {}
    unc = tmrt_result.get("Incertidumbre_operativa") or {}
    shade_unc = unc.get("tmrt_shade") or {}
    if shade_unc.get("p05") is not None and shade_unc.get("p95") is not None:
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, txt=(
            f"Tmrt sombra - intervalo operativo P05-P95: {shade_unc['p05']:.1f} a {shade_unc['p95']:.1f} C"
        ), ln=True, align="C")
        pdf.cell(0, 6, txt="Intervalo de sensibilidad por supuestos; no es un intervalo de confianza instrumental.", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
    pdf.ln(6)

    # --- Resumen estadístico ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, txt="Resumen estadistico del proyecto", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, txt=f"Elementos analizados: {resumen['n_elementos']}", ln=True)

    s = resumen["cobertura_sombra"]
    if s["n"]:
        pdf.cell(
            0, 7,
            txt=f"Cobertura de sombra -- media {s['media']:.1f}% | min {s['min']:.1f}% | "
                f"max {s['max']:.1f}% | desvio {s['desvio']:.1f}%",
            ln=True,
        )
    a = resumen["atenuacion_sombra"]
    if a["n"]:
        pdf.cell(
            0, 7,
            txt=f"Atenuacion en sombra -- media {a['media']:.1f}% | min {a['min']:.1f}% | "
                f"max {a['max']:.1f}% | desvio {a['desvio']:.1f}%",
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
        pdf.cell(0, 10, txt="Cobertura de sombra vs. Delta Tmrt modelada", ln=True)
        if pendiente is not None and r2 is not None:
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, txt=f"Tendencia lineal: pendiente {pendiente:.3f}  |  R2 {r2:.2f}", ln=True)
        pdf.image(dispersion_path, x=25, y=None, w=150)

    # --- Curva de sensibilidad ---
    if sensibilidad_path and os.path.exists(sensibilidad_path):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Sensibilidad del modelo: Tmrt vs. cobertura de sombra", ln=True)
        pdf.image(sensibilidad_path, x=25, y=None, w=150)

    # --- Tabla de elementos ---
    if snapshots:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Detalle de elementos analizados", ln=True)
        pdf.set_font("Arial", "B", 9)
        headers = ["Elemento", "Cobertura", "Atenuacion", "Tmrt sol", "Tmrt sombra", "Delta Tmrt", "Fecha"]
        widths = [36, 22, 22, 25, 27, 25, 33]
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, txt=h, border=1, align="C")
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for entry in snapshots:
            fila = [
                str(entry.get("label", "N/D"))[:22],
                _fmt(entry.get("cobertura_sombra", entry.get("porcentaje_sombra")), "%"),
                _fmt(entry.get("atenuacion_sombra"), "%"),
                _fmt(entry.get("tmrt_sol"), " C"),
                _fmt(entry.get("tmrt_sombra"), " C"),
                _fmt(entry.get("delta_tmrt"), " C"),
                str(entry.get("timestamp", "N/D"))[:16],
            ]
            for valor, w in zip(fila, widths):
                pdf.cell(w, 8, txt=valor, border=1, align="C")
            pdf.ln()

    # --- Auditoria cientifica interna ---
    audit = getattr(app, "last_scientific_audit", None) or {}
    if audit:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Auditoria interna de preparacion cientifica", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 6, txt=str(audit.get("readiness", "N/D")))
        counts = audit.get("counts") or {}
        pdf.cell(0, 6, txt=(
            f"OK={counts.get('pass', 0)} | advertencias={counts.get('warning', 0)} | fallas={counts.get('fail', 0)}"
        ), ln=True)
        for item in audit.get("items", [])[:30]:
            level = str(item.get("level", "info")).upper()
            title = str(item.get("title", ""))
            detail = str(item.get("detail", ""))
            pdf.multi_cell(0, 5, txt=f"[{level}] {title}: {detail}")

    # --- Validacion cientifica ---
    validation = getattr(app, "last_validation_summary", None) or {}
    metrics_models = validation.get("metricas_modelos") or {}
    if metrics_models:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt="Validacion cientifica de modelos", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, txt=f"Particion: {validation.get('split_source', 'N/D')}", ln=True)
        pdf.cell(0, 6, txt=(
            f"k actual={validation.get('k_actual', 0):.5f} | k calibrado={validation.get('k_calibrado', 0):.5f}"
        ), ln=True)
        pdf.ln(2)
        headers = ["Modelo", "n", "RMSE", "MAE", "Bias", "R2"]
        widths = [55, 15, 25, 25, 25, 25]
        pdf.set_font("Arial", "B", 9)
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, txt=h, border=1, align="C")
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for model, metv in metrics_models.items():
            if not metv:
                row = [str(model)[:30], "-", "-", "-", "-", "-"]
            else:
                row = [
                    str(model)[:30], str(metv.get("n", "-")),
                    f"{metv.get('rmse', float('nan')):.2f}",
                    f"{metv.get('mae', float('nan')):.2f}",
                    f"{metv.get('bias', float('nan')):+.2f}",
                    f"{metv.get('r2', float('nan')):.3f}",
                ]
            for val, w in zip(row, widths):
                pdf.cell(w, 8, txt=val, border=1, align="C")
            pdf.ln()
        warnings = validation.get("advertencias") or []
        if warnings:
            pdf.ln(4)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 6, txt="Advertencias de trazabilidad:", ln=True)
            pdf.set_font("Arial", "", 8)
            for warning in warnings[:8]:
                safe = str(warning).replace("•", "-").replace("≥", ">=")
                pdf.multi_cell(0, 5, txt=f"- {safe}")

    # --- Últimos artefactos visuales ---
    curve_path = getattr(app, "last_curve_path", None)
    histogram_path = getattr(app, "last_histogram_path", None)
    classification_path = getattr(app, "last_shadow_classification_path", None)
    if ((curve_path and os.path.exists(curve_path))
            or (histogram_path and os.path.exists(histogram_path))
            or (classification_path and os.path.exists(classification_path))):
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
        if classification_path and os.path.exists(classification_path):
            pdf.add_page()
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, txt="Clasificacion fotografica sombra / sol:", ln=True)
            pdf.image(classification_path, x=25, y=None, w=150)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(str(output_path))
    return str(output_path)
