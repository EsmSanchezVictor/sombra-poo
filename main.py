"""Entrada de Proyecto Sombra: portada, carga y acceso autenticado."""
import tkinter as tk

from core.app_logging import configure_logging
from core.app_version import APP_RELEASE
from ui.error_handlers import install_tk_error_handler
from ui.startup import StartupSplash
from ui.theme import aplicar_tema


def main():
    logger = configure_logging()
    logger.info('Inicio de Proyecto Sombra %s', APP_RELEASE)
    db_manager = root = splash = None
    try:
        root = tk.Tk()
        root.withdraw()
        install_tk_error_handler(root, logger)
        aplicar_tema(root)
        splash = StartupSplash(root)

        splash.phase("Cargando NumPy y pandas…", 0)
        import numpy
        import pandas

        splash.phase("Cargando interfaz y visualización…", 1)
        from main_app import MainApp
        from ui.auth_flow import setup_first_admin

        splash.phase("Abriendo datos locales y preparando el acceso…", 2)
        from database_manager import DatabaseManager
        db_manager = DatabaseManager()
        app = MainApp(root, db_manager)

        splash.complete()
        splash.close()
        splash = None
        root.deiconify()
        root.update_idletasks()
        if db_manager.needs_initial_admin() and not setup_first_admin(root, db_manager):
            return
        app.username_entry.focus_set()
        root.mainloop()
    except Exception:
        logger.exception('No se pudo iniciar o continuar la aplicación')
        raise
    finally:
        try:
            if splash is not None:
                splash.close()
            if root is not None and root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass
        finally:
            if db_manager is not None:
                db_manager.close()


if __name__ == "__main__":
    main()
