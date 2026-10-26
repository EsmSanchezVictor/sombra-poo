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

