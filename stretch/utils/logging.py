from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict

from stretch.utils.colors import Color, colorize


class ColoredFormatter(logging.Formatter):
    """Defines a custom formatter for displaying logs."""

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    COLORS: Dict[str, Color] = {
        "WARNING": "yellow",
        "INFO": "cyan",
        "DEBUG": "white",
        "CRITICAL": "yellow",
        "FATAL": "red",
        "ERROR": "red",
    }

    def __init__(self, *, prefix: str | None = None, use_color: bool = True):
        message = "{levelname:^19s} [{name}] {message}"
        if prefix is not None:
            message = colorize(prefix, "white") + " " + message
        super().__init__(message, style="{")

        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname

        if levelname == "DEBUG":
            record.levelname = ""
        else:
            if self.use_color and levelname in self.COLORS:
                record.levelname = colorize(levelname, self.COLORS[levelname])
        return logging.Formatter.format(self, record)


def configure_logging(
    *,
    prefix: str | None = None,
    to_file: Path | None = None,
    log_level: int = logging.INFO,
) -> None:
    """Instantiates logging, either to the console or to a file.

    Args:
        prefix: An optional prefix to add to the logger
        to_file: Write to a file instead of to stdout
        log_level: The minimum logging level
    """

    root_logger = logging.getLogger()
    while root_logger.hasHandlers():
        root_logger.removeHandler(root_logger.handlers[0])
    handler: logging.Handler
    if to_file is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(to_file, mode="a")
    handler.setFormatter(ColoredFormatter(prefix=prefix))
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
