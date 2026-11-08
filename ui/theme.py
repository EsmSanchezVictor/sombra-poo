"""Paleta y componentes comunes de la interfaz de Proyecto Sombra."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONT = "Segoe UI"
PALETA = {
    "background": "#f5f1fa",
    "panel": "#ffffff",
    "accent": "#efe6f5",
    "selected": "#e8d6f2",
    "border": "#d6c5e1",
    "focus": "#8942ad",
    "primario": "#68258b",
    "primario_hover": "#54206f",
    "texto": "#241533",
    "texto_suave": "#5f4c6f",
    "disabled_bg": "#ede8f0",
    "disabled_fg": "#655b70",
    "exito": "#21634f",
    "exito_hover": "#184d3d",
    "exito_bg": "#e7f4ee",
    "peligro": "#a52d4d",
    "peligro_hover": "#85223e",
    "peligro_bg": "#fae9ef",
    "aviso": "#77531b",
    "aviso_bg": "#faf0dc",
    "aviso_hover": "#f1e1bd",
}


def aplicar_tema(root: tk.Misc, paleta: dict | None = None) -> ttk.Style:
    """Instala los estilos de trabajo y los valores por defecto de Tk."""
    p = PALETA if paleta is None else {**PALETA, **paleta}
    style = ttk.Style(root)
    if style.theme_use() != "clam" and "clam" in style.theme_names():
        style.theme_use("clam")

    def button(name, bg, fg, hover, padding, *, bold=False, border=None):
        style.configure(
            name, background=bg, foreground=fg, bordercolor=border or bg,
            lightcolor=bg, darkcolor=bg, borderwidth=1, relief="flat",
            focuscolor=p["focus"] if fg != "white" else "white",
            focusthickness=1, padding=padding,
            font=(FONT, 9, "bold" if bold else "normal"),
        )
        style.map(
            name,
            background=[("disabled", p["disabled_bg"]), ("pressed", hover), ("active", hover)],
            foreground=[("disabled", p["disabled_fg"])],
            bordercolor=[("focus", p["focus"])],
        )

    button("TButton", p["panel"], p["texto"], p["accent"], (9, 5), border=p["border"])
    for name, key, padding in (
        ("Primary.TButton", "primario", (12, 8)),
        ("Success.TButton", "exito", (12, 8)),
        ("Danger.TButton", "peligro", (12, 8)),
        ("DialogPrimary.TButton", "primario", (12, 7)),
        ("DialogSuccess.TButton", "exito", (12, 7)),
        ("WelcomePrimary.TButton", "primario", (20, 10)),
    ):
        button(name, p[key], "white", p[key + "_hover"], padding, bold=True)
    button("WelcomeSecondary.TButton", p["panel"], p["primario"], p["accent"], (20, 10),
           bold=True, border=p["border"])
    button("Ribbon.TButton", p["panel"], p["texto"], p["accent"], (4, 4))
    button("RibbonPrimary.TButton", p["accent"], p["primario"], p["selected"], (6, 4), bold=True)

    for name in ("TFrame", "Dialog.TFrame", "DialogFooter.TFrame", "TLabel",
                 "TCheckbutton", "TRadiobutton", "TLabelframe", "TLabelframe.Label"):
        style.configure(name, background=p["panel"], foreground=p["texto"], font=(FONT, 9))
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, focuscolor=p["focus"], indicatorbackground=p["panel"])
        style.map(name, foreground=[("disabled", p["disabled_fg"])],
                  indicatorbackground=[("disabled", p["disabled_bg"]), ("selected", p["selected"])])
    style.configure("TLabelframe", bordercolor=p["border"], relief="solid")
    style.configure("TLabelframe.Label", foreground=p["primario"], font=(FONT, 9, "bold"))
    style.configure("Heading.TLabel", foreground=p["texto"], font=(FONT, 14, "bold"))
    style.configure("DialogSection.TLabel", foreground=p["primario"], font=(FONT, 10, "bold"))
    style.configure("Muted.TLabel", foreground=p["texto_suave"], font=(FONT, 9))
    style.configure("RibbonGroup.TLabel", foreground=p["texto_suave"], font=(FONT, 8, "bold"))
    style.configure("TSeparator", background=p["border"])

    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=p["panel"], foreground=p["texto"],
                        background=p["accent"], bordercolor=p["border"],
                        arrowcolor=p["primario"], padding=(5, 3),
                        selectbackground=p["selected"], selectforeground=p["texto"])
        style.map(name, fieldbackground=[("disabled", p["disabled_bg"]),
                                         ("readonly", p["panel"])],
                  bordercolor=[("focus", p["focus"])],
                  foreground=[("disabled", p["disabled_fg"])])
    style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"],
                    foreground=p["texto"], bordercolor=p["border"], font=(FONT, 9))
    style.map("Treeview", background=[("selected", p["selected"])],
              foreground=[("selected", p["texto"])])
    style.configure("Treeview.Heading", background=p["accent"], foreground=p["primario"],
                    bordercolor=p["border"], font=(FONT, 9, "bold"), padding=(6, 4))
    style.map("Treeview.Heading", background=[("active", p["selected"])])
    style.configure("TNotebook", background=p["background"], bordercolor=p["border"])
    style.configure("TNotebook.Tab", background=p["background"], foreground=p["texto_suave"],
                    padding=(10, 5), font=(FONT, 9), focuscolor=p["focus"])
    style.map("TNotebook.Tab", background=[("selected", p["panel"]), ("active", p["accent"])],
              foreground=[("selected", p["primario"]), ("disabled", p["disabled_fg"])])
    style.configure("Scene.TNotebook", background=p["background"], bordercolor=p["border"],
                    tabmargins=(8, 6, 8, 0))
    style.configure("Scene.TNotebook.Tab", padding=(14, 7), background=p["background"],
                    foreground=p["texto_suave"], font=(FONT, 9, "bold"))
    style.map("Scene.TNotebook.Tab", background=[("selected", p["primario"]), ("active", p["accent"])],
              foreground=[("selected", "white"), ("disabled", p["disabled_fg"])],
              focuscolor=[("selected", "white"), ("!selected", p["focus"])])
    style.configure("TScrollbar", background=p["accent"], troughcolor=p["background"],
                    bordercolor=p["border"], arrowcolor=p["primario"])
    style.map("TScrollbar", background=[("active", p["selected"])])
    style.configure("TProgressbar", background=p["primario"], troughcolor=p["accent"],
                    bordercolor=p["border"])

    defaults = {
        "*Font": (FONT, 9),
        "*Toplevel.background": p["panel"],
        "*Frame.background": p["panel"],
        "*Labelframe.background": p["panel"],
        "*Labelframe.foreground": p["primario"],
        "*Label.background": p["panel"],
        "*Label.foreground": p["texto"],
        "*Menu.background": p["panel"],
        "*Menu.foreground": p["texto"],
        "*Menu.activeBackground": p["selected"],
        "*Menu.activeForeground": p["texto"],
        "*Menu.disabledForeground": p["disabled_fg"],
        "*Button.background": p["panel"],
        "*Button.foreground": p["texto"],
        "*Button.activeBackground": p["accent"],
        "*Button.activeForeground": p["texto"],
        "*Button.disabledForeground": p["disabled_fg"],
        "*Button.relief": "flat",
        "*Button.highlightColor": p["focus"],
    }
    for cls in ("Entry", "Spinbox", "Listbox", "Text"):
        for prop, color in (("background", "panel"), ("foreground", "texto"),
                            ("selectBackground", "selected"), ("selectForeground", "texto"),
                            ("highlightBackground", "border"), ("highlightColor", "focus")):
            defaults[f"*{cls}.{prop}"] = p[color]
    for cls in ("Checkbutton", "Radiobutton"):
        for prop, color in (("background", "panel"), ("foreground", "texto"),
                            ("activeBackground", "accent"), ("activeForeground", "texto"),
                            ("selectColor", "selected"), ("highlightColor", "focus")):
            defaults[f"*{cls}.{prop}"] = p[color]
    for pattern, value in defaults.items():
        root.option_add(pattern, value, "widgetDefault")
    return style


def dar_hover(widget: tk.Widget, color_normal: str, color_hover: str) -> None:
    """Aplica el estado de puntero sin alterar el aspecto de un botón deshabilitado."""
    widget.configure(bg=color_normal, activebackground=color_hover)
    widget.bind("<Enter>", lambda _e: widget.config(bg=color_hover) if str(widget.cget("state")) != "disabled" else None)
    widget.bind("<Leave>", lambda _e: widget.config(bg=color_normal))
