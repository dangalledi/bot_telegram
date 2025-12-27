# logger.py

import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logging(
    log_dir: str = "log",
    log_file: str = "bot.log",
    level: int = logging.INFO,
    backups: int = 14,
) -> logging.Logger:
    """
    - Archivo: log/bot.log con rotación diaria (backupCount=14)
    - Consola (stdout): para journald via systemd
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()  # root
    logger.setLevel(level)

    # Evita duplicar handlers si importas varias veces
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Archivo con rotación diaria
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, log_file),
        when="midnight",
        backupCount=backups,
        encoding="utf-8",
        utc=False,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)

    # Stdout -> journald cuando corre con systemd
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
