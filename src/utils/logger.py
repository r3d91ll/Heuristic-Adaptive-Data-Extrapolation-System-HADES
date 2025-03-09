"""
Logging utilities for HADES.
"""
import logging
import os
import sys
from typing import Optional

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: The name of the logger, typically __name__
        level: Optional override for log level
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level from environment or parameter
    log_level = getattr(logging, level or LOG_LEVEL)
    logger.setLevel(log_level)
    
    # Create handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    
    return logger
