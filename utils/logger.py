"""
Logging configuration for the web scraping pipeline.
Provides formatted logging to both console and a rotating or persistent log file.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "scraper_pipeline",
    log_dir: Optional[Path] = None,
    log_file: str = "scraper.log",
    level: int = logging.INFO,
) -> logging.Logger:
    """Configures and returns a standardized logger instance.

    Args:
        name: The logger identifier.
        log_dir: Directory where log file will be saved.
        log_file: Name of the log file.
        level: Logging level (default: logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if setup_logger is invoked more than once
    if logger.handlers:
        return logger

    # Log format string
    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File Handler
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / log_file
        file_handler = logging.FileHandler(file_path, encoding="utf-8", mode="a")
        file_handler.setLevel(level)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

    return logger
