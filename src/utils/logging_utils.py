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
    
    Args:
        name: Logger name (typically __name__ or module name)
        log_file: Path to log file (relative to project root/logs/)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
        
    Example:
        >>> from src.utils.logging_utils import setup_logger
        >>> logger = setup_logger(__name__, "content_categorizer.log")
        >>> logger.info("Starting categorization process")
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


def get_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Convenience function to get a logger with sensible defaults.
    
    Args:
        name: Logger name (typically __name__)
        log_file: Optional log file name (defaults to logger name + .log)
    
    Returns:
        Configured logger instance
        
    Example:
        >>> from src.utils.logging_utils import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
    """
    if log_file is None:
        # Extract module name from logger name for default log file
        module_name = name.split('.')[-1] if '.' in name else name
        log_file = f"{module_name}.log"
    
    return setup_logger(name, Path(log_file))


# Convenience loggers for common modules
def get_categorizer_logger():
    """Get logger for content categorizer module."""
    return get_logger("content_categorizer", "content_categorizer.log")


def get_processor_logger():
    """Get logger for data processing modules."""
    return get_logger("data_processor", "data_processing.log")


def get_api_logger():
    """Get logger for API endpoints."""
    return get_logger("api", "api.log")
