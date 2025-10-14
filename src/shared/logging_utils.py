"""
Logging utilities for the KG-Sentiment platform.

This module provides standardized logging setup with tqdm integration
for consistent logging across the entire application.
"""

import logging
import sys
from pathlib import Path
import pyprojroot

from tqdm.contrib.logging import logging_redirect_tqdm


def setup_logger(name: str, log_file: Path, level: logging = logging.INFO):
    """
    Set up a logger with the specified name and integrate it with tqdm automatically.
    """
    # Create a custom logger
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        # Formatter for log messages
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # File handler to write logs to a file
        log_file_path = pyprojroot.here() / Path("logs") / log_file
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Tqdm handler
        tqdm_handler = logging.StreamHandler(stream=sys.stdout)
        tqdm_handler.setFormatter(formatter)
        logger.addHandler(tqdm_handler)

        # Apply logging redirection automatically
        logging_redirect_tqdm(logger)

    # Prevent logs from propagating to the root logger
    logger.propagate = False

    return logger