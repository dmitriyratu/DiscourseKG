"""
Logging utilities for the DiscourseKG platform.
"""

import logging
import sys
import inspect
from pathlib import Path
import pyprojroot
from tqdm.contrib.logging import logging_redirect_tqdm
from src.config import config


def get_logger(name: str = None, level: logging = None):
    """Set up a logger with automatic naming and tqdm integration."""
    if name is None:
        # Get caller's module name
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    # Extract just the module name (last part after dots)
    module_name = name.split('.')[-1]
    log_file = f"{module_name}.log"
    
    # Create a custom logger
    logger = logging.getLogger(module_name)

    if not logger.handlers:
        # Set level based on environment if not specified
        if level is None:
            level = logging.DEBUG if config.ENVIRONMENT == "development" else logging.INFO
        
        logger.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # File handler
        log_file_path = pyprojroot.here() / Path("logs") / log_file
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Tqdm integration
        logging_redirect_tqdm(logger)

    logger.propagate = False
    return logger