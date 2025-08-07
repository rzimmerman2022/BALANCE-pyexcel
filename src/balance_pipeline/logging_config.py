"""
Centralized logging configuration for the BALANCE pipeline.

This module provides a single point for configuring logging across the entire
application, preventing multiple basicConfig calls and ensuring consistent
logging behavior.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

# Track whether logging has been configured
_logging_configured = False


def configure_logging(
    level: str | int = logging.INFO,
    log_file: Optional[str | Path] = None,
    format_string: Optional[str] = None,
    force: bool = False
) -> None:
    """
    Configure logging for the entire application.
    
    This function should be called once at application startup.
    Subsequent calls will be ignored unless force=True.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path
        format_string: Optional custom format string
        force: Force reconfiguration even if already configured
    """
    global _logging_configured
    
    # Skip if already configured (unless forced)
    if _logging_configured and not force:
        return
    
    # Default format if not provided
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Ensures logging is configured before returning the logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    # Ensure logging is configured with defaults if not already done
    if not _logging_configured:
        configure_logging()
    
    return logging.getLogger(name)


def is_configured() -> bool:
    """Check if logging has been configured."""
    return _logging_configured