from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def get_logger(name: str = "chirp") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    console = Console(force_terminal=True)
    handler = RichHandler(console=console, show_time=True, markup=False)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def configure_root(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, handlers=[RichHandler(console=Console(force_terminal=True))])
