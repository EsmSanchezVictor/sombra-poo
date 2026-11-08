"""Portada de arranque y carga de los recursos visuales originales."""
from time import monotonic
import tkinter as tk
from tkinter import ttk

from core.runtime_paths import resource_path


def load_brand(name, *, trim=False):
    """Carga el PNG de la aplicación; el recorte solo afecta su presentación."""
    try:
        from PIL import Image
        with Image.open(resource_path("assest", name)) as original:
            picture = original.convert("RGBA")
    except (ImportError, OSError, ValueError):
        return None
    if trim:
        bounds = picture.getchannel("A").point(lambda n: 255 if n >= 32 else 0).getbbox()
        if bounds:
            left, top, right, bottom = bounds
            pad = 4
            picture = picture.crop((max(0, left-pad), max(0, top-pad),
                                    min(picture.width, right+pad), min(picture.height, bottom+pad)))
    return picture


def brand_photo(picture, master, width, height):
    if picture is None:
        return None
    from PIL import Image, ImageTk

    preview = picture.copy()
    preview.thumbnail((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(preview, master=master)


class StartupSplash:
    """Ventana liviana que precede a los imports científicos y a la sesión."""

    def __init__(self, root, minimum_ms=1600):
        self.root = root
        self.minimum_ms = minimum_ms
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg="#08060b", highlightthickness=1, highlightbackground="#392449")
        self.window.title("Iniciando Proyecto Sombra")
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        width = min(620, max(320, int(screen_width * .43)), screen_width - 24)
        cover = load_brand("protada.png")
        self.cover = brand_photo(cover, self.window, width, max(100, screen_height // 2))
        if self.cover is not None:
            tk.Label(self.window, image=self.cover, bg="#08060b", borderwidth=0).pack()
        else:
            tk.Label(self.window, text="Proyecto Sombra", bg="#08060b", fg="white",
                     font=("Segoe UI", 19, "bold"), width=30, height=5).pack()
        footer = tk.Frame(self.window, bg="#100c17", padx=19, pady=11)
        footer.pack(fill="x")
        self.status = tk.Label(footer, text="Preparando el arranque…", bg="#100c17",
                               fg="#f4eaff", anchor="w", font=("Segoe UI", 10))
        self.status.pack(fill="x")
        style = ttk.Style(self.window)
        style.configure("Sombra.Startup.Horizontal.TProgressbar", background="#a755ce",
                        troughcolor="#36263e")
        self.progress = ttk.Progressbar(footer, maximum=3, mode="determinate",
                                       style="Sombra.Startup.Horizontal.TProgressbar", takefocus=False)
        self.progress.pack(fill="x", pady=(8, 0))
        self.window.update_idletasks()
        x = max(0, (screen_width - self.window.winfo_reqwidth()) // 2)
        y = max(0, (screen_height - self.window.winfo_reqheight()) // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        self.window.update()
        self.shown_at = monotonic()

    def phase(self, label, completed):
        self.status.configure(text=label)
        self.progress.configure(value=completed)
        # Publica la fase antes de la operación que ocupa el hilo de Tk.
        self.window.update()

    def complete(self):
        self.phase("Listo para iniciar sesión", 3)
        remaining = int(self.minimum_ms - (monotonic() - self.shown_at) * 1000)
        if remaining > 0:
            done = tk.BooleanVar(master=self.window, value=False)
            self.window.after(remaining, done.set, True)
            self.window.wait_variable(done)

    def close(self):
        if self.window.winfo_exists():
            self.window.destroy()
