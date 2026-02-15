"""
Logging configuration using Loguru.
Provides enhanced logging with automatic formatting and rotation.
"""

import sys
from loguru import logger
from src.config.settings import settings


def setup_logger():
    """
    Configure logger with appropriate format and level.
    Remove default handler and add custom configuration.
    """

    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level.upper(),
        colorize=True,
    )

    logger.add(
        "logs/opensloth_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level=settings.log_level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    return logger


setup_logger()
