"""Elementos visuales compartidos por los cuatro paneles laterales."""
from tkinter import ttk

from ui.theme import PALETA


def panel_body(parent, title):
    for widget in parent.winfo_children():
        widget.destroy()
    parent.columnconfigure(0, weight=1)
    body = ttk.Frame(parent, padding=(8, 10))
    body.grid(row=0, column=0, sticky="ew")
    body.columnconfigure(0, weight=1)
    ttk.Label(body, text=title, style="Heading.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 9))
    return body


def panel_section(parent, row, title):
    section = ttk.LabelFrame(parent, text=title, padding=(7, 4))
    section.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    section.columnconfigure(0, weight=1)
    return section


def panel_button(parent, row, text, command, **options):
    button = ttk.Button(parent, text=text, command=command, **options)
    button.grid(row=row, column=0, sticky="ew", pady=2)
    return button


def panel_note(parent, row, text="", *, columnspan=1, color=None):
    note = ttk.Label(parent, text=text, anchor="w", justify="left", wraplength=180,
                     foreground=color or PALETA["texto_suave"], style="Muted.TLabel")
    note.grid(row=row, column=0, columnspan=columnspan, sticky="ew", pady=(3, 4))
    def wrap(event):
        width = max(60, event.width - 4)
        if str(note.cget("wraplength")) != str(width):
            note.configure(wraplength=width)

    note.bind("<Configure>", wrap, add="+")
    return note


def panel_field(parent, row, label, widget_type=ttk.Entry, **options):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(2, 0))
    options.setdefault("width", 16)
    widget = widget_type(parent, **options)
    widget.grid(row=row+1, column=0, sticky="ew", pady=(1, 4))
    return widget
