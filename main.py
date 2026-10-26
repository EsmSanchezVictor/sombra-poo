import tkinter as tk
from core.app_logging import configure_logging
from ui.error_handlers import install_tk_error_handler
from database_manager import DatabaseManager
from main_app import MainApp
from ui.auth_flow import setup_first_admin
from core.app_version import APP_RELEASE


def main():
    logger = configure_logging()
    logger.info('Inicio de Proyecto Sombra %s', APP_RELEASE)
    db_manager = None
    try:
        db_manager = DatabaseManager()
        root = tk.Tk()
        install_tk_error_handler(root,logger)
        if db_manager.needs_initial_admin() and not setup_first_admin(root, db_manager):
            root.destroy()
            return
        MainApp(root, db_manager)
        root.mainloop()
    except Exception:
        logger.exception('No se pudo iniciar o continuar la aplicación')
        raise
    finally:
        # Garantiza liberación del archivo SQLite incluso si Tk termina por una
        # ruta distinta a los botones de salida.
        if db_manager is not None:
            db_manager.close()


if __name__ == "__main__":
    main()
