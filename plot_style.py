"""Estilo y helpers compartidos para todos los gráficos de la app.

POR QUÉ EXISTE ESTE ARCHIVO:
Hoy cada gráfico define su propio estilo por separado y hay dos paletas
de color conviviendo sin criterio: `temp_graph.py` usa "jet" y el
histograma en `ui/app_ui.py::mostrar_curvas_nivel()` usa "viridis". Esto
tiene dos problemas:

1. Científico: "jet" NO es perceptualmente uniforme (es el ejemplo de
   libro de mala práctica en visualización científica) — puede hacer
   ver un salto brusco de temperatura donde el dato cambia suave, o
   esconder un cambio real donde el color "se estanca". "viridis" y
   "RdYlBu_r" sí son uniformes y son estándar en literatura de
   biometeorología urbana para mapas de temperatura.
2. De lectura: si cada figura arma su propia escala de color con su
   propio mínimo/máximo, dos fotos del mismo sitio en momentos
   distintos no se pueden comparar a simple vista — el mismo color
   puede significar temperaturas distintas en cada imagen.

Este módulo centraliza: la paleta a usar por tipo de dato, tamaños de
fuente legibles, y funciones para agregar colorbar con unidades,
anotaciones estadísticas (media/mediana/desvío) y metadatos de
reproducibilidad (fecha, % sombra, N de píxeles) directamente sobre
el gráfico.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

# --- Paletas por tipo de dato ------------------------------------------
# Reemplaza el uso disperso de "jet". RdYlBu_r es divergente y muy usada
# en literatura de confort térmico urbano (rojo = más caliente).
CMAP_TEMPERATURA = "RdYlBu_r"
CMAP_HISTOGRAMA = "viridis"
CMAP_CURVAS_NIVEL = "RdYlBu_r"

FONT_TITULO = 12
FONT_EJES = 10
FONT_ANOTACION = 9


def aplicar_estilo_base():
    """Tamaños y tipografía consistentes en toda la app. Llamar una vez
    al arrancar (por ejemplo, en el punto de entrada de la UI)."""
    plt.rcParams.update({
        "font.size": FONT_EJES,
        "axes.titlesize": FONT_TITULO,
        "axes.labelsize": FONT_EJES,
        "figure.autolayout": False,
        "axes.grid": False,
    })


def agregar_colorbar_temperatura(fig, ax, mappable, unidad: str = "°C"):
    """Agrega una colorbar con etiqueta de unidad — antes varias figuras
    (ej. curvas de nivel) no tenían colorbar, así que no se podía leer
    ningún valor concreto del gráfico, solo la forma."""
    cbar = fig.colorbar(mappable, ax=ax)
    cbar.set_label(f"Temperatura ({unidad})", fontsize=FONT_EJES)
    cbar.ax.tick_params(labelsize=FONT_ANOTACION)
    return cbar


def anotar_estadisticas(ax, valores: np.ndarray, unidad: str = ""):
    """Dibuja líneas verticales de media y mediana con su valor, y un
    cuadro de texto con desvío estándar y N. Antes el histograma no
    mostraba ningún resumen numérico — solo la forma de la distribución."""
    valores = np.asarray(valores).flatten()
    valores = valores[~np.isnan(valores)]
    if valores.size == 0:
        return
    media = float(np.mean(valores))
    mediana = float(np.median(valores))
    desvio = float(np.std(valores))

    ax.axvline(media, color="firebrick", linestyle="--", linewidth=1.2,
               label=f"Media = {media:.1f}{unidad}")
    ax.axvline(mediana, color="black", linestyle=":", linewidth=1.2,
               label=f"Mediana = {mediana:.1f}{unidad}")
    ax.legend(fontsize=FONT_ANOTACION, loc="upper right")
    ax.text(
        0.02, 0.95,
        f"N = {valores.size}\nσ = {desvio:.1f}{unidad}",
        transform=ax.transAxes, fontsize=FONT_ANOTACION,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.75, edgecolor="0.7"),
    )


def anotar_metadatos(fig, texto: str):
    """Estampa una línea de metadatos (fecha, % sombra, archivo fuente,
    k_factor usado) al pie de la figura, para que cualquier imagen
    exportada sea reproducible sin depender de recordar qué la generó.

    CORRECCIÓN: antes el texto se escribía en fig.text(0.01, 0.01, ...),
    pegado al borde físico de la figura, sin reservarle espacio propio —
    eso lo hacía superponerse con la etiqueta del eje X (ej. "Nivel de
    gris") cada vez que tight_layout() recalculaba el layout después.
    Ahora se reserva un margen inferior real con subplots_adjust ANTES
    de ubicar el texto, así el texto y el eje X nunca compiten por el
    mismo espacio. Debe llamarse DESPUÉS de cualquier tight_layout().
    """
    fig.subplots_adjust(bottom=0.22)
    fig.text(0.5, 0.03, texto, fontsize=FONT_ANOTACION - 1, color="0.4",
              ha="center", va="bottom")
