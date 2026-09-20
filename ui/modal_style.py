"""Utilidades visuales para ventanas emergentes de Proyecto Sombra.

v35.6 centraliza el aspecto y el comportamiento de los ``Toplevel`` propios
sin reemplazar los cuadros nativos de Windows (abrir/guardar/messagebox).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, font as tkfont

from ui.theme import PALETA




def ensure_dialog_styles(root: tk.Misc) -> None:
    """Define los estilos mínimos de diálogo sin cambiar el tema ttk activo."""
    try:
        style = ttk.Style(root)
        style.configure("TLabel", foreground=PALETA["texto"], font=("Segoe UI", 9))
        style.configure("Heading.TLabel", foreground=PALETA["texto"], font=("Segoe UI", 13, "bold"))
        style.configure("Muted.TLabel", foreground=PALETA["texto_suave"], font=("Segoe UI", 8))
        style.configure("DialogSection.TLabel", foreground=PALETA["texto"], font=("Segoe UI", 10, "bold"))
        style.configure("TButton", foreground=PALETA["texto"], padding=6, font=("Segoe UI", 9))
        style.configure("DialogPrimary.TButton", background=PALETA["primario"], foreground="white", padding=(12, 7), font=("Segoe UI", 9, "bold"))
        style.map("DialogPrimary.TButton", background=[("active", PALETA["primario_hover"])])
        style.configure("DialogSuccess.TButton", background=PALETA["exito"], foreground="white", padding=(12, 7), font=("Segoe UI", 9, "bold"))
        style.map("DialogSuccess.TButton", background=[("active", PALETA["exito_hover"])])
        style.configure("TCombobox", padding=4)
    except (tk.TclError, AttributeError):
        pass

DIALOG_PAD_X = 18
DIALOG_PAD_Y = 16
FIELD_PAD_Y = 6
LABEL_PAD_X = (0, 14)


def _safe_exists(widget):
    try:
        return bool(widget is not None and widget.winfo_exists())
    except tk.TclError:
        return False


def center_dialog(window: tk.Toplevel, parent: tk.Misc | None = None) -> None:
    """Centra conservando el tamaño solicitado o la geometría explícita."""
    try:
        window.update_idletasks()
        w = max(window.winfo_width(), window.winfo_reqwidth())
        h = max(window.winfo_height(), window.winfo_reqheight())
        if _safe_exists(parent):
            pw = max(parent.winfo_width(), parent.winfo_reqwidth())
            ph = max(parent.winfo_height(), parent.winfo_reqheight())
            x = parent.winfo_rootx() + max(0, (pw - w) // 2)
            y = parent.winfo_rooty() + max(0, (ph - h) // 2)
        else:
            x = max(0, (window.winfo_screenwidth() - w) // 2)
            y = max(0, (window.winfo_screenheight() - h) // 2)
        # Solo fija posición; respeta el tamaño actual/requerido.
        window.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass


def _style_classic_widgets(widget: tk.Misc) -> None:
    """Aproxima los widgets tk clásicos al lenguaje visual ttk de la app."""
    for child in widget.winfo_children():
        try:
            if isinstance(child, tk.Frame) and not isinstance(child, ttk.Frame):
                child.configure(bg=PALETA["panel"], relief="flat", bd=0, highlightthickness=0)
            elif isinstance(child, tk.Label) and not isinstance(child, ttk.Label):
                # Mantiene títulos/negritas y tipografías técnicas (p.ej. Consolas);
                # normaliza solo las etiquetas de cuerpo.
                cfg = {"bg": PALETA["panel"]}
                try:
                    f = tkfont.Font(font=child.cget("font"))
                    actual = f.actual()
                    if actual.get("weight") != "bold" and str(actual.get("family", "")).lower() not in {"consolas", "courier", "courier new"}:
                        cfg["font"] = ("Segoe UI", 9)
                except tk.TclError:
                    cfg["font"] = ("Segoe UI", 9)
                child.configure(**cfg)
            elif isinstance(child, tk.Radiobutton):
                child.configure(
                    bg=PALETA["panel"], activebackground=PALETA["panel"],
                    fg=PALETA["texto"], font=("Segoe UI", 9),
                    selectcolor=PALETA["panel"], highlightthickness=0,
                )
            elif isinstance(child, tk.Checkbutton):
                child.configure(
                    bg=PALETA["panel"], activebackground=PALETA["panel"],
                    fg=PALETA["texto"], font=("Segoe UI", 9),
                    selectcolor=PALETA["panel"], highlightthickness=0,
                )
            elif isinstance(child, tk.Button):
                # No pisa colores especiales ya asignados (p.ej. verde/azul).
                bg = str(child.cget("background"))
                default_like = bg in {"SystemButtonFace", "#d9d9d9", "white", PALETA["panel"]}
                child.configure(
                    font=("Segoe UI", 9), relief="flat", bd=1,
                    padx=max(int(child.cget("padx") or 0), 10),
                    pady=max(int(child.cget("pady") or 0), 5),
                    cursor="hand2",
                    highlightthickness=0,
                )
                if default_like:
                    child.configure(
                        bg=PALETA["panel"], fg=PALETA["texto"],
                        activebackground=PALETA["accent"],
                        activeforeground=PALETA["texto"],
                    )
            elif isinstance(child, tk.Entry):
                child.configure(font=("Segoe UI", 9), relief="solid", bd=1)
            elif isinstance(child, tk.Listbox):
                child.configure(font=("Segoe UI", 9), relief="solid", bd=1)
            elif isinstance(child, tk.Spinbox):
                child.configure(font=("Segoe UI", 9), relief="solid", bd=1)
        except (tk.TclError, ValueError, TypeError):
            pass
        _style_classic_widgets(child)


def prepare_dialog(
    window: tk.Toplevel,
    parent: tk.Misc | None = None,
    *,
    modal: bool = False,
    resizable: bool | tuple[bool, bool] | None = None,
    close_callback=None,
    escape_closes: bool = True,
    minsize: tuple[int, int] | None = None,
) -> tk.Toplevel:
    """Aplica cromado, centrado, teclado y tipografía homogéneos.

    Puede llamarse inmediatamente después de crear el Toplevel. El estilado
    recursivo y el centrado se ejecutan ``after_idle`` para incluir los widgets
    que la función llamadora agregue a continuación.
    """
    ensure_dialog_styles(window)
    try:
        window.configure(bg=PALETA["panel"])
        if _safe_exists(parent):
            window.transient(parent)
        if isinstance(resizable, tuple):
            window.resizable(*resizable)
        elif isinstance(resizable, bool):
            window.resizable(resizable, resizable)
        if minsize:
            window.minsize(*minsize)
    except (tk.TclError, AttributeError):
        pass

    def close():
        if callable(close_callback):
            close_callback()
        else:
            try:
                window.destroy()
            except tk.TclError:
                pass

    try:
        window.protocol("WM_DELETE_WINDOW", close)
        if escape_closes:
            window.bind("<Escape>", lambda _e: close(), add="+")
    except (tk.TclError, AttributeError):
        pass

    def finish():
        if not _safe_exists(window):
            return
        _style_classic_widgets(window)
        center_dialog(window, parent)
        if modal:
            try:
                window.grab_set()
            except tk.TclError:
                pass

    try:
        window.after_idle(finish)
    except (tk.TclError, AttributeError):
        pass
    return window


def dialog_container(window: tk.Misc, *, padding=(DIALOG_PAD_X, DIALOG_PAD_Y, DIALOG_PAD_X, DIALOG_PAD_Y)):
    """Contenedor blanco/padded equivalente al usado en Árbol/Estructura."""
    frame = ttk.Frame(window, padding=padding)
    frame.pack(fill="both", expand=True)
    return frame


def dialog_header(parent: tk.Misc, title: str, subtitle: str = "", *, layout="pack"):
    """Cabecera común de los formularios nuevos."""
    frame = ttk.Frame(parent)
    if layout == "grid":
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    else:
        frame.pack(fill="x", pady=(0, 14))
    ttk.Label(frame, text=title, style="Heading.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(frame, text=subtitle, style="Muted.TLabel", wraplength=620, justify="left").pack(
            anchor="w", pady=(2, 0)
        )
    return frame


def dialog_button_bar(parent: tk.Misc, *, layout="pack"):
    frame = ttk.Frame(parent)
    if layout == "grid":
        frame.grid(sticky="e", pady=(16, 0))
    else:
        frame.pack(fill="x", pady=(16, 0))
    return frame


def ask_text(
    parent: tk.Misc | None,
    title: str,
    prompt: str,
    *,
    initial: str = "",
    show: str | None = None,
    accept_text: str = "Aceptar",
) -> str | None:
    """Reemplazo visual homogéneo de ``simpledialog.askstring``."""
    result = {"value": None}
    dlg = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
    dlg.title(title)
    prepare_dialog(dlg, parent, modal=True, resizable=False)
    cont = dialog_container(dlg)
    dialog_header(cont, title, prompt)
    var = tk.StringVar(value=initial)
    entry = ttk.Entry(cont, textvariable=var, width=40, show=show or "")
    entry.pack(fill="x", pady=(0, 4))

    buttons = ttk.Frame(cont)
    buttons.pack(fill="x", pady=(16, 0))

    def accept():
        result["value"] = var.get()
        dlg.destroy()

    ttk.Button(buttons, text="Cancelar", command=dlg.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text=accept_text, command=accept, style="DialogPrimary.TButton").pack(side="right")
    dlg.bind("<Return>", lambda _e: accept())
    entry.focus_set()
    dlg.wait_window()
    return result["value"]


def ask_password_pair(
    parent: tk.Misc | None,
    title: str = "Cambiar contraseña",
    *,
    min_length: int = 8,
) -> tuple[str | None, str | None]:
    """Pide contraseña y confirmación en un único diálogo homogéneo."""
    result = {"value": (None, None)}
    dlg = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
    dlg.title(title)
    prepare_dialog(dlg, parent, modal=True, resizable=False)
    cont = dialog_container(dlg)
    dialog_header(cont, title, f"Ingresá la nueva contraseña dos veces. Mínimo {min_length} caracteres.")
    form = ttk.Frame(cont)
    form.pack(fill="x")
    form.columnconfigure(1, weight=1)
    p1 = tk.StringVar(); p2 = tk.StringVar()
    ttk.Label(form, text="Nueva contraseña:").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
    e1 = ttk.Entry(form, textvariable=p1, show="*", width=34)
    e1.grid(row=0, column=1, sticky="ew", pady=6)
    ttk.Label(form, text="Repetir contraseña:").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
    e2 = ttk.Entry(form, textvariable=p2, show="*", width=34)
    e2.grid(row=1, column=1, sticky="ew", pady=6)
    error = ttk.Label(cont, text="", foreground="#d9534f")
    error.pack(fill="x", pady=(4, 0))
    buttons = ttk.Frame(cont)
    buttons.pack(fill="x", pady=(16, 0))

    def accept():
        a, b = p1.get(), p2.get()
        if len(a) < min_length:
            error.configure(text=f"La contraseña debe tener al menos {min_length} caracteres.")
            return
        if a != b:
            error.configure(text="Las contraseñas no coinciden.")
            return
        result["value"] = (a, b)
        dlg.destroy()

    ttk.Button(buttons, text="Cancelar", command=dlg.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Guardar contraseña", command=accept, style="DialogPrimary.TButton").pack(side="right")
    dlg.bind("<Return>", lambda _e: accept())
    e1.focus_set()
    dlg.wait_window()
    return result["value"]
