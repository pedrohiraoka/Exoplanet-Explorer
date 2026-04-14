"""Logging configuration for Exoplanet Explorer."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: The name of the logger (usually __name__).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    log_dir = Path.home() / ".exoplanet_explorer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "exoplanet_explorer.log"

    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        pass

    logger.propagate = False

    return logger


def set_log_level(level: str | int) -> None:
    """Set the log level for all Exoplanet Explorer loggers.

    Args:
        level: Log level as string (e.g., 'DEBUG') or int (e.g., logging.DEBUG).
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger("src")
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        handler.setLevel(level)

    os.environ["LOG_LEVEL"] = logging.getLevelName(level)
