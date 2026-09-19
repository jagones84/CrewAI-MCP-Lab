"""Application logger that writes to file + stdout with timestamps and module tags."""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def setup_logging(log_file_path: str, logger_name: str = "comfyui_image_gen") -> logging.Logger:
    """Configure the application logger.

    Args:
        log_file_path: Path of the log file. Parent directories are created.
        logger_name: Name of the returned logger.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler: Optional[logging.FileHandler] = None
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == os.path.abspath(log_file_path):
            file_handler = handler
            break
    if file_handler is None:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger
