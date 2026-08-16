"""Herramientas de análisis científico a nivel de proyecto.

Pensadas para responder las preguntas para las que existe el software:
¿cuánto ayuda la sombra en cada elemento analizado?, ¿cómo se comparan
entre sí?, ¿qué tan sensible es el resultado al % de sombra según el
propio modelo? Ninguna de estas funciones depende de tener una imagen
cargada — trabajan sobre el historial de snapshots del proyecto y/o
sobre el modelo de Temperatura directamente.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from plot_style import CMAP_TEMPERATURA, FONT_TITULO, FONT_ANOTACION


def resumen_estadistico(snapshots: list) -> dict:
    """Estadística descriptiva (n, media, mín, máx, desvío) de % de
    sombra y ΔTmrt sobre los elementos del proyecto que tienen esos
    datos calculados."""
    sombras = [s["porcentaje_sombra"] for s in snapshots if isinstance(s.get("porcentaje_sombra"), (int, float))]
    deltas = [s["delta_tmrt"] for s in snapshots if isinstance(s.get("delta_tmrt"), (int, float))]

    def _stats(values):
        if not values:
            return {"n": 0, "media": None, "min": None, "max": None, "desvio": None}
        arr = np.array(values, dtype=float)
        return {
            "n": int(arr.size),
            "media": float(np.mean(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "desvio": float(np.std(arr)),
        }

    return {
        "n_elementos": len(snapshots),
        "porcentaje_sombra": _stats(sombras),
        "delta_tmrt": _stats(deltas),
    }


def grafico_comparativo(snapshots: list, output_path: str, temp_unit: str = "°C"):
    """Gráfico de dos paneles: % de sombra y ΔTmrt por cada elemento
    analizado del proyecto. Guarda el PNG en output_path.
    Devuelve output_path, o None si no hay elementos con datos."""
    validos = [s for s in snapshots if isinstance(s.get("porcentaje_sombra"), (int, float))]
    if not validos:
        return None

    etiquetas = [s.get("label") or f"#{s.get('n', i)}" for i, s in enumerate(validos)]
    sombras = [s["porcentaje_sombra"] for s in validos]
    deltas = [s.get("delta_tmrt") if isinstance(s.get("delta_tmrt"), (int, float)) else 0.0 for s in validos]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    cmap = plt.get_cmap(CMAP_TEMPERATURA)
    colores = [cmap(v / 100) for v in sombras]

    ax1.bar(etiquetas, sombras, color=colores, edgecolor="0.3")
    ax1.set_ylabel("% de sombra")
    ax1.set_ylim(0, 100)
    ax1.set_title("Comparación de elementos analizados en el proyecto", fontsize=FONT_TITULO)

    ax2.bar(etiquetas, deltas, color="firebrick", alpha=0.85, edgecolor="0.3")
    ax2.set_ylabel(f"ΔTmrt ({temp_unit})")
    ax2.set_xlabel("Elemento")
    ax2.axhline(0, color="0.3", linewidth=0.8)
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right", fontsize=FONT_ANOTACION)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def dispersión_sombra_tmrt(snapshots: list, output_path: str, temp_unit: str = "°C"):
    """Dispersión real % de sombra vs. ΔTmrt de los elementos del
    proyecto, con línea de tendencia (regresión lineal simple). A
    diferencia de curva_sensibilidad() (puramente teórica, according al
    modelo), esto usa los DATOS REALES ya calculados de cada elemento
    — permite ver si la relación sombra→ΔTmrt se comporta como el
    modelo predice o si hay dispersión/outliers en la práctica.

    Devuelve (output_path, pendiente, r2) o (None, None, None) si no
    hay al menos 2 elementos con ambos datos.
    """
    puntos = [
        (s["porcentaje_sombra"], s["delta_tmrt"]) for s in snapshots
        if isinstance(s.get("porcentaje_sombra"), (int, float))
        and isinstance(s.get("delta_tmrt"), (int, float))
    ]
    if len(puntos) < 2:
        return None, None, None

    x = np.array([p[0] for p in puntos], dtype=float)
    y = np.array([p[1] for p in puntos], dtype=float)

    pendiente, ordenada = np.polyfit(x, y, 1)
    y_pred = pendiente * x + ordenada
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-9 else 0.0

    fig, ax = plt.subplots(figsize=(7, 5))
    cmap = plt.get_cmap(CMAP_TEMPERATURA)
    ax.scatter(x, y, c=[cmap(v / 100) for v in x], edgecolors="0.3", s=70, zorder=3)
    x_linea = np.linspace(x.min(), x.max(), 50)
    ax.plot(x_linea, pendiente * x_linea + ordenada, color="firebrick", linewidth=1.5,
            label=f"Tendencia: ΔTmrt ≈ {pendiente:.3f}·sombra {ordenada:+.2f}  (R²={r2:.2f})")
    ax.set_xlabel("% de sombra (dato real del elemento)")
    ax.set_ylabel(f"ΔTmrt real ({temp_unit})")
    ax.set_title("Dispersión real: % de sombra vs. ΔTmrt\n(datos de los elementos del proyecto)", fontsize=FONT_TITULO)
    ax.legend(fontsize=FONT_ANOTACION, loc="best")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path, float(pendiente), float(r2)


def exportar_tabla_excel(snapshots: list, output_path: str) -> str:
    """Exporta la tabla de elementos analizados a Excel — mismas
    columnas que la tabla del informe PDF, para quien prefiera analizar
    los datos en otra herramienta (Excel, pandas, R, lo que sea)."""
    import pandas as pd

    filas = []
    for entry in snapshots:
        filas.append({
            "Elemento": entry.get("label", "N/D"),
            "% sombra": entry.get("porcentaje_sombra"),
            "Tmrt sol (°C)": entry.get("tmrt_sol"),
            "Tmrt sombra (°C)": entry.get("tmrt_sombra"),
            "Delta Tmrt (°C)": entry.get("delta_tmrt"),
            "Temp. ambiente (°C)": entry.get("temp_ambient"),
            "Fecha": entry.get("timestamp"),
        })
    df = pd.DataFrame(filas)
    df.to_excel(output_path, index=False)
    return output_path


def curva_sensibilidad(temp_calculator, temp_ambient: float, fecha, hora: float,
                        output_path: str, shadow_type: str = "tree", temp_unit: str = "°C"):
    """Recorre 0-100% de sombra con la ubicación/fecha/hora/temperatura
    actuales y grafica cómo responde el Tmrt en sombra según el propio
    modelo — sin necesitar ninguna imagen. Sirve para entender la forma
    de la curva del modelo y detectar una calibración de k_factor poco
    razonable (por ejemplo, una curva casi plana o con saltos).

    Devuelve (output_path, porcentajes, valores_tmrt_sombra).
    """
    porcentajes = np.linspace(0, 100, 41)
    tmrt_sombra = []
    tmrt_sol_ref = None
    for p in porcentajes:
        resultado = temp_calculator.calculate_tmrt(
            temp_ambient, float(p), shadow_type=shadow_type,
            date_value=fecha, time_value=hora,
        )
        tmrt_sombra.append(resultado["Tmrt_sombra"])
        if tmrt_sol_ref is None:
            tmrt_sol_ref = resultado["Tmrt_sol"]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(porcentajes, tmrt_sombra, color="firebrick", linewidth=2, label="Tmrt en sombra")
    if tmrt_sol_ref is not None:
        ax.axhline(tmrt_sol_ref, color="0.4", linestyle="--", linewidth=1, label="Tmrt al sol (0% sombra)")
    ax.set_xlabel("% de sombra")
    ax.set_ylabel(f"Tmrt ({temp_unit})")
    ax.set_title(
        f"Sensibilidad Tmrt vs. % de sombra\n"
        f"(T aire {temp_ambient:.1f}{temp_unit}, {fecha}, {hora:.1f}h)",
        fontsize=FONT_TITULO,
    )
    ax.legend(fontsize=FONT_ANOTACION)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path, porcentajes, tmrt_sombra
