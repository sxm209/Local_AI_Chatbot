from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import data_paths


def configure_logging() -> None:
    paths = data_paths()
    log_file = paths["logs"] / "backend.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s event=%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler())
