"""
Logging configuration using Loguru.
Provides structured logging with rotation and multiple output targets.
"""

import sys
from loguru import logger
from app.core.config import get_settings

# Remove default handler
logger.remove()

# Get settings
settings = get_settings()

# Add console handler
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# Add file handler with rotation
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Export configured logger
__all__ = ["logger"]