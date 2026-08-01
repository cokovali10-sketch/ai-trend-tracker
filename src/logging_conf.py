"""
Настройка логирования — консоль + файл с ротацией.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from src.config import settings, path_for

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-14s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_configured = False


def setup_logging() -> logging.Logger:
    """Инициализирует корневой логгер проекта (вызывается один раз)."""
    global _configured
    logger = logging.getLogger("trends")
    if _configured:
        return logger

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Консоль
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Файл с ротацией (макс. 1 МБ, 3 бэкапа)
    log_path = path_for(settings.log_file)
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    logger.propagate = False
    _configured = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Возвращает дочерний логгер: trends.<name>."""
    return logging.getLogger(f"trends.{name}")
