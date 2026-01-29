"""Bootstrap de la aplicación principal."""

import tkinter as tk
from ui.app_ui import SombraApp

# Alias para mantener compatibilidad con imports previos
App = SombraApp

def main() -> None:
    """Punto de entrada para ejecutar la UI directamente."""
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()