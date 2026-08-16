"""Generación de íconos simples para la barra de herramientas (ribbon).

Se dibujan en tiempo de ejecución con PIL en vez de cargarse desde
archivos — no hay assets de ícono para las acciones nuevas (Nuevo/
Abrir/Guardar/Ejecutar/Análisis), y este entorno no tiene forma de
descargar un set de íconos. Son pictogramas simples (trazo de 2px,
color único) — no reemplazan a los 4 PNG existentes (fiebre/sombra/
config/vista-3d) que ya identifican los paneles, esos se siguen
usando tal cual desde ui/app_ui.py.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageTk

_CACHE: dict = {}


def _lienzo(size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _nuevo(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    m = size * 0.16
    d.rectangle([m, m, size - m, size - m], outline=color, width=2)
    cx, cy, r = size / 2, size / 2, size * 0.16
    d.line([cx - r, cy, cx + r, cy], fill=color, width=2)
    d.line([cx, cy - r, cx, cy + r], fill=color, width=2)
    return img


def _abrir(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    m = size * 0.14
    d.polygon(
        [(m, m + size * 0.12), (size * 0.42, m + size * 0.12), (size * 0.52, m + size * 0.02),
         (size - m, m + size * 0.02), (size - m, size - m), (m, size - m)],
        outline=color, width=2,
    )
    return img


def _guardar(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    m = size * 0.16
    d.rectangle([m, m, size - m, size - m], outline=color, width=2)
    d.rectangle([size * 0.32, m, size * 0.68, size * 0.42], outline=color, width=2)
    d.rectangle([size * 0.32, size * 0.6, size * 0.68, size - m], fill=color)
    return img


def _play(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    m = size * 0.22
    d.polygon([(m, m), (m, size - m), (size - m, size / 2)], fill=color)
    return img


def _barras(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    base = size * 0.85
    for i, h in enumerate([0.35, 0.65, 0.5, 0.8]):
        x0 = size * (0.10 + i * 0.21)
        x1 = x0 + size * 0.15
        d.rectangle([x0, base - size * h, x1, base], fill=color)
    d.line([size * 0.06, base, size * 0.94, base], fill=color, width=2)
    return img


def _curva(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    puntos = [
        (size * 0.1, size * 0.75), (size * 0.3, size * 0.55),
        (size * 0.5, size * 0.65), (size * 0.7, size * 0.3),
        (size * 0.9, size * 0.2),
    ]
    d.line(puntos, fill=color, width=2, joint="curve")
    for p in puntos:
        r = size * 0.035
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)
    return img


def _pdf(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    m = size * 0.18
    d.polygon(
        [(m, m), (size * 0.62, m), (size - m, size * 0.32), (size - m, size - m), (m, size - m)],
        outline=color, width=2,
    )
    for i in range(3):
        y = size * (0.55 + i * 0.13)
        d.line([m + size * 0.08, y, size - m - size * 0.08, y], fill=color, width=1)
    return img


def _logo(size, color):
    img = _lienzo(size)
    d = ImageDraw.Draw(img)
    d.ellipse([size * 0.55, size * 0.08, size * 0.85, size * 0.38], outline=color, width=2)
    d.ellipse([size * 0.08, size * 0.28, size * 0.58, size * 0.70], outline=color, width=2)
    d.rectangle([size * 0.29, size * 0.64, size * 0.37, size * 0.88], fill=color)
    d.line([size * 0.04, size * 0.90, size * 0.58, size * 0.90], fill=color, width=2)
    return img


_GENERADORES = {
    "nuevo": _nuevo,
    "abrir": _abrir,
    "guardar": _guardar,
    "play": _play,
    "barras": _barras,
    "curva": _curva,
    "pdf": _pdf,
    "logo": _logo,
}


def obtener_icono(nombre: str, size: int = 26, color: str = "#3d4257") -> ImageTk.PhotoImage:
    """Devuelve un ImageTk.PhotoImage cacheado. El caché es necesario:
    Tkinter no retiene una referencia propia a PhotoImage, así que si
    no se guarda en algún lado el ícono se vacía apenas Python recolecta
    el objeto (bug clásico de Tkinter, no un descuido acá)."""
    clave = (nombre, size, color)
    if clave not in _CACHE:
        generador = _GENERADORES.get(nombre)
        if generador is None:
            raise ValueError(f"Ícono desconocido para el ribbon: {nombre}")
        imagen = generador(size, color)
        _CACHE[clave] = ImageTk.PhotoImage(imagen)
    return _CACHE[clave]
