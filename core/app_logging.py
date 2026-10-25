"""Registro local rotativo; sin claves ni valores de autenticación."""
import logging
from logging.handlers import RotatingFileHandler
from core.auth_policy import default_users_path


def configure_logging(directory=None):
    folder = directory or default_users_path().parent / 'logs'
    from pathlib import Path
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('sombra')
    logger.setLevel(logging.INFO)
    target = str(folder / 'sombra.log')
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(Path(target).resolve()) for h in logger.handlers):
        handler = RotatingFileHandler(target, maxBytes=1024*1024, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        logger.addHandler(handler)
    return logger


def install_tk_error_handler(root, logger):
    def report(exception_type, exception, traceback):
        from tkinter import messagebox
        from core.local_time import LocalTimeError
        logger.error('Error de callback de la interfaz',exc_info=(exception_type,exception,traceback))
        if isinstance(exception, LocalTimeError):
            messagebox.showerror('Fecha y hora del escenario', str(exception))
        else:
            messagebox.showerror('Error de la aplicación','Se produjo un error. El detalle quedó en el registro de diagnóstico local.')
    root.report_callback_exception = report
