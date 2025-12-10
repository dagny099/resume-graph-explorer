"""
Centralized logging configuration for ChronoScope.

Provides consistent logging across all modules with appropriate formatting and levels.
"""

import logging
from typing import Optional

from chrono_scope.utils.constants import LOG_LEVEL_DEFAULT, LOG_FORMAT


# Global logger cache to avoid recreating loggers
_loggers = {}


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger with standardized configuration.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
               If None, uses LOG_LEVEL_DEFAULT from constants

    Returns:
        Configured logger instance

    Example:
        >>> from chronoscope.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing document...")
        >>> logger.warning("Low confidence extraction")
        >>> logger.error("Failed to parse date")
    """
    # Return cached logger if already created
    if name in _loggers:
        return _loggers[name]

    # Create new logger
    logger = logging.getLogger(name)

    # Set level
    log_level = level or LOG_LEVEL_DEFAULT
    logger.setLevel(getattr(logging, log_level.upper()))

    # Only add handler if logger doesn't have any (avoid duplicate logs)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, log_level.upper()))

        # Use consistent format
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    # Cache for reuse
    _loggers[name] = logger

    return logger


def configure_root_logger(level: str = LOG_LEVEL_DEFAULT):
    """
    Configure the root logger for the entire application.

    Call this once at application startup to set global logging behavior.

    Args:
        level: Log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

    Example:
        >>> from chronoscope.utils.logger import configure_root_logger
        >>> configure_root_logger('DEBUG')  # Enable debug logging
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT
    )


# Create a default logger for this module
logger = get_logger(__name__)
