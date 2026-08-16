"""Tema visual centralizado de la aplicación.

Antes cada pantalla definía sus propios colores de botón sueltos
(#4CAF50 en un lado, #2563eb en otro, tk.Button planos sin hover acá,
ttk allá) — esto da un único lugar para la paleta y los estilos ttk, y
un helper para que los tk.Button "clásicos" (que no usan ttk) también
tengan hover consistente sin repetir el bind en cada uno.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

PALETA = {
    # Los 4 originales — mismos valores, para no romper nada que ya
    # los usa (self.palette["background"], etc.).
    "background": "#f5f7fb",
    "panel": "#ffffff",
    "accent": "#e6ebf5",
    "border": "#d6dce8",
    # Nuevos — vocabulario de color con intención (primario, éxito,
    # texto) en vez de códigos hex sueltos repetidos por pantalla.
    "primario": "#2f6fed",
    "primario_hover": "#2557c4",
    "texto": "#26324a",
    "texto_suave": "#6b7385",
    "exito": "#3aa76d",
    "exito_hover": "#2e8a59",
    "peligro": "#d9534f",
}


def aplicar_tema(root: tk.Misc, paleta: dict | None = None) -> ttk.Style:
    """Configura ttk.Style globalmente. Se llama una sola vez al
    arrancar la app, antes de construir el resto de los widgets."""
    p = paleta or PALETA
    style = ttk.Style(root)
    try:
        # 'clam' es la única base de ttk que respeta bg/fg personalizados
        # de forma consistente entre Windows/Linux — el tema nativo de
        # Windows ignora background en varios widgets.
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "TButton", background=p["panel"], foreground=p["texto"],
        borderwidth=1, focusthickness=0, padding=6, font=("Segoe UI", 9),
    )
    style.map("TButton", background=[("active", p["accent"])])

    style.configure(
        "Primary.TButton", background=p["primario"], foreground="white",
        padding=8, font=("Segoe UI", 9, "bold"),
    )
    style.map("Primary.TButton", background=[("active", p["primario_hover"])])

    style.configure(
        "Success.TButton", background=p["exito"], foreground="white",
        padding=8, font=("Segoe UI", 9, "bold"),
    )
    style.map("Success.TButton", background=[("active", p["exito_hover"])])

    style.configure("TCombobox", padding=4)
    style.configure("TLabel", background=p["panel"], foreground=p["texto"], font=("Segoe UI", 9))
    style.configure(
        "Heading.TLabel", background=p["panel"], foreground=p["texto"],
        font=("Segoe UI", 13, "bold"),
    )
    style.configure(
        "Muted.TLabel", background=p["panel"], foreground=p["texto_suave"],
        font=("Segoe UI", 8),
    )
    return style


def dar_hover(widget: tk.Widget, color_normal: str, color_hover: str) -> None:
    """Hover manual para un tk.Button 'clásico' (no ttk) — para los
    lugares donde ya existe un tk.Button con bg fijo y no vale la pena
    migrarlo entero a ttk.Button todavía."""
    widget.configure(bg=color_normal, activebackground=color_hover)
    widget.bind("<Enter>", lambda _e: widget.config(bg=color_hover))
    widget.bind("<Leave>", lambda _e: widget.config(bg=color_normal))
