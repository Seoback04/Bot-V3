"""Structured logging: console handler + rotating file handler."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import SETTINGS


_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(log_file: Path | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(getattr(logging, SETTINGS.log_level, logging.INFO))
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console)

    file_path = log_file or (SETTINGS.output_dir / "run.log")
    try:
        fh = RotatingFileHandler(file_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(fh)
    except OSError:
        root.warning("Could not attach file log handler at %s", file_path)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
